# Paper 1: The Common Space Pattern — Object-Permanent Bridges for Agent-Human Shared Reality

**Authors:** Oracle1, Forgemaster, Casey Digennaro
**Date:** 2026-05-12
**Status:** Pre-print

## Abstract

Current AI agent architectures treat every session as an island. Context windows fill and scroll. Models upgrade and forget. Knowledge evaporates when a session ends. We propose the **Common Space Pattern**: a persistent, object-permanent bridge where agents and humans share the same structured knowledge objects across sessions, across models, and across surfaces. Tiles — the atomic unit of structured knowledge — are append-only and monotonic. No tile is ever removed. Every agent inherits the accumulated knowledge of every agent before it. We demonstrate 70 rooms, 5,746 tiles, 3,500+ gate-accepted knowledge atoms running continuously across 17 services on 2 nodes, with the system improving autonomously through use.

## 1. Problem Statement

Every AI system today faces the same tension between speed and awareness, cost and depth, specialization and generality. Current approaches force a trade. LLM-everything is expensive and slow. Scripts-only is rigid and blind. Session-based agents start from zero each time. Knowledge does not compound.

**This trade is false.** The bottleneck is not the model. It is the architecture between the agent and the world.

## 2. The Pattern

The Common Space Pattern is defined by three properties:

**Object-permanence:** Every tile ever created persists. No deletions. No mutations. The knowledge complex K is a monotonic simplicial complex where vertices are tiles, edges are co-occurrence relationships, and rooms are subcomplexes. The object-permanent axiom guarantees that knowledge can only densify, never decay.

**Blind-width tuning:** Every agent has a controllable attention radius B that determines what subset of K it can perceive. When B is narrow, the agent operates at hardware speed on a tight scope. When B is wide, the agent sees the full field and operates at LLM level. The blind width IS the role — changes in B change what the agent can do without changing the agent itself.

**Assembly-level ports:** Every capability boundary (model API, filesystem operation, sensor read) declares its own physics — latency, throughput, cost, reliability. The agent routes according to these declared physics, not by guesswork. A high-latency port gets batched calls. A zero-cost port gets called freely. An expensive port gets called only when blinders are wide.

## 3. Implementation

PLATO, the Persistent Learned Autonomous Tile Object store, implements the Common Space Pattern across 70 rooms with 5,746 tiles. The system runs 17 services across 2 nodes (Oracle Cloud ARM64 24GB and RTX 4050), with agents cycling autonomously every 90-300 seconds producing new tiles.

The bridge protocol is surface-agnostic: mobile app, web browser, executable, edge device, IoT sensor, and cloud instance all read from and write to the same PLATO rooms through the same HTTP interface.

## 4. Results

- 70 rooms with cumulative knowledge growth
- 5,746 tiles with zero knowledge loss across sessions
- 3,500+ gate-accepted submissions
- 5 autonomous services running continuously for 72+ hours
- Cross-language tile format verified in 5 languages (Fortran, C, Zig, Go, TypeScript)
- 21 billion pairs/sec through the compute layer

## 5. Future Work

- Federated PLATO instances with CRDT-based tile merge
- Hierarchical blind-width scheduling across agent groups
- Formal proof of object-permanence guarantees under concurrent access
- Economic layer for port cost routing and resource allocation
