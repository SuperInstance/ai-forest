const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const lib = b.addSharedLibrary(.{
        .name = "plato_zig",
        .root_source_file = b.path("bridge.zig"),
        .target = target,
        .optimize = optimize,
    });

    lib.linkSystemLibrary("plato_math");
    lib.addLibraryPath(.{ .cwd_relative = "../fortran" });

    b.installArtifact(lib);

    // Tests
    const test_art = b.addTest(.{
        .root_source_file = b.path("bridge.zig"),
        .target = target,
        .optimize = optimize,
    });
    test_art.linkSystemLibrary("plato_math");
    test_art.addLibraryPath(.{ .cwd_relative = "../fortran" });

    const test_run = b.addRunArtifact(test_art);
    const test_step = b.step("test", "Run Zig bridge tests");
    test_step.dependOn(&test_run.step);
}
