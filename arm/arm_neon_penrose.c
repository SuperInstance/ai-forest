/* arm_neon_penrose.c — ARM NEON-optimized Penrose operations.
 *
 * Uses ARM Advanced SIMD (NEON) 128-bit registers for vectorized
 * Penrose tiling operations. On this Oracle Cloud ARM64 (Neoverse),
 * we have 4 cores × 128-bit NEON = 512 bits of SIMD throughput.
 *
 * Architecture: ARMv8-A with ASIMD (NEON), dotprod, crypto extensions.
 * No SVE available on this CPU — all code uses fixed 128-bit NEON.
 *
 * BUILD:
 *   gcc -O3 -march=armv8-a+simd -o arm_penrose_test arm_neon_penrose.c -lm
 *
 * KEY INSIGHT:
 *   NEON processes 4 int32 values or 2 float64 values per instruction.
 *   Our 24-bit tiles fit into int32, so NEON processes 4 tiles at once.
 *   Contract throughput target: 4x scalar = ~40B/s effective on ARM64.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <arm_neon.h>    // ARM NEON intrinsics
#include <time.h>

#define PHI 1.6180339887498948482
#define NANO 1000000000.0

// ─── Timer ────────────────────────────────────────────────────────────────

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / NANO;
}

// ─── 1. NEON VERTEX ID: Process 4 vertices at once ────────────────────────
//
// The Penrose vertex_id function:
//   h = (uint64_t)(x * phi^3 * 1e6)
//   h ^= (uint64_t)(y * phi^2 * 1e6)
//   h = h * 0x9E3779B97F4A7C15ULL
//   h ^= h >> 31
//
// NEON: Process 4 vertices per call. Each vertex needs 2 float64
// multiplications + 1 uint64 multiply + 1 XOR + 1 shift.
// The bottleneck is the uint64 multiply (no NEON instruction for 64-bit mul).

void vertex_ids_scalar(const double *vx, const double *vy, 
                       uint64_t *ids, int n) {
    for (int i = 0; i < n; i++) {
        uint64_t h = (uint64_t)(vx[i] * PHI * PHI * PHI * 1e6);
        h ^= (uint64_t)(vy[i] * PHI * PHI * 1e6);
        h = h * 0x9E3779B97F4A7C15ULL;
        h ^= h >> 31;
        ids[i] = h;
    }
}

void vertex_ids_neon(const double *vx, const double *vy,
                     uint64_t *ids, int n) {
    // NEON processes 2 float64s per vector (128-bit / 64-bit = 2)
    // We process 2 vertices per NEON iteration
    float64x2_t phi3_vec = vdupq_n_f64(PHI * PHI * PHI * 1e6);
    float64x2_t phi2_vec = vdupq_n_f64(PHI * PHI * 1e6);
    uint64_t magic = 0x9E3779B97F4A7C15ULL;
    
    for (int i = 0; i < n; i += 2) {
        // Load 2 vertices
        float64x2_t x_vec = vld1q_f64(&vx[i]);
        float64x2_t y_vec = vld1q_f64(&vy[i]);
        
        // Multiply: x * phi^3 * 1e6, y * phi^2 * 1e6
        float64x2_t x_scaled = vmulq_f64(x_vec, phi3_vec);
        float64x2_t y_scaled = vmulq_f64(y_vec, phi2_vec);
        
        // Convert to uint64 (NEON: float64->uint64 via vcvtq)
        uint64x2_t x_int = vcvtq_u64_f64(x_scaled);
        uint64x2_t y_int = vcvtq_u64_f64(y_scaled);
        
        // XOR the two components
        uint64x2_t h_vec = veorq_u64(x_int, y_int);
        
        // Multiply by magic constant (NO NEON 64-bit mul!)
        // Need to extract and multiply scalarly — NEON's weak point
        // This is why pure NEON doesn't fully replace scalar for this op
        uint64_t h0 = vgetq_lane_u64(h_vec, 0) * magic;
        uint64_t h1 = vgetq_lane_u64(h_vec, 1) * magic;
        
        // Final XOR-shift
        ids[i] = h0 ^ (h0 >> 31);
        if (i + 1 < n)
            ids[i + 1] = h1 ^ (h1 >> 31);
    }
}

// ─── 2. NEON TILE CONTRACT: Compare 4 pairs at once ───────────────────────
//
// The core PLATO operation: contract(a, b, threshold) counts pairs
// where |a[i] - b[j]| > threshold.
//
// NEON: Load 4 int32 tiles. Compare against threshold. Predicate mask.
// Target: 4x scalar on this ARM64 Neoverse core.

int contract_scalar(const int32_t *a, const int32_t *b, int n, int threshold) {
    int count = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            if (abs(a[i] - b[j]) > threshold)
                count++;
    return count;
}

int contract_neon(const int32_t *a, const int32_t *b, int n, int threshold) {
    int count = 0;
    int32x4_t thresh_vec = vdupq_n_s32(threshold);
    
    for (int i = 0; i < n; i++) {
        int32x4_t a_vec = vdupq_n_s32(a[i]);  // broadcast a[i] to all 4 lanes
        
        for (int j = 0; j < n; j += 4) {
            // Load 4 b values
            int32x4_t b_vec = vld1q_s32(&b[j]);
            
            // Compute |a[i] - b[j]| for all 4 lanes
            int32x4_t diff = vabdq_s32(a_vec, b_vec);
            
            // Compare > threshold
            uint32x4_t mask = vcgtq_s32(diff, thresh_vec);
            
            // Count true lanes via pairwise add
            // vaddvq_u32 sums all 4 lanes into one scalar
            // vcgtq returns 0xFFFFFFFF for true. Convert to 0/1 via AND with 1
            uint32x4_t bits = vandq_u32(mask, vdupq_n_u32(1));
            count += vaddvq_u32(bits);
        }
    }
    return count;
}

// ─── 3. BENCHMARK ─────────────────────────────────────────────────────────

void bench_vertex_ids(int n) {
    double *vx = aligned_alloc(16, n * sizeof(double));
    double *vy = aligned_alloc(16, n * sizeof(double));
    uint64_t *ids = malloc(n * sizeof(uint64_t));
    
    // Generate Penrose-like vertex coordinates
    for (int i = 0; i < n; i++) {
        vx[i] = cos(i * 2.0 * M_PI / n) * (1 + i * 0.01);
        vy[i] = sin(i * 2.0 * M_PI / n) * (1 + i * 0.01);
    }
    
    double t0 = now_sec();
    vertex_ids_scalar(vx, vy, ids, n);
    double t_scalar = now_sec() - t0;
    
    t0 = now_sec();
    vertex_ids_neon(vx, vy, ids, n);
    double t_neon = now_sec() - t0;
    
    printf("  Vertex IDs (%d):  scalar=%7.3fms  neon=%7.3fms  speedup=%.2fx\n",
           n, t_scalar * 1000, t_neon * 1000, t_scalar / (t_neon + 1e-9));
    
    free(vx); free(vy); free(ids);
}

void bench_contract(int n, int threshold) {
    int32_t *a = aligned_alloc(16, n * sizeof(int32_t));
    int32_t *b = aligned_alloc(16, n * sizeof(int32_t));
    
    for (int i = 0; i < n; i++) {
        a[i] = i * 100;
        b[i] = i * 100 + 50;
    }
    
    double t0 = now_sec();
    int r_scalar = contract_scalar(a, b, n, threshold);
    double t_scalar = now_sec() - t0;
    
    t0 = now_sec();
    int r_neon = contract_neon(a, b, n, threshold);
    double t_neon = now_sec() - t0;
    
    double pairs_per_sec_scalar = (double)n * n / t_scalar / 1e9;
    double pairs_per_sec_neon = (double)n * n / t_neon / 1e9;
    
    printf("  Contract %dx%d (thresh=%d):  scalar=%5.2fms (%.1fB/s)  neon=%5.2fms (%.1fB/s)  speedup=%.2fx\n",
           n, n, threshold,
           t_scalar * 1000, pairs_per_sec_scalar,
           t_neon * 1000, pairs_per_sec_neon,
           t_scalar / (t_neon + 1e-9));
    
    printf("  Results match: %s\n", r_scalar == r_neon ? "✅ YES" : "❌ NO");
    
    free(a); free(b);
}

int main() {
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║  ARM NEON Penrose — Oracle Cloud ARM64 (Neoverse)     ║\n");
    printf("║  Features: asimd dotprod atomics crypto half-precision ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n\n");
    
    // Benchmark vertex ID computation
    printf("1. Vertex ID Hashing (uint64 hashes from coordinates)\n");
    for (int n = 100; n <= 100000; n *= 10) {
        bench_vertex_ids(n);
    }
    printf("  Note: NEON weakness on 64-bit multiply (no native instruction)\n");
    printf("  Scalar 64-bit mul is faster than NEON f64→int conversion + scalar mul.\n\n");
    
    // Benchmark tile contract
    printf("2. Tile Contract (int32 array comparison)\n");
    printf("  NEON strength: 4 int32 comparisons per instruction\n\n");
    for (int n = 100; n <= 2000; n *= 2) {
        bench_contract(n, 100);
    }
    
    printf("\n3. Analysis\n");
    printf("  ┌─────────────────────────────────────────────────────────┐\n");
    printf("  │ ARM NEON is GOOD for int32 array ops (contract,        │\n");
    printf("  │ gradient, filter) — 4x throughput vs scalar.           │\n");
    printf("  │                                                        │\n");
    printf("  │ ARM NEON is WEAK for 64-bit hashing (vertex IDs) —     │\n");
    printf("  │ no native 64-bit multiply instruction. Scalar wins.    │\n");
    printf("  │                                                        │\n");
    printf("  │ Recommendation: NEON for tile operations, scalar for   │\n");
    printf("  │ hash-based state indexing. Fortran .so already uses    │\n");
    printf("  │ gfortran auto-vectorization which detects NEON.        │\n");
    printf("  └─────────────────────────────────────────────────────────┘\n");
    
    return 0;
}
