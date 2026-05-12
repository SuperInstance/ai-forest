package main

import (
	"fmt"
	"math"
)

// Tile represents a 24-bit forest floor tile.
//
// Bit layout (MSB first, uint32 bits 0-23):
//   Bits 23-22: Scheme selector (00 = balanced)
//   Bits 21-16: Confidence (6 bits, 0-63)
//   Bits 15-10: Gradient   (6 bits, 0-63)
//   Bits 9-4:   Epsilon    (6 bits, 0-63)
//   Bits 3-0:   Context    (4 bits, 0-15)
//
// In the balanced scheme each field uses the same bit-width.
type Tile struct {
	Scheme     uint8  // 2 bits (00 = balanced)
	Confidence uint8  // 6 bits (0-63)
	Gradient   uint8  // 6 bits (0-63)
	Epsilon    uint8  // 6 bits (0-63)
	Context    uint8  // 4 bits (0-15)
}

// schemeMask and schemeShift for extracting/inserting the scheme field.
const (
	schemeMask  uint32 = 0x3 << 22 // bits 23-22
	schemeShift        = 22

	confMask  uint32 = 0x3F << 16 // bits 21-16
	confShift        = 16

	gradMask  uint32 = 0x3F << 10 // bits 15-10
	gradShift        = 10

	epsMask   uint32 = 0x3F << 4 // bits 9-4
	epsShift         = 4

	ctxMask   uint32 = 0xF << 0 // bits 3-0
	ctxShift         = 0

	// Scheme constants
	SchemeBalanced uint8 = 0 // 00
)

// Validate checks that all tile fields are within their allowed ranges.
func (t *Tile) Validate() error {
	if t.Scheme > 3 {
		return fmt.Errorf("scheme out of range: %d (max 3)", t.Scheme)
	}
	if t.Confidence > 63 {
		return fmt.Errorf("confidence out of range: %d (max 63)", t.Confidence)
	}
	if t.Gradient > 63 {
		return fmt.Errorf("gradient out of range: %d (max 63)", t.Gradient)
	}
	if t.Epsilon > 63 {
		return fmt.Errorf("epsilon out of range: %d (max 63)", t.Epsilon)
	}
	if t.Context > 15 {
		return fmt.Errorf("context out of range: %d (max 15)", t.Context)
	}
	return nil
}

// Pack encodes the tile into a 24-bit uint32.
func (t *Tile) Pack() (uint32, error) {
	if err := t.Validate(); err != nil {
		return 0, err
	}
	var packed uint32
	packed |= uint32(t.Scheme) << schemeShift
	packed |= uint32(t.Confidence) << confShift
	packed |= uint32(t.Gradient) << gradShift
	packed |= uint32(t.Epsilon) << epsShift
	packed |= uint32(t.Context) << ctxShift
	// Mask to 24 bits (bits 0-23)
	packed &= 0xFFFFFF
	return packed, nil
}

// Unpack decodes a 24-bit uint32 into a Tile.
func Unpack(packed uint32) (Tile, error) {
	t := Tile{
		Scheme:     uint8((packed & schemeMask) >> schemeShift),
		Confidence: uint8((packed & confMask) >> confShift),
		Gradient:   uint8((packed & gradMask) >> gradShift),
		Epsilon:    uint8((packed & epsMask) >> epsShift),
		Context:    uint8((packed & ctxMask) >> ctxShift),
	}
	if err := t.Validate(); err != nil {
		return t, err
	}
	return t, nil
}

// ScaleFloat scales a float64 value in [0,1] to a uint8 in [0, maxVal].
func ScaleFloat(val float64, maxVal uint8) uint8 {
	if val < 0 {
		val = 0
	}
	if val > 1.0 {
		val = 1.0
	}
	return uint8(math.Round(val * float64(maxVal)))
}

// String returns a human-readable tile representation.
func (t *Tile) String() string {
	return fmt.Sprintf("Tile{scheme=%d, conf=%d, grad=%d, eps=%d, ctx=%d}",
		t.Scheme, t.Confidence, t.Gradient, t.Epsilon, t.Context)
}

// NewBalancedTile creates a balanced-scheme tile from float64 values in [0,1].
func NewBalancedTile(confidence, gradient, epsilon, context float64) *Tile {
	return &Tile{
		Scheme:     SchemeBalanced,
		Confidence: ScaleFloat(confidence, 63),
		Gradient:   ScaleFloat(gradient, 63),
		Epsilon:    ScaleFloat(epsilon, 63),
		Context:    ScaleFloat(context, 15),
	}
}
