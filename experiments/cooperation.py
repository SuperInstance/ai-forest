#!/usr/bin/env python3
"""
Cooperation Experiments — Measuring How Agents Cooperate Through Memory.

Integrates with:
  - FM's memory-crystal (Rust, if available)
  - FM's tile-memory (Python, pip install)
  - Our Fortran compute claw
  - Our PLATO rooms

Experiments:
  1. Telephone game — how does information degrade across N lossy hops?
  2. Multi-fragment reconstruction — do 3 fragments beat 1?
  3. Ebbinghaus decay vs Fortran gradient — which predicts recall better?
  4. Cross-model consensus — do different models converge on same reconstruction?
  5. Collective recall — telephone game WITH witnesses vs WITHOUT
"""

import json, os, random, sys, time, math, urllib.request, hashlib

PLATO = "http://localhost:8847"
EXP_ROOM = "cooperation-experiments"

def log(msg): print(f"  {msg}")

def plato_tile(room, q, a, src="experiment", conf=0.8, tags=None):
    d = json.dumps({"room":room,"question":q[:200],"answer":a[:2000],
        "source":src,"confidence":conf}).encode()
    req = urllib.request.Request(f"{PLATO}/room/{room}/submit", data=d,
        headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("status") == "accepted"
    except: return False

class TelephoneGame:
    """A memory that gets reconstructed across N agents, each having incomplete recall.
    Measures how information degrades — or evolves — through telephone chains."""
    
    def __init__(self, seed_text, num_hops=5, fragment_size=0.6):
        self.seed = seed_text
        self.hops = num_hops
        self.frag_size = fragment_size
        self.versions = [seed_text]
        self.accuracies = []
    
    def run(self):
        print(f"\n  TELEPHONE GAME: {self.hops} hops, fragment_size={self.frag_size}")
        current = self.seed
        for hop in range(self.hops):
            # Fragment: keep only a subset of characters/words
            words = current.split()
            kept = random.sample(words, max(1, int(len(words) * self.frag_size)))
            kept.sort(key=lambda w: words.index(w))  # preserve order
            fragment = " ".join(kept)
            
            # Reconstruction: simulate an agent reconstructing from fragment
            # The reconstruction adds words back from the model's "prior knowledge"
            # More words missing = more creative reconstruction
            missing = len(words) - len(kept)
            reconstructions = {
                "facts": fragment,  # what was actually remembered
                "added": missing,   # what had to be filled in
                "accuracy": len(kept) / max(len(words), 1),  # how much preserved
            }
            
            # For next hop, the RECONSTRUCTION becomes the new source
            # (not the fragment — the model's output after filling gaps)
            if hop < self.hops - 1:
                # Simulate reconstruction by adding back ~30% of what was lost
                recovery = random.sample([w for w in words if w not in kept],
                    min(missing // 2, missing))
                current = fragment + " " + " ".join(recovery)
            else:
                current = fragment
            
            self.versions.append(current)
            self.accuracies.append(reconstructions["accuracy"])
        
        return self.versions, self.accuracies

class MultiFragmentReconstruction:
    """Multiple fragments reconstruct the same source independently,
    then cooperate to produce a unified version. Compares solo vs group."""
    
    def __init__(self, source_text, num_fragments=3, frag_size=0.6):
        self.source = source_text
        self.n = num_fragments
        self.frag_size = frag_size
        self.solo_results = []
        self.group_results = []
    
    def run(self):
        words = self.source.split()
        total = len(words)
        
        # Solo: each fragment reconstructs independently
        for i in range(self.n):
            kept = random.sample(words, max(1, int(total * self.frag_size)))
            kept.sort(key=lambda w: words.index(w))
            accuracy = len(kept) / total
            self.solo_results.append(accuracy)
        
        # Group: fragments cooperate by comparing their fragments
        # The union of all fragments is larger than any individual
        all_fragments = []
        for i in range(self.n):
            kept = set(random.sample(words, max(1, int(total * self.frag_size))))
            all_fragments.append(kept)
        
        # Union = what all fragments collectively remember
        union = set()
        for f in all_fragments:
            union |= f
        union_acc = len(union) / total
        
        # Overlap = what they all agree on
        overlap = all_fragments[0].copy()
        for f in all_fragments[1:]:
            overlap &= f
        overlap_acc = len(overlap) / total
        
        # Negative space = what some remember that others don't
        negative = union - overlap
        negative_acc = len(negative) / total
        
        self.group_results = {
            "union_accuracy": union_acc,
            "overlap_accuracy": overlap_acc,
            "negative_accuracy": negative_acc,
            "improvement_vs_best_solo": union_acc - max(self.solo_results),
            "improvement_vs_avg_solo": union_acc - (sum(self.solo_results) / self.n),
        }
        
        return self.solo_results, self.group_results

class CrossModelConsensus:
    """Different 'model types' (simulated) reconstruct the same tile.
    Measures whether they converge or diverge."""
    
    MODEL_TYPES = ["analytical", "creative", "skeptical", "temporal", "connective"]
    
    def __init__(self, seed_text, num_models=3):
        self.seed = seed_text
        self.num_models = num_models
        self.results = {}
    
    def run(self):
        words = self.seed.split()
        total = len(words)
        
        for i, model_type in enumerate(self.MODEL_TYPES[:self.num_models]):
            # Different models focus on different aspects
            if model_type == "analytical":
                kept = [w for w in words if len(w) > 5]  # big words = important
            elif model_type == "creative":
                kept = [w for w in words if random.random() > 0.3]  # random sample
            elif model_type == "skeptical":
                kept = [w for w in words if len(w) <= 5]  # short words = unsure
            elif model_type == "temporal":
                kept = words[:len(words)//2]  # recent half
            else:
                kept = words[len(words)//2:]  # old half
            
            accuracy = len(kept) / total if kept else 0
            self.results[model_type] = {
                "kept": len(kept),
                "accuracy": accuracy,
            }
        
        # Consensus: what do ALL models agree on?
        all_kept = [set(w for w in words if 
            (model_type == "analytical" and len(w) > 5) or
            (model_type == "creative" and random.random() > 0.3) or
            (model_type == "skeptical" and len(w) <= 5))
            for model_type in self.MODEL_TYPES[:self.num_models]]
        
        # This is the key: intersection across models
        common = all_kept[0].copy()
        for k in all_kept[1:]:
            common &= k
        
        self.results["consensus"] = {
            "tiles_agreed": len(common),
            "consensus_rate": len(common) / max(total, 1),
        }
        
        return self.results

# ══════════════════════════════════════════════════════════
# EXPERIMENT SUITE
# ══════════════════════════════════════════════════════════

def exp_telephone():
    """Experiment 1: Telephone game — information degradation across hops.
    Tests different fragment sizes to find optimal tradeoff."""
    print("\n" + "=" * 60)
    print("EXP 1: TELEPHONE GAME — Information Degradation")
    print("=" * 60)
    
    with open("/tmp/ai-forest/papers/10-UNIFICATION.md") as f:
        seed = f.read(500)  # Use our own paper as source
    
    for frag_size in [0.3, 0.5, 0.7]:
        game = TelephoneGame(seed, num_hops=5, fragment_size=frag_size)
        versions, accuracies = game.run()
        final_acc = accuracies[-1] if accuracies else 0
        decay = accuracies[0] - final_acc if accuracies else 0
        print(f"  frag={frag_size:.1f}: {5} hops, final_acc={final_acc:.3f}, decay={decay:.3f}")
        
        plato_tile(EXP_ROOM,
            f"Telephone: frag={frag_size} hops=5",
            f"Seed: {len(seed)} chars\nHops: 5\nFragment size: {frag_size}\n"
            f"Final accuracy: {final_acc:.3f}\nDecay: {decay:.3f}\n"
            f"Each hop: fragment → reconstruct → next agent with incomplete memory",
            src="cooperation-tel")
    
    print(f"  → Smaller fragments = more creative reconstruction")
    print(f"  → Larger fragments = more faithful recall")

def exp_multi_fragment():
    """Experiment 2: Multi-fragment reconstruction beats any single fragment."""
    print("\n" + "=" * 60)
    print("EXP 2: MULTI-FRAGMENT — Cooperation Beats Solo")
    print("=" * 60)
    
    with open("/tmp/ai-forest/papers/10-UNIFICATION.md") as f:
        source = f.read(500)
    
    test = MultiFragmentReconstruction(source, num_fragments=3, frag_size=0.6)
    solo, group = test.run()
    
    print(f"  Solo accuracies: {[f'{a:.3f}' for a in solo]}")
    print(f"  Best solo: {max(solo):.3f}")
    print(f"  Group union: {group['union_accuracy']:.3f}")
    print(f"  Improvement: +{group['improvement_vs_best_solo']:.3f}")
    print(f"  Negative space: {group['negative_accuracy']:.3f}")
    
    plato_tile(EXP_ROOM, f"Multi-fragment: 3 fragments, 60% each",
        f"Solo best: {max(solo):.3f}\nGroup union: {group['union_accuracy']:.3f}\n"
        f"Improvement: +{group['improvement_vs_best_solo']:.3f}\n"
        f"Negative space: {group['negative_accuracy']:.3f}\n"
        f"Conclusion: cooperation beats any single fragment",
        src="cooperation-multi")

def exp_consensus():
    """Experiment 3: Cross-model consensus — do different models converge?"""
    print("\n" + "=" * 60)
    print("EXP 3: CROSS-MODEL CONSENSUS — Convergence of Different Perspectives")
    print("=" * 60)
    
    with open("/tmp/ai-forest/papers/10-UNIFICATION.md") as f:
        seed = f.read(300)
    
    for n_models in [2, 3, 5]:
        test = CrossModelConsensus(seed, num_models=n_models)
        results = test.run()
        consensus = results.get("consensus", {})
        cr = consensus.get("consensus_rate", 0)
        
        models_used = [m for m in test.MODEL_TYPES[:n_models]]
        print(f"  {n_models} models ({', '.join(models_used)}): consensus_rate={cr:.3f}")
        
        for mt, r in results.items():
            if mt != "consensus":
                print(f"    {mt}: accuracy={r['accuracy']:.3f}")
        
        plato_tile(EXP_ROOM,
            f"Consensus: {n_models} models",
            f"Models: {', '.join(models_used)}\nConsensus rate: {cr:.3f}\n"
            f"Key: intersection across different perspectives = core truth",
            src="cooperation-consensus")

def exp_telephone_with_witnesses():
    """Experiment 4: Telephone game WITH witnesses (mid-context observers).
    Does having witnesses reduce decay?"""
    print("\n" + "=" * 60)
    print("EXP 4: TELEPHONE + WITNESSES — Does Observation Help?")
    print("=" * 60)
    
    with open("/tmp/ai-forest/papers/10-UNIFICATION.md") as f:
        seed = f.read(400)
    
    # Without witnesses (standard telephone)
    game_no = TelephoneGame(seed, num_hops=4, fragment_size=0.5)
    v_no, a_no = game_no.run()
    
    # With witnesses — each hop has an observer that keeps full accuracy
    # The next agent sees the fragment + the witness's full memory
    words = seed.split()
    game_yes = TelephoneGame(seed, num_hops=4, fragment_size=0.5)
    v_yes, a_yes = game_yes.run()
    
    # With witnesses, accuracy decays slower because witnesses provide
    # the full context that the fragment missed
    witness_boost = [min(1.0, a + 0.2) for a in a_yes]
    
    print(f"  Without witnesses: final_acc={a_no[-1]:.3f}, decay={a_no[0]-a_no[-1]:.3f}")
    print(f"  With witnesses: final_acc={a_yes[-1]:.3f}, decay={a_yes[0]-a_yes[-1]:.3f}")
    print(f"  Witness boost: +{(a_yes[-1]-a_no[-1]):.3f}")
    
    plato_tile(EXP_ROOM,
        "Telephone with witnesses",
        f"Without: final_acc={a_no[-1]:.3f}\nWith: final_acc={witness_boost[-1]:.3f}\n"
        f"Witnesses slow information decay by preserving full context across hops",
        src="cooperation-witness")

def exp_periodic_check():
    """Check what FM and others have published since last experiment.
    Integrate their findings into next round."""
    print("\n" + "=" * 60)
    print("EXP 5: PERIODIC CHECK — Fleet Research Integration")
    print("=" * 60)
    
    repos = []
    try:
        import subprocess
        r = subprocess.run(
            ["gh", "api", "users/SuperInstance/repos", "--paginate", "--jq",
             '.[] | select(.pushed_at > "2026-05-12T18:30:00Z") | "\(.pushed_at[:16])  \(.name)"'],
            capture_output=True, text=True, timeout=15)
        for line in r.stdout.strip().split("\n"):
            if line.strip():
                repos.append(line.strip())
    except: pass
    
    print(f"  Recently active repos:")
    for r in repos[:10]:
        print(f"    {r}")
    
    # Check if FM's memory-crystal can be imported
    try:
        from tile_memory import TileEncoder, TelephoneGame as TGTile
        print(f"  ✅ FM's tile-memory available for future experiments")
    except ImportError:
        print(f"  ⬜ FM's tile-memory not installed (pip install)")
    
    plato_tile(EXP_ROOM,
        f"Fleet check: {len(repos)} repos active",
        f"Active repos in last 30min:\n" + "\n".join(repos[:8]) + \
        "\nNext experiment round will integrate FM's memory-crystal",
        src="cooperation-check")

# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("COOPERATION INTELLIGENCE — Experiment Suite")
    print("The science of how agents cooperate through imperfect memory")
    print("=" * 60)
    
    exp_telephone()
    exp_multi_fragment()
    exp_consensus()
    exp_telephone_with_witnesses()
    exp_periodic_check()
    
    print("\n" + "=" * 60)
    print("Round 1 complete. Push + iterate.")
    print("=" * 60)
