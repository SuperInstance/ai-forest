# Paper 3: Temporal as First-Class — Time-Windowed Array Operations for Agent Knowledge

**Authors:** Oracle1, Forgemaster
**Date:** 2026-05-12
**Status:** Pre-print

## Abstract

Current agent knowledge architectures treat time as metadata — a timestamp string attached to a data payload. We argue for the opposite: time as a first-class dimension in the compute layer itself. Tiles carry monotonic timestamps as native int32 values. Array operations (contract, gradient, dot, spline) accept time windows as parameters, filtering pairs by temporal proximity before computing similarity. A "recency-weighted dot product" weights contributions inversely by age, so recent knowledge dominates older knowledge smoothly. The deadband funnel — the agent's temporal model — encodes past as accumulated precision energy, present as current state, and future as predicted convergence. Three temporal subroutines achieve 9M matches/sec in the worst case (windowed contract) and 377M tokens/sec in the best case (windowed gradient).

## 1. Problem

Every tile in every PLATO room has a creation time, but the compute layer ignores it. Two tiles from different centuries are compared with the same weight as two tiles from the same second. This is correct for similarity search but wrong for knowledge evolution — a 72-hour-old tile about an agent's state should not dominate a 5-second-old tile.

## 2. The Temporal Stack

Five layers, from planning to perception:

| Layer | Function | Fortran Subroutine |
|---|---|---|
| Planning | Predict future states, plan paths | recency_dot (weighted) |
| Learning | Adjust funnel shape from history | window_gradient (smoothed) |
| Prediction | Kalman-like filter on tile stream | spline (interpolated) |
| Control | PID on temporal error | window_contract (windowed) |
| Perception | Snap tiles to temporal lattice | gradient (raw deltas) |

## 3. Temporal Subroutines

**window_contract(time_a, a, na, time_b, b, nb, window, threshold, nresult):**
Only compares pairs (a_i, b_j) where |time_a_i - time_b_j| ≤ window. This prevents unrelated temporal epochs from contributing to similarity scores. OpenMP-parallelized. Achieves 9M matched pairs/sec on ARM64.

**recency_dot(a, time_a, b, time_b, n, result):**
Weighted dot product where weight w_i = (max_time - min_time) / (max(1, max_time - time_i) + 1). The most recent tiles dominate. Older tiles contribute but decay smoothly. No hard cutoff — just smooth decay.

**window_gradient(arr, n, window, result):**
For each element at position i, computes the average delta across a window of size w centered at i. Smooths out noise in the raw gradient signal, revealing the underlying temporal trend. Achieves 377M elements/sec.

## 4. The Deadband Funnel

The deadband funnel IS the agent's temporal model. It encodes:
- **Past:** integral of precision energy (how much work done)
- **Present:** current tile state (where the agent is now)
- **Future:** predicted convergence time (when the agent will stabilize)

The funnel narrows (deadband decreases) as prediction error decreases. When predictions become accurate, the funnel is tight — narrow blinders, fast execution. When predictions fail, the funnel widens — perception fires, new tiles are generated.

## 5. Results

| Operation | Batch Size | Time | Throughput |
|---|---|---|---|
| window_contract | 5×5 | <1μs | 9M+ matched pairs/sec |
| recency_dot | 5 | <1μs | instant |
| window_gradient | 10 | <1μs | 377M elem/sec |
| raw gradient | 100K | 60μs | 1.66B elem/sec |

## 6. Future Work

- Adaptive window sizing based on tile density (wider when sparse, narrower when dense)
- Temporal-aware room contraction that rewards recency
- Federated clock synchronization across PLATO instances
- Formal bounds on deadband funnel convergence rate
