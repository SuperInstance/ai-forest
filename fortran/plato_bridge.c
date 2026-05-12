/* C Bridge for Neural PLATO — handles POSIX sockets so Fortran can focus on compute.
 *
 * Fortran handles the array operations (seed cycle, contract, evaluation).
 * C handles the PLATO HTTP I/O (read tiles, write tiles).
 * The bridge: C reads tiles → hands arrays to Fortran → C writes results back.
 *
 * This is the sensory/motor cortex. Fortran is the neocortex.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>

#define BUFSIZE 65536
#define PLATO_HOST "localhost"
#define PLATO_PORT 8847

/* ─── Internal: raw HTTP request ──────────────────────────────────────── */
static char *http_request(const char *method, const char *path, const char *body) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return NULL;

    struct hostent *server = gethostbyname(PLATO_HOST);
    if (!server) { close(sock); return NULL; }

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    memcpy(&addr.sin_addr.s_addr, server->h_addr, server->h_length);
    addr.sin_port = htons(PLATO_PORT);

    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) { close(sock); return NULL; }

    char req[BUFSIZE];
    int reqlen;
    if (body) {
        reqlen = snprintf(req, BUFSIZE,
            "%s %s HTTP/1.1\r\nHost: %s:%d\r\nContent-Type: application/json\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n%s",
            method, path, PLATO_HOST, PLATO_PORT, strlen(body), body);
    } else {
        reqlen = snprintf(req, BUFSIZE,
            "%s %s HTTP/1.1\r\nHost: %s:%d\r\nConnection: close\r\n\r\n",
            method, path, PLATO_HOST, PLATO_PORT);
    }

    send(sock, req, reqlen, 0);

    static char resp[BUFSIZE];
    int total = 0, n;
    while ((n = read(sock, resp + total, BUFSIZE - total - 1)) > 0)
        total += n;
    resp[total] = 0;
    close(sock);

    /* Extract body after \r\n\r\n */
    char *body_start = strstr(resp, "\r\n\r\n");
    return body_start ? body_start + 4 : resp;
}

/* ─── Read tiles from a PLATO room ───────────────────────────────────── */
int plato_read_tiles(const char *room, int *buffer, int max_tiles) {
    char path[256];
    snprintf(path, sizeof(path), "/room/%s?limit=%d", room, max_tiles);
    
    char *resp = http_request("GET", path, NULL);
    if (!resp) return 0;

    /* Parse JSON response — count "question" fields, hash them into buffer */
    int count = 0;
    char *p = resp;
    while ((p = strstr(p, "\"question\"")) && count < max_tiles) {
        p = strstr(p, "\"") + 1;  /* move past first quote */
        p = strstr(p, "\"") + 1;  /* move to content */
        char *end = strstr(p, "\"");
        if (end) {
            /* Simple hash of question text */
            unsigned long h = 5381;
            for (char *c = p; c < end; c++)
                h = ((h << 5) + h) + *c;
            buffer[count++] = (int)(h & 0x7FFFFFFF);
        }
        p = end ? end + 1 : p + 1;
    }
    return count;
}

/* ─── Write a single tile to a PLATO room ─────────────────────────────── */
int plato_write_tile(const char *room, const char *question, const char *answer,
                     const char *source, double confidence) {
    char body[BUFSIZE];
    int blen = snprintf(body, BUFSIZE,
        "{\"room\":\"%s\",\"question\":\"%s\",\"answer\":\"%s\",\"source\":\"%s\",\"confidence\":%.2f}",
        room, question, answer, source, confidence);

    char path[256];
    snprintf(path, sizeof(path), "/room/%s/submit", room);
    
    char *resp = http_request("POST", path, body);
    if (!resp) return 0;

    return strstr(resp, "\"accepted\"") ? 1 : 0;
}

/* ─── Get PLATO status — return tile count ────────────────────────────── */
int plato_tile_count(const char *room) {
    char path[256];
    snprintf(path, sizeof(path), "/room/%s?limit=1", room);
    
    char *resp = http_request("GET", path, NULL);
    if (!resp) return 0;

    /* Count tiles by counting "question" occurrences */
    int count = 0;
    char *p = resp;
    while ((p = strstr(p, "\"question\""))) { count++; p += 10; }
    return count;
}
