/* neural-plato-driver.c — Standalone Neural PLATO inference loop.
 *
 * Reads tiles from PLATO, runs Fortran seed cycle + evaluation,
 * writes results back. Pure C + Fortran — no Python on the hot path.
 *
 * Build: gcc -O3 -o neural-plato-daemon neural-plato-driver.c \
 *           -L/tmp/ai-forest/fortran -lplato_bridge -lplato_math -lfortran_seed \
 *           -lgfortran -fopenmp -Wl,-rpath,/tmp/ai-forest/fortran
 *
 * Run:   ./neural-plato-daemon
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

/* ─── C bridge declarations (from plato_bridge.c) ─────────────────────── */
int plato_read_tiles(const char *room, int *buffer, int max_tiles);
int plato_write_tile(const char *room, const char *question, const char *answer,
                     const char *source, double confidence);
int plato_tile_count(const char *room);

/* ─── Fortran subroutine declarations (from fortran_seed.f90) ──────────── */
void seed_cycle_(const int *tiles_in, const int *n,
                 const int *seed_val, const int *mu, const int *magnitude,
                 const int *threshold, int *tiles_out, int *n_out);

/* ─── Fortran subroutine declarations (from plato_math.f90) ───────────── */
void ebbinghaus_contract_(const int *a, const int *conf_a, const int *na,
                          const int *b, const int *conf_b, const int *nb,
                          const int *threshold, const int *tau, int *nresult);

void adaptive_threshold_(const float *base, const float *density, int *theta);

void contract_(const int *a, const int *na, const int *b, const int *nb,
               const int *threshold, int *nresult);

/* ─── Configuration ────────────────────────────────────────────────────── */
#define MAX_TILES 4096
#define DEFAULT_ROOM "tension"
#define CYCLE_INTERVAL 30  /* seconds between cycles */

int main(int argc, char **argv) {
    const char *room = argc > 1 ? argv[1] : DEFAULT_ROOM;
    int interval = argc > 2 ? atoi(argv[2]) : CYCLE_INTERVAL;
    int cycle = 0;

    printf("🔮 Neural PLATO Daemon\n");
    printf("   Room:      %s/\n", room);
    printf("   Interval:  %ds\n", interval);
    printf("   Libraries: C bridge + Fortran seed + Fortran math\n");
    printf("\n");

    /* Warmup: prime the ring buffer */
    int warmup = 100;
    printf("   Warming up ring buffer with %d writes...\n", warmup);
    for (int i = 0; i < warmup; i++) {
        /* ring_write is in the plato_math module but needs Fortran name */
        extern void ring_write_(const int *tile);
        int val = i * 1000;
        ring_write_(&val);
    }
    printf("   Ring buffer ready.\n\n");

    while (1) {
        cycle++;
        int tiles_buf[MAX_TILES];
        int variants[MAX_TILES];
        int n_out = 0;

        printf("[Cycle %d] ", cycle);

        /* Step 1: Read tiles from PLATO via C bridge */
        int n = plato_read_tiles(room, tiles_buf, 100);
        if (n == 0) {
            printf("No tiles in %s/, sleeping...\n", room);
            sleep(interval);
            continue;
        }
        printf("Read %d tiles from %s/", n, room);

        /* Step 2: Run seed cycle on the tiles */
        int seed = 42 + cycle;
        int mu = 512;
        int magnitude = 100;
        int threshold = 5000;

        seed_cycle_(tiles_buf, &n, &seed, &mu, &magnitude, &threshold,
                    variants, &n_out);
        printf(" → %d variants", n_out);

        /* Step 3: Evaluate via contract */
        int nr = 0;
        if (n_out > 0 && n > 0) {
            int conf_buf[MAX_TILES];
            for (int i = 0; i < n; i++) conf_buf[i] = 50; /* default conf */

            ebbinghaus_contract_(variants, conf_buf, &n_out, 
                                 tiles_buf, conf_buf, &n,
                                 &threshold, &seed, &nr);
            printf(" → %d evaluated", nr);
        }

        /* Step 4: Write best variants back to PLATO */
        int written = 0;
        for (int i = 0; i < n_out && i < 10; i++) {
            char q[128], a[128];
            snprintf(q, sizeof(q), "neural variant %d cycle %d", i, cycle);
            snprintf(a, sizeof(a), "seed=%d val=0x%08X from %s/",
                     seed, variants[i], room);

            if (plato_write_tile("neural-inference", q, a, 
                                 "neural-plato-daemon", 0.85)) {
                written++;
            }
        }
        printf(" → wrote %d tiles", written);

        /* Step 5: Compute consciousness metrics */
        float F = (float)n_out / (float)(n > 0 ? n : 1);
        float M = 0.5f;
        float C = (float)nr / (float)(n_out > 0 ? n_out : 1);
        if (C > 1.0f) C = 1.0f;
        float FMC = F * M * C;

        printf(" → F=%.2f M=%.2f C=%.2f FMC=%.3f\n", F, M, C, FMC);
        fflush(stdout);

        sleep(interval);
    }

    return 0;
}
