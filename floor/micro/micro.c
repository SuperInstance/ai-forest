/*
 * micro.c — AI Forest floor micro-agent
 *
 * Minimal C agent for embedded edge devices.
 * Reads a sensor value, encodes it as a 24-bit tile,
 * and POSTs it to the floor room via POSIX sockets.
 *
 * Usage: ./micro-agent [interval_seconds] [sensor_file]
 *   interval_seconds  polling interval (default: 5)
 *   sensor_file       path to sensor value (default: reads stdin once)
 *
 * Build:  make
 * Run:    make run
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <errno.h>

/* ================================================================
 * 24-bit Tile Encoding (from 24BIT-SPEC.md)
 * ================================================================
 * Bit layout (balanced scheme):
 *   bits 0-5    (0): scheme     = 2 bits
 *   bits 2-7    (2): confidence = 6 bits
 *   bits 8-13  (14): gradient   = 6 bits
 *   bits 14-19 (20): epsilon    = 6 bits
 *   bits 20-25 (26): context    = 6 bits
 *
 * Stored in lower 24 bits of uint32_t.
 * ================================================================ */

typedef union {
    uint32_t raw;
    struct {
        unsigned scheme    : 2;
        unsigned confidence : 6;
        unsigned gradient   : 6;
        unsigned epsilon    : 6;
        unsigned context    : 6;
    } balanced;
} Tile24;

/* ================================================================
 * Defaults
 * ================================================================ */
#define DEFAULT_INTERVAL  5   /* seconds between polls */
#define HOST              "localhost"
#define PORT              8847
#define PATH              "/room/floor-micro/submit"

/* ================================================================
 * Strip trailing newline / carriage return
 * ================================================================ */
static void chomp(char *s) {
    size_t len = strlen(s);
    while (len > 0 && (s[len-1] == '\n' || s[len-1] == '\r'))
        s[--len] = '\0';
}

/* ================================================================
 * Read a sensor value from file OR stdin
 * Returns the parsed integer, or -1 on error.
 * ================================================================ */
static int read_sensor(const char *path) {
    char buf[128];
    FILE *fp;

    if (path) {
        fp = fopen(path, "r");
        if (!fp) {
            fprintf(stderr, "[micro] ERROR: cannot open %s: %s\n",
                    path, strerror(errno));
            return -1;
        }
    } else {
        fp = stdin;
    }

    if (!fgets(buf, sizeof(buf), fp)) {
        if (path) fclose(fp);
        return -1;
    }
    chomp(buf);

    if (path) fclose(fp);
    return atoi(buf);
}

/* ================================================================
 * Encode a raw sensor value into a 24-bit tile (balanced scheme)
 * ================================================================ */
static Tile24 encode_tile(int raw_value) {
    Tile24 tile = {0};

    /*
     * Map a raw sensor value (say 0-1023) into the 24-bit fields.
     *
     *   gradient   = rate of change / magnitude band
     *   epsilon    = residual / fine detail
     *   confidence = how "sure" we are (based on value stability)
     *   context    = sensor type ID (1 = generic floor sensor)
     */

    /* Clamp to 0-1023 for 10-bit sensor */
    if (raw_value < 0) raw_value = 0;
    if (raw_value > 1023) raw_value = 1023;

    tile.balanced.scheme     = 0;  /* 00 = balanced */
    tile.balanced.gradient   = (raw_value >> 4) & 0x3F;   /* upper 6 bits */
    tile.balanced.epsilon    = raw_value & 0x3F;           /* lower 6 bits */
    tile.balanced.confidence = 32;                         /* mid confidence */
    tile.balanced.context    = 1;                          /* floor sensor */

    return tile;
}

/* ================================================================
 * Build the question string from tile fields
 * ================================================================ */
static void build_answer(Tile24 tile, char *out, size_t outsz) {
    snprintf(out, outsz,
             "value=%u conf=%u grad=%u eps=%u ctx=%u scheme=%u",
             tile.raw,
             (unsigned)tile.balanced.confidence,
             (unsigned)tile.balanced.gradient,
             (unsigned)tile.balanced.epsilon,
             (unsigned)tile.balanced.context,
             (unsigned)tile.balanced.scheme);
}

/* ================================================================
 * POST JSON payload to the floor room via raw POSIX sockets
 * Returns 0 on success, -1 on error.
 * ================================================================ */
static int post_tile(const char *json_body) {
    int sock = -1, ret = -1;
    struct sockaddr_in server;
    struct hostent *he;
    char req[8192];
    char resp[4096];
    ssize_t n;

    /* Resolve hostname */
    he = gethostbyname(HOST);
    if (!he) {
        fprintf(stderr, "[micro] ERROR: cannot resolve %s\n", HOST);
        return -1;
    }

    /* Create socket */
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("[micro] ERROR: socket");
        return -1;
    }

    server.sin_family = AF_INET;
    server.sin_port   = htons(PORT);
    memcpy(&server.sin_addr, he->h_addr_list[0], he->h_length);

    /* Connect */
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        fprintf(stderr, "[micro] ERROR: connect %s:%d: %s\n",
                HOST, PORT, strerror(errno));
        goto cleanup;
    }

    /* Build HTTP POST request */
    {
        int len = strlen(json_body);
        int nw = snprintf(req, sizeof(req),
            "POST %s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n"
            "\r\n"
            "%s",
            PATH, HOST, PORT, len, json_body);

        if (nw < 0 || (size_t)nw >= sizeof(req)) {
            fprintf(stderr, "[micro] ERROR: request too large\n");
            goto cleanup;
        }
    }

    /* Send request */
    n = send(sock, req, strlen(req), 0);
    if (n < 0) {
        perror("[micro] ERROR: send");
        goto cleanup;
    }

    /* Read response (don't care about body, just status) */
    n = recv(sock, resp, sizeof(resp) - 1, 0);
    if (n > 0) {
        resp[n] = '\0';
        /* Log response status line if verbose */
        char *status_line = strtok(resp, "\r\n");
        if (status_line) {
            fprintf(stderr, "[micro] response: %s\n", status_line);
        }
    }

    ret = 0;

cleanup:
    if (sock >= 0) close(sock);
    return ret;
}

/* ================================================================
 * Print usage
 * ================================================================ */
static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [interval_sec] [sensor_file]\n"
        "\n"
        "  interval_sec   polling interval in seconds (default: %d)\n"
        "  sensor_file    path to sensor value file\n"
        "                 (if omitted, reads one value from stdin and exits)\n"
        "\n"
        "Environment:\n"
        "  FLOOR_HOST     target host  (default: localhost)\n"
        "  FLOOR_PORT     target port  (default: %d)\n"
        "\n",
        prog, DEFAULT_INTERVAL, PORT);
}

/* ================================================================
 * Main
 * ================================================================ */
int main(int argc, char **argv) {
    int interval = DEFAULT_INTERVAL;
    int sensor_val;
    Tile24 tile;
    char answer[256];
    char json[1024];
    const char *sensor_file = NULL;
    const char *prog = argv[0] ? argv[0] : "micro-agent";

    /* Parse args */
    if (argc > 1 && (!strcmp(argv[1], "-h") || !strcmp(argv[1], "--help"))) {
        usage(prog);
        return 0;
    }

    if (argc > 1) interval = atoi(argv[1]);
    if (interval < 1) {
        fprintf(stderr, "[micro] interval must be >= 1 second\n");
        return 1;
    }
    if (argc > 2) sensor_file = argv[2];

    fprintf(stderr, "[micro] starting — interval=%ds sensor=%s\n",
            interval, sensor_file ? sensor_file : "(stdin)");

    for (int cycle = 0; ; cycle++) {
        /* 1. Read sensor */
        sensor_val = read_sensor(sensor_file);
        if (sensor_val < 0) {
            fprintf(stderr, "[micro] WARNING: no sensor reading on cycle %d\n", cycle);
            sensor_val = 0;
        }

        /* 2. Encode tile */
        tile = encode_tile(sensor_val);

        /* 3. Build JSON */
        build_answer(tile, answer, sizeof(answer));
        snprintf(json, sizeof(json),
            "{\"question\":\"floor reading\","
            "\"answer\":\"%s\","
            "\"source\":\"micro-agent\","
            "\"confidence\":0.5}",
            answer);

        fprintf(stderr, "[micro] cycle %d — value=%d raw=0x%06X => %s\n",
                cycle, sensor_val, (unsigned)(tile.raw & 0xFFFFFF), answer);

        /* 4. POST */
        if (post_tile(json) < 0) {
            fprintf(stderr, "[micro] WARNING: POST failed on cycle %d\n", cycle);
        }

        /* 5. Wait */
        if (!sensor_file) {
            /* Single read from stdin — done */
            fprintf(stderr, "[micro] single read complete, exiting.\n");
            break;
        }

        sleep(interval);
    }

    return 0;
}
