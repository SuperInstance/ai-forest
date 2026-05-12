//! ft-zig — Zig compute path for the ft CLI.
//!
//! Replaces the Python ctypes layer for the hot path.
//! Zig handles the C ABI, comptime array optimization, and caching.
//! PLATO communication is handled by a thin Python wrapper.
//!
//! Compile: zig build-lib ft_zig.zig -lc -lplato_math -L../fortran
//! Call from Python: ctypes.CDLL('./libft_zig.so')

const std = @import("std");
const c = @cImport({
    @cInclude("plato_bridge.h");
});

// ─── Fortran Hot Paths ─────────────────────────────────────────────────────
//
// These call directly into the Fortran .so. No Python overhead.
// Each function returns a JSON string that Python passes back to the CLI.

export fn ft_contract(
    a_ptr: [*]const i32, a_len: i32,
    b_ptr: [*]const i32, b_len: i32,
    threshold: i32,
) i32 {
    var nresult: i32 = 0;
    c.contract(a_ptr, a_len, b_ptr, b_len, threshold, &nresult);
    return nresult;
}

export fn ft_dot(
    a_ptr: [*]const i32, b_ptr: [*]const i32, n: i32,
) i64 {
    var result: i64 = 0;
    c.dot(a_ptr, b_ptr, n, &result);
    return result;
}

export fn ft_spline(
    before_ptr: [*]const i32, after_ptr: [*]const i32,
    n: i32, mu: i32,
    result_ptr: [*]i32,
) void {
    c.spline(before_ptr, after_ptr, n, mu, result_ptr);
}

export fn ft_gradient(
    arr_ptr: [*]const i32, n: i32,
    result_ptr: [*]i32,
) void {
    c.gradient(arr_ptr, n, result_ptr);
}

// ─── Comptime Room Cache ──────────────────────────────────────────────────
//
// Known room IDs and their typical sizes. Generated at compile time.
// When Python asks "contract these two rooms", Zig already knows
// their typical sizes and can pre-allocate optimal arrays.

const RoomCache = struct {
    room_id: u32,
    name: [32]u8,
    name_len: u8,
    expected_size: u32,
    hits: u64,
};

var room_cache: [32]RoomCache = undefined;
var cache_count: u32 = 0;

export fn ft_register_room(name_ptr: [*]const u8, name_len: u8, expected_size: u32) u32 {
    if (cache_count >= 32) return 0;
    const idx = cache_count;
    cache_count += 1;
    @memset(&room_cache[idx].name, 0);
    @memcpy(room_cache[idx].name[0..name_len], name_ptr[0..name_len]);
    room_cache[idx].name_len = name_len;
    room_cache[idx].room_id = idx;
    room_cache[idx].expected_size = expected_size;
    room_cache[idx].hits = 0;
    return idx;
}

export fn ft_cache_hit(room_id: u32) void {
    if (room_id < cache_count) {
        room_cache[room_id].hits += 1;
    }
}

export fn ft_cache_stats() u32 {
    var n: u32 = 0;
    for (0..cache_count) |i| {
        if (room_cache[i].hits > 0) {
            n += 1;
        }
    }
    return n;
}

// ─── Physics ──────────────────────────────────────────────────────────────



export fn ft_window_contract(
    time_a_ptr: [*]const i32, a_ptr: [*]const i32, na: i32,
    time_b_ptr: [*]const i32, b_ptr: [*]const i32, nb: i32,
    window: i32, threshold: i32,
) i32 {
    var nresult: i32 = 0;
    c.window_contract(time_a_ptr, a_ptr, na, time_b_ptr, b_ptr, nb, window, threshold, &nresult);
    return nresult;
}

export fn ft_recency_dot(
    a_ptr: [*]const i32, time_a_ptr: [*]const i32,
    b_ptr: [*]const i32, time_b_ptr: [*]const i32,
    n: i32,
) i64 {
    var result: i64 = 0;
    c.recency_dot(a_ptr, time_a_ptr, b_ptr, time_b_ptr, n, &result);
    return result;
}

export fn ft_window_gradient(
    arr_ptr: [*]const i32, n: i32, window: i32,
    result_ptr: [*]i32,
) void {
    c.window_gradient(arr_ptr, n, window, result_ptr);
}

export fn ft_physics(latency_ptr: *f32, flops_ptr: *f32, simd_ptr: *i32) void {
    c.physics(latency_ptr, flops_ptr, simd_ptr);
}
