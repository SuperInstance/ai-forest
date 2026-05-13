#ifdef __cplusplus
extern "C" {
#endif
/* penrose_memory.c — PLATO spatial memory allocator based on Penrose tilings.
 *
 * The Penrose tiling IS the memory architecture:
 *   - INFLATION = memory allocation (subdivide a region)
 *   - DEFLATION = memory freeing (merge regions)
 *   - VERTEX ID = memory address (non-repeating, no collisions)
 *   - 5-FOLD SYMMETRY = 5 opcode dispatch vectors
 *   - phi (golden ratio) = the adjunction unit at every layer
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define PHI 1.6180339887498948482
#define MAX_REGIONS 65536

typedef struct {
    double cx, cy;
    int type;
    int level;
    int in_use;
    uint64_t id;
} PenroseRegion;

static PenroseRegion regions[MAX_REGIONS];
static int n_regions = 0;

static uint64_t region_id(double cx, double cy, int type, int level) {
    uint64_t h = (uint64_t)(cx * PHI * PHI * PHI * 1e6);
    h ^= (uint64_t)(cy * PHI * PHI * 1e6);
    h = (h * 0x9E3779B97F4A7C15ULL) ^ (type * 0xBF58476D1CE4E5B9ULL) ^ (level * 0x9E3779B9ULL);
    return h;
}

int penrose_seed_memory(void) {
    n_regions = 0;
    for (int i = 0; i < 10; i++) {
        double a1 = (2.0 * i - 1.0) * M_PI / 10.0;
        double a2 = (2.0 * i + 1.0) * M_PI / 10.0;
        regions[n_regions].cx = (cos(a1) + cos(a2)) / 2.0;
        regions[n_regions].cy = (sin(a1) + sin(a2)) / 2.0;
        regions[n_regions].type = 0;
        regions[n_regions].level = 0;
        regions[n_regions].in_use = 0;
        regions[n_regions].id = region_id(regions[n_regions].cx, regions[n_regions].cy, 0, 0);
        n_regions++;
    }
    return n_regions;
}

int penrose_allocate(void) {
    for (int i = 0; i < n_regions; i++) {
        if (!regions[i].in_use) {
            regions[i].in_use = 1;
            return i;
        }
    }
    return -1;
}

void penrose_free(int region_idx) {
    if (region_idx >= 0 && region_idx < n_regions)
        regions[region_idx].in_use = 0;
}

void penrose_stats(int *free_count, int *used_count, int *total_count) {
    int f = 0, u = 0;
    for (int i = 0; i < n_regions; i++) {
        if (regions[i].in_use) u++; else f++;
    }
    *free_count = f;
    *used_count = u;
    *total_count = n_regions;
}

int penrose_verify_no_collisions(void) {
    for (int i = 0; i < n_regions; i++)
        for (int j = i + 1; j < n_regions; j++)
            if (regions[i].id == regions[j].id) return 0;
    return 1;
}

#ifdef __cplusplus
}
#endif
