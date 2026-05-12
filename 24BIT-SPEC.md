# 24-Bit Tile Format — Cross-Language Specification

> The common data type that every forest layer speaks. Every agent reads it. Every port writes it. Every language compiles to it.

---

## Word Layout

Every tile is exactly 24 bits, dynamically partitioned per connection:

```
Bit:  23  22  21  20  19  18  17  16  15  14  13  12  11  10  09  08  07  06  05  04  03  02  01  00
     ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
     │         FIELD A          │         FIELD B          │         FIELD C          │         FIELD D          │
     └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

Default partition (6 bits × 4 fields): confidence, gradient, epsilon, context.

But the partition changes per connection. The first 2 bits of every tile encode the partition scheme.

### Partition Schemes

| Scheme | Bits | Fields | Use Case |
|--------|------|--------|----------|
| 00 | 6+6+6+6 | conf, grad, eps, ctx | Default — balanced |
| 01 | 12+4+4+4 | confidence, grad, eps, ctx | Confidence-heavy (canopy) |
| 10 | 8+8+4+4 | conf+grad, eps, ctx_a, ctx_b | Deep gradient (understory) |
| 11 | 4+4+4+12 | conf, grad, eps, context | Context-heavy (seed bank) |

### Field Meanings

**confidence (6-12 bits):** How sure the agent is. 0 = pure guess, max = absolute certainty.
- 6 bits: 64 levels (forest floor)
- 8 bits: 256 levels (understory)
- 12 bits: 4096 levels (canopy)

**gradient (4-8 bits):** Position in the shelf-sign gradient. 0 = entry-level, max = expert.
- 4 bits: 16 levels (seed bank — coarse)
- 8 bits: 256 levels (understory — fine)

**epsilon (4 bits):** Micro-syncopation offset. Timing variance ±128µs in 16 steps.
- Always 4 bits across all schemes.
- Used for temporal alignment between rooms.

**context (4-12 bits):** Which room or spline this tile belongs to.
- 4 bits: 16 room IDs (forest floor — limited scope)
- 12 bits: 4096 room IDs (mycelium — full scope)

---

## Language Implementations

### C
```c
typedef union {
    uint32_t raw;       // 32-bit (8 unused)
    struct {
        unsigned scheme : 2;
        unsigned field_a : 6;
        unsigned field_b : 6;
        unsigned field_c : 6;
        unsigned field_d : 6;
    } default_partition;
    struct {
        unsigned scheme : 2;
        unsigned confidence : 12;
        unsigned gradient : 4;
        unsigned epsilon : 4;
        unsigned ctx : 4;
    } confidence_heavy;
    struct {
        unsigned scheme : 2;
        unsigned conf_grad : 8;
        unsigned epsilon : 4;
        unsigned ctx_a : 4;
        unsigned ctx_b : 4;
    } deep_gradient;
    struct {
        unsigned scheme : 2;
        unsigned confidence : 4;
        unsigned gradient : 4;
        unsigned epsilon : 4;
        unsigned ctx : 12;
    } context_heavy;
} Tile24;
```

### Rust
```rust
#[repr(u32)]
pub enum Tile24 {
    Balanced(u6, u6, u6, u6),        // scheme 00
    ConfidenceHeavy(u12, u4, u4, u4), // scheme 01
    DeepGradient(u8, u4, u4, u4),    // scheme 10
    ContextHeavy(u4, u4, u4, u12),   // scheme 11
}
```

### Python
```python
@dataclass
class Tile24:
    scheme: int  # 2 bits
    fields: tuple  # 4 fields, total 22 bits
    
    @classmethod
    def balanced(cls, conf, grad, eps, ctx):
        return cls(0, (conf, grad, eps, ctx))
    
    def encode(self) -> int:
        """Pack to 24-bit integer"""
        result = self.scheme << 22
        for i, f in enumerate(self.fields):
            shift = 22 - (2 + i * 6)  # 6 bits each for default
            result |= (f & 0x3F) << shift
        return result & 0xFFFFFF
```

### Go
```go
type Tile24 struct {
    Scheme  uint8  // 2 bits
    Fields  [4]uint16 // 4 fields, total 22 bits
}

func (t Tile24) Encode() uint32 {
    var result uint32 = uint32(t.Scheme) << 22
    for i, f := range t.Fields {
        shift := uint(22 - (2 + i * 6))
        result |= (uint32(f) & 0x3F) << shift
    }
    return result & 0xFFFFFF
}
```

### TypeScript
```typescript
type Tile24 = {
    scheme: 0 | 1 | 2 | 3;
    fields: [number, number, number, number]; // 4 fields
    encode(): number; // returns 24-bit int
}
```
