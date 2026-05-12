#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

/* C bridge */
int plato_read_tiles(const char *room, int *buffer, int max_tiles);
int plato_write_tile(const char *room, const char *question, const char *answer,
                     const char *source, double confidence);

/* Inline RNG — matches Fortran seed_cycle logic */
static unsigned long long rng_state = 42;

static int rng_int(int max) {
    rng_state = (rng_state * 6364136223846793005ULL + 1442695040888963407ULL) % 9223372036854775807ULL;
    return (int)(rng_state % (unsigned long long)max);
}

/* Fisher-Yates shuffle — same as Fortran seed_permute */
static void seed_permute(int *tiles, int n) {
    for (int i = n - 1; i > 0; i--) {
        int j = rng_int(i + 1);
        int tmp = tiles[i];
        tiles[i] = tiles[j];
        tiles[j] = tmp;
    }
}

/* Blend each tile with a random partner — same as Fortran seed_blend */
static void seed_blend(int *tiles, int n, int mu) {
    for (int i = 0; i < n; i++) {
        int partner = rng_int(n);
        long long diff = (long long)(tiles[partner] - tiles[i]) * (long long)mu / 1024;
        tiles[i] += (int)diff;
    }
}

/* Add noise — same as Fortran seed_perturb */
static void seed_perturb(int *tiles, int n, int magnitude) {
    for (int i = 0; i < n; i++) {
        int noise = rng_int(magnitude * 2 + 1) - magnitude;
        tiles[i] += noise;
    }
}

/* Adversarial filter — same as Fortran seed_filter */
static int seed_filter(int *tiles, int n, int threshold, int *out) {
    int n_out = 0;
    for (int i = 0; i < n; i++) {
        int diff = 0;
        for (int j = i - 3; j <= i + 3 && j < n; j++) {
            if (j >= 0 && j != i && abs(tiles[i] - tiles[j]) > threshold)
                diff++;
        }
        if (diff >= 2)
            out[n_out++] = tiles[i];
    }
    return n_out;
}

/* Full seed cycle — matches Fortran seed_cycle */
static int seed_cycle(int *tiles, int n, int seed, int mu, int mag, int thresh, int *out) {
    rng_state = seed;
    seed_permute(tiles, n);
    seed_blend(tiles, n, mu);
    seed_perturb(tiles, n, mag);
    return seed_filter(tiles, n, thresh, out);
}

int main(int argc, char **argv) {
    const char *room = argc > 1 ? argv[1] : "tension";
    int interval = argc > 2 ? atoi(argv[2]) : 30;
    int cycle = 0;

    printf("Neural PLATO Daemon (C)\n");
    printf("  Room: %s/\n", room);
    printf("  Interval: %ds\n", interval);
    printf("  Seed cycle: C implementation (no Fortran interop needed)\n");
    printf("  PLATO I/O: C bridge (POSIX sockets)\n\n");

    while (1) {
        cycle++;
        int buf[1024];
        int variants[1024];

        int n = plato_read_tiles(room, buf, 500);
        if (n == 0) { printf("[%d] No tiles\n", cycle); sleep(interval); continue; }

        /* Copy buf to a mutable array for seed_cycle */
        int work[1024];
        memcpy(work, buf, n * sizeof(int));

        int nv = seed_cycle(work, n, 42 + cycle, 512, 100, 5000, variants);
        if (nv > 100) nv = 100;

        int written = 0;
        for (int i = 0; i < nv && i < 15; i++) {
            char q[128], a[128];
            snprintf(q, sizeof(q), "neural v%d c%d", i, cycle);
            snprintf(a, sizeof(a), "v=0x%08X from %s", variants[i], room);
            if (plato_write_tile("neural-inference", q, a, "c-daemon", 0.85))
                written++;
        }

        printf("[%d] %d tiles → %d variants → wrote %d\n", cycle, n, nv, written);
        fflush(stdout);
        sleep(interval);
    }
    return 0;
}
