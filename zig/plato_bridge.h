// Auto-generated C header for Fortran .so bindings.
// Generated from plato_math.f90 subroutines with bind(c).

#ifndef PLATO_BRIDGE_H
#define PLATO_BRIDGE_H

#include <stdint.h>

void contract(const int32_t* a, int na, const int32_t* b, int nb,
              int32_t threshold, int32_t* nresult);

void dot(const int32_t* a, const int32_t* b, int n, int64_t* result);

void spline(const int32_t* before, const int32_t* after, int n,
            int32_t mu, int32_t* result);

void gradient(const int32_t* arr, int n, int32_t* result);

void filter_val(const int32_t* arr, int n, int32_t target, int32_t tolerance,
                int32_t* indices, int32_t* n_found);

void physics(float* latency_ns, float* flops, int32_t* simd_bits);

#endif
