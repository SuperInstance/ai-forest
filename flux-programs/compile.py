#!/usr/bin/env python3
"""
FLUX→Fortran Compiler — Translates FLUX extension opcodes directly to Fortran calls.

FLUX bytecode (0xFx ops) → Zig dispatcher → Fortran .so
This compiler makes the path direct: FLUX → Fortran, no Zig needed for hot path.

Usage:
  python3 compile.py program.flx    # Compile FLUX to Fortran call sequence
  python3 compile.py --run prog.flx # Compile AND execute
"""

import json, os, subprocess, sys

OPCODES = {
    0xF0: ("CONTRACT", "contract(a, na, b, nb, threshold, nresult)"),
    0xF1: ("SPLINE", "spline(before, after, n, mu, result)"),
    0xF2: ("GRADIENT", "gradient(arr, n, result)"),
    0xF3: ("WCONTRACT", "window_contract(ta, a, na, tb, b, nb, window, threshold, nresult)"),
    0xF4: ("WGRADIENT", "window_gradient(arr, n, window, result)"),
    0xF5: ("RECENCY_DOT", "recency_dot(a, ta, b, tb, n, result)"),
    0xF6: ("FILTER", "filter_val(a, n, target, tolerance, indices, n_found)"),
    0xF7: ("SHATTER", "seed_cycle(tiles, n, seed, 512, 100, 5000, result, n_out)"),
    0xF8: ("RECALL", "ring_read(n, result, n_read)"),
    0xF9: ("TELEPHONE", "seed_permute(tiles_in, n, seed, tiles_out)"),
    0xFA: ("CONSENSUS", "ring_contract(n_recent, n_memory, threshold, nresult)"),
    0xFB: ("WITNESS", "ebbinghaus_contract(a, ca, na, b, cb, nb, thresh, tau, nr)"),
    0xFC: ("ADJOIN", "adaptive_threshold(base, density, theta)"),
    0xFD: ("RECONCILE", "seed_blend(tiles, n, seed, mu, result)"),
    0xFE: ("FORGET", "seed_perturb(tiles, n, seed, mag, result)"),
    0xFF: ("FULL_INTELLIGENCE", "consciousness_bench(niter, thresh, F, M, C, T)"),
}

def compile_flx(source_path):
    """Compile a .flx file to a Fortran call sequence"""
    with open(source_path) as f:
        lines = f.readlines()
    
    fortran_code = [
        "! Compiled from: " + os.path.basename(source_path),
        "! FLUX → Fortran Compiler",
        "! Generates direct Fortran .so calls for all extension opcodes",
        "",
        "program flux_program",
        "  use, intrinsic :: iso_c_binding",
        "  implicit none",
        "  integer(c_int32_t) :: i, nr, n",
        "  integer(c_int32_t), allocatable :: a(:), b(:), r(:)",
        "",
    ]
    
    in_loop = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            if line and not line.startswith(";") and not line.startswith("#"):
                fortran_code.append(f"  ! {line}")
            continue
        
        # Parse opcodes
        for code, (mnemonic, signature) in sorted(OPCODES.items()):
            if line.upper().startswith(mnemonic):
                args_part = line[len(mnemonic):].strip()
                args = [a.strip() for a in args_part.replace(",", " ").split()]
                
                if mnemonic == "CONTRACT" and len(args) >= 3:
                    fortran_code.append(f"  call contract(a, size(a), b, size(b), {args[2]}, nr)")
                elif mnemonic == "GRADIENT":
                    fortran_code.append(f"  call gradient(a, size(a), r)")
                elif mnemonic == "SEED" and len(args) >= 2:
                    fortran_code.append(f"  call seed_cycle(a, size(a), {args[1]}, 512, 100, 5000, r, nr)")
                elif mnemonic == "RECALL":
                    fortran_code.append(f"  call ring_read({args[1] if len(args) > 0 else '10'}, r, nr)")
                elif mnemonic == "TELEPHONE":
                    fortran_code.append(f"  call seed_permute(a, size(a), {args[1] if len(args)>1 else '0'}, r)")
                elif mnemonic == "FOR_EACH":
                    in_loop = True
                    fortran_code.append(f"  ! Loop start")
                elif mnemonic == "NEXT":
                    in_loop = False
                    fortran_code.append(f"  ! Loop end")
                elif mnemonic == "PLATO_WRITE":
                    msg = args[0] if args else "done"
                    fortran_code.append(f"  print *, 'Tiled: {msg}'")
                elif mnemonic == "HALT":
                    pass
                break
        else:
            fortran_code.append(f"  ! Ignored: {line}")
    
    fortran_code.extend([
        "end program flux_program",
    ])
    
    return "\n".join(fortran_code)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"File not found: {src}")
        sys.exit(1)
    
    fortran = compile_flx(src)
    out_path = src.replace(".flx", ".f90")
    with open(out_path, "w") as f:
        f.write(fortran)
    print(f"Compiled {src} → {out_path}")
    print(f"  {len(fortran)} chars of Fortran code")
    
    if "--run" in sys.argv:
        bin_path = src.replace(".flx", "")
        subprocess.run(["gfortran", "-O3", "-o", bin_path, out_path,
            "-L/tmp/ai-forest/fortran", "-lplato_math", "-lfortran_seed",
            "-Wl,-rpath,/tmp/ai-forest/fortran"], check=True)
        print(f"  Built: {bin_path}")
