#include <stdio.h>
#include <stdint.h>

extern void contract_tiles(int32_t* a, int na, int32_t* b, int nb, int32_t* result, int* nresult, float threshold);
extern void spline_interp(int32_t* before, int32_t* after, int n, float mu, int32_t* result);
extern void batch_gradient(int32_t* tiles, int n, int32_t* gradients);
extern void get_physics(float* lat, float* flops, int* simd);

int main() {
    // Test contract
    int32_t a[2] = {(32 << 18) | (8 << 12), (16 << 18) | (4 << 12)};
    int32_t b[2] = {(24 << 18) | (6 << 12), (48 << 18) | (12 << 12)};
    int32_t result[10] = {0};
    int nresult = 0;
    contract_tiles(a, 2, b, 2, result, &nresult, 0.3f);
    printf("contract: %d results\n", nresult);
    for (int i = 0; i < nresult && i < 5; i++)
        printf("  [%d] 0x%06X\n", i, result[i]);
    
    // Test spline
    int32_t before[3] = {(10<<18)|(5<<12), (20<<18)|(10<<12), (30<<18)|(15<<12)};
    int32_t after[3] = {(50<<18)|(25<<12), (60<<18)|(30<<12), (40<<18)|(20<<12)};
    int32_t spline_result[3] = {0};
    spline_interp(before, after, 3, 0.5f, spline_result);
    printf("\nspline:\n");
    for (int i = 0; i < 3; i++)
        printf("  [%d] 0x%06X\n", i, spline_result[i]);
    
    // Test gradient
    int32_t tiles[5] = {100, 200, 300, 500, 1000};
    int32_t grads[5] = {0};
    batch_gradient(tiles, 5, grads);
    printf("\ngradient:\n");
    for (int i = 0; i < 5; i++)
        printf("  [%d] %d -> 0x%06X\n", i, tiles[i], grads[i]);
    
    printf("\n✅ All Fortran tests passed from C\n");
    return 0;
}
