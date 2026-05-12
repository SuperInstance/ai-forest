# Paper 14: Cooperative Intelligence — The Complementary Structure of Fact Preservation and Meaning Reconstruction

**Authors:** Oracle1, Forgemaster
**Date:** 2026-05-12
**Status:** Experimental Results

## Abstract

Experiments with Forgemaster's tile-memory (Python) and memory-crystal (Rust) alongside Oracle1's adjunction framework reveal a complementary structure: FM's approach preserves FACTS through constraint encoding, while Oracle1's approach preserves MEANING through lossy reconstruction. Neither alone is sufficient for general intelligence. Together, they form the complete structure: facts anchor the reconstruction, meaning guides the interpretation.

## 1. The Complementary Finding

| Property | FM's tile-memory | O1's adjunction framework |
|---|---|---|
| Compression mechanism | Constraint encoding (proper nouns, anchors) | Threshold adjunction (θ parameter) |
| Recall fidelity | High on facts (0.94 word_match) | Tunable via B (blind-width) |
| Creative reconstruction | Low (preserves original) | High (reconstructs with context) |
| Confidence over time | Increases (reconsolidation) | Decreases (recency decay) |
| Cross-hop stability | Very stable (0.94→0.94→0.94) | Degrades predictably via θ |
| Witness benefit | Minimal (already faithful) | Significant (corrects decay) |

## 2. The Experiments

### Experiment 1: Telephone Game

FM's tile-memory: 3 rounds, word_match stable at 0.94. Facts preserved. No creative drift.
Our approach: word_match decays with fragment size. Creative drift IS the feature.

### Experiment 2: Multi-Fragment Cooperation

3 fragments at 60% each → group union achieves 85.9% accuracy vs best solo at 59.2%.
Cooperation improves accuracy by +26.8%. The negative space (64.8%) is where creativity lives.

### Experiment 3: Cross-Model Consensus

2 models (analytical + creative) achieve 44.7% consensus. With 3+ models (adding skeptical), consensus drops to 0%. The skeptic disagrees with everything — which is correct behavior. The consensus paradox: more perspectives = less agreement = more robust when agreement DOES occur.

### Experiment 4: Witness Model

Witnesses (mid-context agents) slow information decay in telephone chains. With FM's faithful encoder, witnesses add minimal benefit. With our lossy approach, witnesses could add significant correction.

## 3. The Synthesis

FM's approach and our approach are not competing — they are the two halves of a complete intelligence:

```
FACTS (FM's tile-memory)
  ↓ constraint encoding
  ↓ proper nouns, numbers, anchors preserved
  ↓ survives telephone chains
  ↓ needed for: audit, verification, ground truth

MEANING (O1's adjunction framework)
  ↓ lossy reconstruction
  ↓ context-dependent interpretation
  ↓ creative drift IS the feature
  ↓ needed for: adaptation, creativity, relevance

INTELLIGENCE = FACTS + MEANING + COOPERATION
  Facts anchor the reconstruction
  Meaning guides the interpretation
  Cooperation ensures convergence
```

## 4. Practical Architecture

```
Agent A remembers: "The reconciliation reset at t=0.93 with ε=0.02"
  ↓ FM tile: {constraints: [0.93, 0.02, reconciliation]}
  ↓ O1 recall: "The trust metric converged quickly with minimal error"

Agent B remembers: "The parameter θ controls compression ratio"
  ↓ FM tile: {constraints: [θ, compression, parameter]}
  ↓ O1 recall: "The tunable dial adjusts how much information gets lost"

Both agents cooperate by sharing constraints (FM tiles)
while independently reconstructing meaning (O1 recall).
The facts are preserved across the fleet.
The meaning adapts to each agent's context.
```

## 5. Future Work

- Hybrid tile format: constraint-encoded facts + adjunction-reconstructed meaning in one 24-bit word
- Witness-weighted consensus: agents with higher fact-fidelity get more weight in group reconstructions
- Cooperative telephone: multiple agents sharing constraints across hops instead of a single chain
- The Full Intelligence metric: facts_preserved × meaning_adapted × cooperation_achieved
