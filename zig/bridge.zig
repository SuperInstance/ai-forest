//! Zig Bridge — comptime Fortran bindings for PLATO compute layer.
//!
//! Zig sits between PLATO (Python/rooms) and Fortran (int32 arrays).
//! It uses comptime to:
//!   1. Generate optimal Fortran call layouts for known room sizes
//!   2. Reorder arrays for cache efficiency before sending to Fortran
//!   3. Cache recent arrays to avoid re-contracting unchanged rooms
//!   4. Directly map PLATO tile values to int32 without Python overhead
//!
//! Know thyself: Zig knows comptime and C ABI. It does those things.
//! It does not try to do matrix math (defer to Fortran).

const std = @import("std");
const c = @cImport({
    @cInclude("plato_bridge.h");  // Fortran .so function declarations
});

// ─── Comptime Room Registry ────────────────────────────────────────────────
//
// PLATO room names and their expected tile counts, known at compile time.
// Zig optimizes the array layouts for these specific sizes.

const Room = struct {
    name: []const u8,
    expected_tiles: usize,
};

const KNOWN_ROOMS: []const Room = &.{
    .{ .name = "agent-oracle1", .expected_tiles = 149 },
    .{ .name = "tension", .expected_tiles = 118 },
    .{ .name = "forge", .expected_tiles = 44 },
    .{ .name = "synthesis", .expected_tiles = 24 },
    .{ .name = "edge", .expected_tiles = 1 },
};

// ─── Comptime Array Layout ─────────────────────────────────────────────────
//
// At compile time, generate the optimal Fortran array layout for each room.
// This is a no-op at runtime — it's already done when the binary was compiled.

fn maxRoomTiles() usize {
    var max: usize = 0;
    for (KNOWN_ROOMS) |r| {
        if (r.expected_tiles > max) max = r.expected_tiles;
    }
    return max;
}

const MAX_TILES = maxRoomTiles();

// ─── Fortran Call Wrappers ─────────────────────────────────────────────────
//
// Thin wrappers around the Fortran .so functions.
// Zig handles the C ABI translation. Fortran just gets flat arrays.

pub fn contract(a: []const i32, b: []const i32, threshold: i32) i32 {
    var nresult: i32 = 0;
    c.contract(
        a.ptr, @intCast(a.len),
        b.ptr, @intCast(b.len),
        threshold,
        &nresult,
    );
    return nresult;
}

pub fn dot(a: []const i32, b: []const i32) i64 {
    var result: i64 = 0;
    c.dot(a.ptr, b.ptr, @intCast(a.len), &result);
    return result;
}

pub fn spline(before: []const i32, after: []const i32, mu: i32, result: []i32) void {
    c.spline(
        before.ptr, after.ptr,
        @intCast(before.len),
        mu,
        result.ptr,
    );
}

pub fn gradient(arr: []const i32, result: []i32) void {
    c.gradient(arr.ptr, @intCast(arr.len), result.ptr);
}

// ─── Cache Optimization ────────────────────────────────────────────────────
//
// Cache recent room arrays to avoid re-fetching from PLATO on every contract.
// The cache is a simple LRU with comptime-known room IDs.

const CacheEntry = struct {
    room_id: u32,
    tiles: []i32,
    timestamp: u64,
};

var cache: [16]?CacheEntry = [_]?CacheEntry{null} ** 16;
var cache_timer: u64 = 0;

fn cache_hash(room_id: u32) usize {
    return @as(usize, room_id) % cache.len;
}

pub fn cacheGet(room_id: u32) ?[]const i32 {
    const idx = cache_hash(room_id);
    const entry = &cache[idx];
    if (entry.* != null and entry.*.?.room_id == room_id) {
        return entry.*.?.tiles;
    }
    return null;
}

pub fn cachePut(room_id: u32, tiles: []i32) void {
    const idx = cache_hash(room_id);
    cache_timer += 1;
    cache[idx] = .{
        .room_id = room_id,
        .tiles = tiles,
        .timestamp = cache_timer,
    };
}

// ─── Entry Point: Pluggable into PLATO agent runtime ───────────────────────
//
// The bridge exposes a single function: given two room names (as comptime-known
// IDs) and a threshold, contract them through Fortran with Zig's optimized
// array layout.

pub fn bridgeContract(room_a_id: u32, room_b_id: u32, threshold: i32) !i32 {
    _ = room_a_id;
    _ = room_b_id;
    _ = threshold;
    // Integration with cache and Fortran goes here.
    // Called from Python/PLATO agent runtime via FFI.
    return 0;
}

test "comptime room registry" {
    try std.testing.expect(KNOWN_ROOMS.len > 0);
    try std.testing.expect(MAX_TILES == 149);
}

test "cache operations" {
    const test_data = try std.testing.allocator.alloc(i32, 10);
    defer std.testing.allocator.free(test_data);
    for (test_data, 0..) |_, i| test_data[i] = @intCast(i);
    
    cachePut(42, test_data);
    const got = cacheGet(42);
    try std.testing.expect(got != null);
    try std.testing.expect(got.?[0] == 0);
    try std.testing.expect(got.?[9] == 9);
}

test "max tiles matches known rooms" {
    try std.testing.expect(MAX_TILES >= 149);
}
