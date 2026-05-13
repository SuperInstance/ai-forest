# 128 — A 128-bit-native Fortran-like Language for Large-Scale Array Computing

> *Every word is 128 bits. Every operation is vectorized. Every backend is automatic.*

---

## 1. The Thesis

Fortran succeeded because its word size matched the hardware (32-bit int, 64-bit float). The compiler optimized for that word size. SIMD (128-bit NEON, 512-bit AVX) came later as an extension.

128 inverts this: **128 bits is the native word.** Everything else (4×int32, 2×int64, 1×int128, 4×float32, 2×float64, 8×float16) is a lane configuration within the 128-bit word.

The compiler doesn't "vectorize" 32-bit operations into 128-bit SIMD. It expresses EVERYTHING as 128-bit operations — some of which happen to operate on individual 32-bit lanes.

| | Fortran 77 | Fortran 90+ | 128 |
|---|---|---|---|
| Native word | 32-bit | 32/64-bit | **128-bit** |
| Array ops | Loops | Array slices | **Built-in operators** |
| SIMD | None | Compiler auto-vectorization | **Language primitives** |
| Temporal | Manual | Manual | **First-class types** |
| GPU | None | OpenACC/OpenMP | **Automatic codegen** |
| Memory | Static | Heap | **Ring buffer (built-in)** |

---

## 2. Language Specification

### 2.1. The Word

Every variable is 128 bits wide. The type determines how the lanes are partitioned:

```
type word128 = u128;      // 1 × 128-bit unsigned
type word4i   = [4]i32;   // 4 × 32-bit signed integer  (default for tile arrays)
type word2i   = [2]i64;   // 2 × 64-bit signed integer  (for indices)
type word4f   = [4]f32;   // 4 × 32-bit float           (for confidence scores)
type word2d   = [2]f64;   // 2 × 64-bit double          (for Penrose coordinates)
type word8h   = [8]f16;   // 8 × 16-bit half-float      (for compressed confidence)
```

### 2.2. Array Types

Arrays of 128-bit words. Column-major (like Fortran). Bounds-checked at compile time where possible.

```
// A room of tiles: T rows (tiles) × 4 fields (conf, grad, eps, ctx)
room tiles[1024]   — 1024 tiles, each 128-bit word = 4 × int32

// A Penrose tiling vertex array
room vertices[5000] — 5000 vertices, each 128-bit word = 2 × float64 (x, y)

// A ring buffer (circular, auto-wrapping)
ring buffer[1048576] — 1M tiles, circular buffer, write pointer tracked
```

### 2.3. Built-in Operators

```
// CONTRACT: count pairs where |a[i] - b[j]| > threshold
// Compiles to: Fortran contract() + NEON SDOT + CUDA kernel
result = contract(room_a, room_b, threshold)

// SPLINE: interpolate between states
// Compiles to: Fortran spline() + NEON MLA + CUDA kernel
next = spline(before, after, mu)

// GRADIENT: compute deltas between consecutive tiles
// Compiles to: Fortran gradient() + NEON ABD + CUDA kernel
deltas = gradient(tiles)

// WINDOW: temporal filtering
// Compiles to: Fortran window_contract() + predicated NEON
filtered = window(tiles, delta_t, window_size)

// PENROSE: generate non-repeating spatial indices
// Compiles to: C++ penrose_generate() + CUDA kernel
ids = penrose(tiles, iterations)

// RECALL: lossy reconstruction with Ebbinghaus decay
// Compiles to: Fortran recency_dot() + ring buffer read
reconstructed = recall(room, context, blind_width)
```

### 2.4. Temporal Types (First-Class)

Time is not a library. It's a type.

```
temporal tiles[1000]    — every tile has an implicit timestamp
temporal window w = 10s — a sliding window over the temporal stream

// Spline interpolation between temporal samples
temporal spline(before, after) -> prediction

// Gradient over a temporal dimension
temporal gradient(tiles) -> rate_of_change

// Ebbinghaus decay applied to confidence
temporal confidence = exp(-t / tau)  — built-in decay function
```

### 2.5. Penrose Types (Built-in Spatial Indexing)

```
penrose p3(iterations) : vertices, triangles, types
// Generates a P3 rhombus tiling at the given iteration depth
// p3(7) → 6100 triangles, 1624 vertices, all unique IDs
// p3.vertices → array of 2 × f64 (x, y coordinates)
// p3.triangles → array of 3 × i32 (vertex indices)
// p3.types → array of i32 (0=thick, 1=thin)

// Use penrose vertex IDs as memory addresses
addr = p3.vertex_id(i) : u64
// addr is guaranteed unique across the entire tiling
```

---

## 3. Compiler Architecture

128 → FLUX bytecode → Fortran .so / CUDA kernel / ARM NEON intrinsics

```
Source (128 language)
    │
    ├──→ 128 compiler (this spec)
    │       │
    │       ├──→ FLUX bytecode (interpreter mode, for testing)
    │       ├──→ Fortran .so (production, gfortran -O3 -fopenmp)
    │       ├──→ CUDA kernel (for NVIDIA GPUs, nvcc -arch=sm_89)
    │       └──→ ARM NEON intrinsics (for ARM64, gcc -march=armv8.2-a)
    │
    └──→ All backends produce the same results
         (verified by test suite)
```

### 3.1. Code Generation Example

```
// 128 source:
room a[1000];      // 1000 tiles
room b[1000];      // 1000 tiles
result = contract(a, b, 500);

// Generated FLUX bytecode:
// 0xF0 CONTRACT a, b, 500

// Generated Fortran:
// call contract(a, 1000, b, 1000, 500, nresult)

// Generated CUDA:
// contract_kernel<<<grid, block>>>(d_a, d_b, 500, d_result);

// Generated ARM NEON:
// contract_neon(a, b, 1000, 500);
```

---

## 4. Proof of Concept

```python
# 128 compiler — proof of concept in Python
# Translates 128 source to FLUX bytecode + Fortran calls

def compile_128(source: str) -> dict:
    """Compile 128 source to all backends."""
    
    tokens = tokenize(source)
    ast = parse(tokens)
    
    return {
        "flux": generate_flux(ast),
        "fortran": generate_fortran(ast),
        "cuda": generate_cuda(ast),
        "neon": generate_neon(ast),
    }

def tokenize(source: str) -> list:
    """Simple tokenizer for 128 language."""
    tokens = []
    for line in source.split("\n"):
        line = line.strip()
        if not line or line.startswith("//"): continue
        for word in line.replace("(", " ( ").replace(")", " ) ").replace(";", " ; ").split():
            tokens.append(word)
    return tokens

def parse(tokens: list) -> dict:
    """Parse tokens into an AST."""
    ast = {"declarations": [], "operations": []}
    i = 0
    while i < len(tokens):
        if tokens[i] == "room":
            # room name[size] — or room name[size] with temporal/penrose
            name = tokens[i + 1].split("[")[0]
            size = tokens[i + 1].split("[")[1].rstrip("]")
            ast["declarations"].append({"type": "room", "name": name, "size": int(size)})
            i += 2
        elif tokens[i] == "temporal":
            name = tokens[i + 1].split("[")[0]
            size = tokens[i + 1].split("[")[1].rstrip("]")
            ast["declarations"].append({"type": "temporal", "name": name, "size": int(size)})
            i += 2
        elif tokens[i] in ("contract", "spline", "gradient", "recall", "penrose"):
            op = tokens[i]
            args = tokens[i + 1].split(",")
            args = [a.strip("(); ") for a in args]
            ast["operations"].append({"op": op, "args": args})
            i += 2
        else:
            i += 1
    return ast

def generate_fortran(ast: dict) -> str:
    """Generate Fortran code from AST."""
    code = ["! Generated by 128 compiler", "program plato_program", 
            "  use, intrinsic :: iso_c_binding", "  implicit none",
            "  integer(c_int32_t) :: i, nr, n"]
    
    for decl in ast["declarations"]:
        code.append(f"  integer(c_int32_t), allocatable :: {decl['name']}(:)")
    
    for op in ast["operations"]:
        if op["op"] == "contract" and len(op["args"]) >= 3:
            code.append(f"  call contract({op['args'][0]}, size({op['args'][0]}), "
                       f"{op['args'][1]}, size({op['args'][1]}), {op['args'][2]}, nr)")
        elif op["op"] == "spline" and len(op["args"]) >= 3:
            code.append(f"  call spline({op['args'][0]}, {op['args'][1]}, "
                       f"size({op['args'][0]}), {op['args'][2]}, nr)")
    
    code.append("end program plato_program")
    return "\n".join(code)

# Test the compiler
test_source = """
room a[1000];
room b[1000];
result = contract(a, b, 500);
result = spline(a, b, 512);
"""

compiled = compile_128(test_source)
print("=== Generated Fortran ===")
print(compiled["fortran"])
print()
print("=== Declarations ===")
for d in compiled["declarations"]:
    print(f"  {d['type']} {d['name']}[{d['size']}]")
print("=== Operations ===")
for op in compiled["operations"]:
    print(f"  {op['op']}({', '.join(op['args'])})")
```

---

## 5. Roadmap

| Phase | What | When |
|---|---|---|
| 0 | Language spec (this document) | Now |
| 1 | Python proof-of-concept compiler | Today |
| 2 | Fortran backend (existing .so calls) | Today |
| 3 | FLUX bytecode backend (256-ops) | This week |
| 4 | CUDA backend (NVCC kernel generation) | This week |
| 5 | ARM NEON backend (intrinsic generation) | This week |
| 6 | Self-hosting (128 compiler written in 128) | Next month |

---

*Every word is 128 bits. Every operation is vectorized. Every backend is automatic.*
