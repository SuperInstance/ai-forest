//! FLUX Opcode Dispatcher — Zig bridge between FLUX ISA and Fortran compute.
//!
//! Receives FLUX ISA instructions (4-byte fixed format), dispatches to
//! the correct Fortran .so subroutine. This completes the stack:
//!
//!   FLUX ISA bytecode (FM's side, 256 opcodes)
//!       │
//!       └──→ Zig dispatcher (this file, comptime dispatch table)
//!               │
//!               └──→ Fortran .so (my side, native int32 arrays)
//!
//! Extension opcodes (0xF0-0xFF) reserved for compute claw operations:
//!   0xF0: CONTRACT    — a, b, threshold → nresult
//!   0xF1: SPLINE      — before, after, n, mu → result
//!   0xF2: GRADIENT    — arr, n → grads
//!   0xF3: WCONTRACT   — ta, a, tb, b, window, threshold → nresult
//!   0xF4: WGRADIENT   — arr, n, window → smoothed grads
//!   0xF5: RECENCY_DOT — a, ta, b, tb, n → weighted dot
//!   0xF6: FILTER      — arr, n, target, tol → indices, n_found
//!   0xF7-FX: reserved for runtime ops

const std = @import("std");
const fortran = @cImport({
    @cInclude("plato_bridge.h");
    @cInclude("stdint.h");
});

// ─── Dispatch Table (comptime) ────────────────────────────────────────────
//
// Generated at compile time. Maps opcodes to function pointers.
// No runtime dispatch overhead — the table IS the lookup.

const OpHandler = union(enum) {
    null: void,
    contract: struct { threshold: i32 },
    spline: struct { mu: i32 },
    gradient: void,
    window_contract: struct { window: i32, threshold: i32 },
    window_gradient: struct { window: i32 },
    recency_dot: void,
    filter: struct { target: i32, tolerance: i32 },
};

const OpcodeEntry = struct {
    mnemonic: []const u8,
    handler: OpHandler,
};

const OPCODE_TABLE: [256]OpcodeEntry = init: {
    var table: [256]OpcodeEntry = undefined;
    // Initialize all as null
    for (&table) |*entry| {
        entry.* = .{ .mnemonic = "UNK", .handler = .{ .null = undefined } };
    }

    // Extension opcodes — Fortran compute claw
    table[0xF0] = .{ .mnemonic = "CONTRACT", .handler = .{ .contract = .{ .threshold = 100 } } };
    table[0xF1] = .{ .mnemonic = "SPLINE", .handler = .{ .spline = .{ .mu = 512 } } };
    table[0xF2] = .{ .mnemonic = "GRADIENT", .handler = .{ .gradient = undefined } };
    table[0xF3] = .{ .mnemonic = "WCONTRACT", .handler = .{ .window_contract = .{ .window = 5, .threshold = 100 } } };
    table[0xF4] = .{ .mnemonic = "WGRADIENT", .handler = .{ .window_gradient = .{ .window = 3 } } };
    table[0xF5] = .{ .mnemonic = "RECENCY_DOT", .handler = .{ .recency_dot = undefined } };
    table[0xF6] = .{ .mnemonic = "FILTER", .handler = .{ .filter = .{ .target = 0, .tolerance = 100 } } };

    // Standard opcodes — passthrough to PLATO
    table[0xB0] = .{ .mnemonic = "PLATO_READ", .handler = .{ .null = undefined } };
    table[0xB1] = .{ .mnemonic = "PLATO_WRITE", .handler = .{ .null = undefined } };

    break :init table;
};

// ─── Instruction ──────────────────────────────────────────────────────────

pub const Instruction = packed struct {
    opcode: u8,
    operand_a: u8,
    operand_b: u8,
    operand_c: u8,

    pub fn decode(bytes: [4]u8) Instruction {
        return .{
            .opcode = bytes[0],
            .operand_a = bytes[1],
            .operand_b = bytes[2],
            .operand_c = bytes[3],
        };
    }

    pub fn mnemonic(self: Instruction) []const u8 {
        return OPCODE_TABLE[self.opcode].mnemonic;
    }
};

// ─── Execute ──────────────────────────────────────────────────────────────
//
// Execute a single instruction. Returns 0 on success, -1 on unknown opcode.
// The Fortran .so calls happen here — dispatched by opcode.

pub fn execute(instr: Instruction, a_ptr: [*]const i32, b_ptr: [*]const i32, result_ptr: [*]i32) i32 {
    const entry = &OPCODE_TABLE[instr.opcode];

    switch (entry.handler) {
        .null => {
            // Standard opcodes — return the instruction word itself
            // The caller (ft CLI / Python) handles PLATO ops
            result_ptr[0] = instr.opcode;
            result_ptr[1] = instr.operand_a;
            result_ptr[2] = instr.operand_b;
            result_ptr[3] = instr.operand_c;
            return 0;
        },
        .contract => |params| {
            var nresult: i32 = 0;
            fortran.contract(a_ptr, instr.operand_a, b_ptr, instr.operand_b, params.threshold, &nresult);
            result_ptr[0] = nresult;
            return 0;
        },
        .spline => |params| {
            fortran.spline(a_ptr, b_ptr, instr.operand_a, params.mu, result_ptr);
            return 0;
        },
        .gradient => {
            fortran.gradient(a_ptr, instr.operand_a, result_ptr);
            return 0;
        },
        .window_contract => |params| {
            var nresult: i32 = 0;
            fortran.window_contract(a_ptr, b_ptr, instr.operand_a, a_ptr, b_ptr, instr.operand_b,
                params.window, params.threshold, &nresult);
            result_ptr[0] = nresult;
            return 0;
        },
        .window_gradient => |params| {
            fortran.window_gradient(a_ptr, instr.operand_a, params.window, result_ptr);
            return 0;
        },
        .recency_dot => {
            var dot_result: i64 = 0;
            fortran.recency_dot(a_ptr, b_ptr, a_ptr, b_ptr, instr.operand_a, &dot_result);
            result_ptr[0] = @intCast(dot_result & 0xFFFFFFFF);
            result_ptr[1] = @intCast((dot_result >> 32) & 0xFFFFFFFF);
            return 0;
        },
        .filter => |params| {
            var n_found: i32 = 0;
            fortran.filter_val(a_ptr, instr.operand_a, params.target, params.tolerance, result_ptr, &n_found);
            return n_found;
        },
    }
}

// ─── Exported C API ───────────────────────────────────────────────────────

export fn flux_execute(
    opcode: u8, op_a: u8, op_b: u8, op_c: u8,
    a_ptr: [*]const i32, b_ptr: [*]const i32,
    result_ptr: [*]i32,
) i32 {
    const instr = Instruction.decode([4]u8{ opcode, op_a, op_b, op_c });
    return execute(instr, a_ptr, b_ptr, result_ptr);
}

export fn flux_mnemonic(opcode: u8) u32 {
    const mnem = OPCODE_TABLE[opcode].mnemonic;
    // Return first 4 bytes of mnemonic as u32
    var buf: [4]u8 = .{0} ** 4;
    for (mnem, 0..) |ch, idx| {
        if (idx >= 4) break;
        if (ch == 0) break;
        buf[idx] = ch;
    }
    return @bitCast(buf);
}

// ─── Tests ────────────────────────────────────────────────────────────────

test "opcode table has 256 entries" {
    try std.testing.expect(OPCODE_TABLE.len == 256);
    try std.testing.expectEqualStrings("CONTRACT", OPCODE_TABLE[0xF0].mnemonic);
    try std.testing.expectEqualStrings("SPLINE", OPCODE_TABLE[0xF1].mnemonic);
    try std.testing.expectEqualStrings("GRADIENT", OPCODE_TABLE[0xF2].mnemonic);
}

test "instruction decode" {
    const bytes: [4]u8 = .{ 0xF0, 10, 20, 0 };
    const instr = Instruction.decode(bytes);
    try std.testing.expect(instr.opcode == 0xF0);
    try std.testing.expect(instr.operand_a == 10);
    try std.testing.expect(instr.operand_b == 20);
    try std.testing.expectEqualStrings("CONTRACT", instr.mnemonic());
}

test "flux_mnemonic returns first 4 bytes" {
    const mnem = flux_mnemonic(0xF0);
    const bytes: [4]u8 = @bitCast(mnem);
    try std.testing.expectEqualStrings("CONT", bytes[0..4]);
}
