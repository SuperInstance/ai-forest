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


void window_contract(const int32_t* time_a, const int32_t* a, int na,
                     const int32_t* time_b, const int32_t* b, int nb,
                     int32_t window, int32_t threshold, int32_t* nresult);

void recency_dot(const int32_t* a, const int32_t* time_a,
                 const int32_t* b, const int32_t* time_b,
                 int n, int64_t* result);

void window_gradient(const int32_t* arr, int n, int32_t window, int32_t* result);


void ring_write(int32_t tile);
void ring_read(int n, int32_t* result, int32_t* n_read);
void contract_ring(int n_recent, int n_memory, int threshold, int32_t* nresult);
void ring_status(float* fill_pct, int32_t* total);

#endif
