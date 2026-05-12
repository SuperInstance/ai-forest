/* plato_http.c — POSIX socket HTTP client for PLATO server
 *
 * Exposes two C-callable functions for Fortran:
 *   plato_get_tiles()  — GET /room/<name>/tiles, parse into int32 array
 *   plato_post_tile()  — POST /room/<name>/submit with JSON body
 *
 * Both use raw POSIX sockets (like micro.c) — no libcurl dependency.
 *
 * Build: gcc -O2 -fPIC -c plato_http.c && gfortran ... plato_http.o
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <errno.h>
#include <time.h>

/* ================================================================
 * Constants
 * ================================================================ */
#define PLATO_HOST  "127.0.0.1"
#define PLATO_PORT  8847
#define MAX_RESPONSE (256 * 1024)  /* 256KB response buffer */
#define MAX_TILES    (64 * 1024)    /* max 64K tiles per read */

/* ================================================================
 * Low-level socket helpers
 * ================================================================ */

static int http_connect(void) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return -1;

    struct sockaddr_in server;
    memset(&server, 0, sizeof(server));
    server.sin_family = AF_INET;
    server.sin_port   = htons(PLATO_PORT);
    server.sin_addr.s_addr = inet_addr(PLATO_HOST);

    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        close(sock);
        return -1;
    }
    return sock;
}

static int http_request(int sock, const char *req) {
    ssize_t n = send(sock, req, strlen(req), 0);
    return (n > 0) ? 0 : -1;
}

/* Read full HTTP response into heap-allocated buffer, returns body offset */
/* Caller must free() the returned pointer. */
static char *http_read_body(int sock, int *out_len, int *body_off) {
    int cap = 65536;
    int total = 0;
    char *buf = malloc(cap);
    if (!buf) return NULL;
    
    ssize_t n;
    while ((n = recv(sock, buf + total, cap - total - 1, 0)) > 0) {
        total += n;
        if (total >= cap - 1) {
            cap *= 2;
            char *nb = realloc(buf, cap);
            if (!nb) { free(buf); return NULL; }
            buf = nb;
        }
    }
    buf[total] = '\0';
    *out_len = total;
    
    /* Find header-body boundary */
    const char *hdr = strstr(buf, "\r\n\r\n");
    *body_off = hdr ? (int)(hdr - buf + 4) : 0;
    return buf;
}

/* ================================================================
 * Extract JSON body from HTTP response (skip headers)
 * ================================================================ */

/* ================================================================
 * Parse tiles from JSON response
 *
 * JSON format: {"tiles":[{"_hash": "...","confidence":...,...},...]}
 * We extract _hash values as 24-bit ints
 * ================================================================ */
static int parse_tiles_json(const char *json, int32_t *tiles, int max_tiles) {
    int n = 0;
    const char *p = json;
    int32_t hash_val;

    while (n < max_tiles && (p = strstr(p, "\"_hash\": \"")) != NULL) {
        p += 10; /* skip past "_hash": " */
        /* Parse the 8-char hex hash */
        char hex[9];
        int i;
        for (i = 0; i < 8 && p[i] && p[i] != '"'; i++) {
            hex[i] = p[i];
        }
        hex[i] = '\0';
        if (i == 8) {
            hash_val = (int32_t)strtoul(hex, NULL, 16) & 0x00FFFFFF;
            tiles[n++] = hash_val;
        }
        /* Also look for "confidence" value to encode as tile */
        p = strstr(p, "\"confidence\":");
        if (p) {
            p += 13;
            double conf = strtod(p, (char**)&p);
            /* Encode hash + confidence as single 24-bit value */
            int32_t conf_int = (int32_t)(conf * 63.0) & 0x3F;  /* 6 bits confidence */
            tiles[n-1] = (tiles[n-1] & 0xFFFFC0) | conf_int;
        }
    }
    return n;
}

/* ================================================================
 * plato_get_tiles() — C-callable: fetch tiles from PLATO room
 *
 * Arguments (all passed by pointer for Fortran interop):
 *   room_name     — null-terminated room name string
 *   tiles_out     — output int32 array (caller allocates MAX_TILES)
 *   n_tiles       — output: number of tiles received
 *
 * Returns 0 on success, -1 on error.
 * ================================================================ */
int plato_get_tiles_c(const char *room_name, int32_t *tiles_out, int32_t *n_tiles) {
    char req[4096];
    int sock;
    int ret = -1;
    char *resp = NULL;
    int body_off, total;

    *n_tiles = 0;


    sock = http_connect();
    if (sock < 0) {
        fprintf(stderr, "[plato_http] connect failed\n");
        return -1;
    }

    /* Build GET request */
    snprintf(req, sizeof(req),
        "GET /room/%s/tiles HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Connection: close\r\n"
        "\r\n",
        room_name, PLATO_HOST, PLATO_PORT);



    if (http_request(sock, req) < 0) {
        fprintf(stderr, "[plato_http] send failed\n");
        goto cleanup;
    }

    resp = http_read_body(sock, &total, &body_off);
    if (!resp || total <= 0) {
    
        goto cleanup;
    }


    *n_tiles = parse_tiles_json(resp + body_off, tiles_out, MAX_TILES);

    ret = 0;

cleanup:
    free(resp);
    close(sock);
    return ret;
}

/* ================================================================
 * plato_post_tile() — C-callable: submit a tile to PLATO room
 *
 * Arguments:
 *   room_name  — null-terminated room name string
 *   question   — null-terminated question string
 *   answer     — null-terminated answer string
 *   confidence — float confidence value
 *
 * Returns 0 on success, -1 on error.
 * ================================================================ */
int plato_post_tile_c(const char *room_name, const char *question,
                    const char *answer, float confidence) {
    char json_body[32768];
    char req[65536];
    int sock;
    int ret = -1;
    char *resp = NULL;
    int total, body_off;

    sock = http_connect();
    if (sock < 0) return -1;

    /* Build JSON body */
    snprintf(json_body, sizeof(json_body),
        "{\"question\":\"%s\",\"answer\":\"%s\",\"source\":\"neural-plato\",\"confidence\":%.2f}",
        question, answer, confidence);

    int body_len = strlen(json_body);
    snprintf(req, sizeof(req),
        "POST /room/%s/submit HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n"
        "%s",
        room_name, PLATO_HOST, PLATO_PORT, body_len, json_body);

    if (http_request(sock, req) < 0) goto cleanup;

    resp = http_read_body(sock, &total, &body_off);
    ret = 0;

cleanup:
    free(resp);
    close(sock);
    return ret;
}

/* ================================================================
 * plato_post_tile_json() — C-callable: submit a pre-formatted JSON tile
 *
 * Arguments:
 *   room_name  — null-terminated room name string
 *   json_len   — length of JSON body
 *   json_body  — pre-formatted JSON string
 *
 * Returns 0 on success, -1 on error.
 * ================================================================ */
int plato_post_tile_json_c(const char *room_name, int32_t json_len, const char *json_body) {
    char req[65536];
    int sock;
    int ret = -1;
    char *resp = NULL;
    int total, body_off;
    int body_len = (int)json_len;

    sock = http_connect();
    if (sock < 0) return -1;

    snprintf(req, sizeof(req),
        "POST /room/%s/submit HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n"
        "%s",
        room_name, PLATO_HOST, PLATO_PORT, body_len, json_body);

    if (http_request(sock, req) < 0) goto cleanup;

    resp = http_read_body(sock, &total, &body_off);
    ret = 0;

cleanup:
    free(resp);
    close(sock);
    return ret;
}


/* Fortran-safe wrapper: takes string buffer + length instead of C string */
/* This avoids Fortran-to-C string interop issues */
int plato_get_tiles(const char *name_buf, int32_t *name_len, 
                     int32_t *tiles_out, int32_t *n_tiles) {
    /* Copy Fortran buffer into a null-terminated C string */
    int len = *name_len;
    if (len < 0) len = 0;
    if (len > 1023) len = 1023;
    char local_name[1024];
    int i;
    for (i = 0; i < len; i++) {
        local_name[i] = name_buf[i];
    }
    local_name[len] = '\0';
    
    /* Debug: write first 32 chars to make sure we got the right data */
    write(2, "[plato_http] name='", 20);
    write(2, local_name, len < 32 ? len : 32);
    write(2, "' len=", 6);
    char dbg[16];
    snprintf(dbg, 16, "%d\n", len);
    write(2, dbg, strlen(dbg));
    
    /* Call the internal implementation */
    return plato_get_tiles_c(local_name, tiles_out, n_tiles);
}

/* Fortran-safe wrapper for plato_post_tile */
/* Takes buffers + lengths instead of C strings */
int plato_post_tile(const char *rm_buf, int32_t *rm_len,
                    const char *q_buf, int32_t *q_len,
                    const char *a_buf, int32_t *a_len,
                    float *conf) {
    char rm[256], q[256], a[256];
    int rml = *rm_len > 255 ? 255 : *rm_len;
    int ql = *q_len > 255 ? 255 : *q_len;
    int al = *a_len > 255 ? 255 : *a_len;
    memcpy(rm, rm_buf, rml); rm[rml] = '\0';
    memcpy(q, q_buf, ql); q[ql] = '\0';
    memcpy(a, a_buf, al); a[al] = '\0';
    return plato_post_tile_c(rm, q, a, *conf);
}

/* Fortran-safe wrapper for plato_post_tile_json */
int plato_post_tile_json(const char *rm_buf, int32_t *rm_len,
                         int32_t *json_len, const char *json_buf) {
    char rm[256];
    int rml = *rm_len > 255 ? 255 : *rm_len;
    memcpy(rm, rm_buf, rml); rm[rml] = '\0';
    return plato_post_tile_json_c(rm, *json_len, json_buf);
}
