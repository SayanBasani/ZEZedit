# ZEZEDIT 2.0 — TEMPORAL NOVELTY & MULTI-LAYER OVERLAP SYSTEM
## Mathematical Formulation, Root Cause Analysis & Invariants

**Version:** 2.0.0-alpha.1  
**Authoritative Path:** `docs/architecture/TEMPORAL_NOVELTY_DESIGN.md`  
**Date:** 2026-11-13  
**Project:** `D:\ZezEdit`

---

## 1. Executive Summary & Root Cause Analysis

### The Session 7 Defect
In Session 7, Batch 1 discovery returned the following two candidates from the same source video:
- **Candidate A:** `[63.07s – 87.31s]` (Duration: `24.24s`)
- **Candidate B:** `[63.07s – 114.01s]` (Duration: `50.94s`)

Although Candidate A and Candidate B were generated with distinct database IDs, Candidate B completely subsumed Candidate A (100% containment of interval A inside B).

### Why the Previous System Permitted This
1. **tIoU Under-Penalization of Containment:**
   $$\text{Intersection} = 87.31 - 63.07 = 24.24\text{s}$$
   $$\text{Union} = 114.01 - 63.07 = 50.94\text{s}$$
   $$\text{tIoU} = \frac{24.24}{50.94} \approx 0.4759$$
   The previous `_deduplicate_and_group()` evaluated only `tIoU >= 0.55`. Because `0.4759 < 0.55`, `_deduplicate_and_group()` failed to flag Candidate B as an alternative cut of Candidate A.
2. **Missing Intra-Batch Selection Check:**
   When iterating through sorted candidates to fill the target clip count (`selected_candidates.append(cand)`), the engine only checked `if cand.alternative_of_id is not None`. Because Candidate B escaped the tIoU check, it was accepted directly into the final batch alongside Candidate A.

---

## 2. Mathematical Formulation of Temporal Overlap

Given interval $A = [S_A, E_A]$ and interval $B = [S_B, E_B]$ with $D_A = E_A - S_A$ and $D_B = E_B - S_B$:

### A. Intersection Length
$$I(A, B) = \max\left(0, \min(E_A, E_B) - \max(S_A, S_B)\right)$$

### B. Union Length
$$U(A, B) = \max(E_A, E_B) - \min(S_A, S_B)$$

### C. Temporal Intersection over Union (tIoU)
$$\text{tIoU}(A, B) = \frac{I(A, B)}{U(A, B)}$$

### D. Relative Overlap Ratios
- **Ratio relative to A:**
  $$R_A = \frac{I(A, B)}{D_A}$$
- **Ratio relative to B:**
  $$R_B = \frac{I(A, B)}{D_B}$$
- **Containment Ratio (relative to shorter interval):**
  $$R_{\min}(A, B) = \frac{I(A, B)}{\min(D_A, D_B)}$$

---

## 3. Authoritative Multi-Layer Novelty Invariants

A candidate moment $C$ is rejected as non-novel if **any** of the following conditions hold against any previously selected candidate in the current batch or any historically generated clip:

1. **Exact / Near-Exact Boundary Match:**
   $$|S_C - S_{\text{ref}}| < 2.5\text{s} \quad \text{AND} \quad |E_C - E_{\text{ref}}| < 2.5\text{s}$$
2. **tIoU Limit Exceeded:**
   $$\text{tIoU}(C, \text{ref}) \ge 0.50 \quad (\text{or } 0.55 \text{ in relaxed mode})$$
3. **Substantial Asymmetric Overlap:**
   $$R_C \ge 0.55 \quad \text{OR} \quad R_{\text{ref}} \ge 0.55$$
4. **Full / Substantial Containment ($R_{\min}$ Guard):**
   $$R_{\min}(C, \text{ref}) \ge 0.60 \quad (\text{or } 0.70 \text{ in relaxed mode})$$
   *Note: In the Session 7 failure case, $R_{\min} = 1.00$, immediately triggering rejection.*
5. **Content / Transcript Similarity:**
   $$\text{Jaccard}(T_C, T_{\text{ref}}) > 0.75 \quad \text{AND} \quad R_C > 0.30$$

---

## 4. Selection Lifecycle Pipeline

```
1. Pool Generation:
   Extract all candidate intervals bounded by speech sentences & visual scene transitions.

2. Multimodal Scoring:
   Compute 10 score components and total attractiveness score.

3. Gate Filtering:
   Reject hard failures (duration < min_duration, invalid audio, zero speech/visual signal).

4. Historical Exclusion Filter:
   Compare candidates against all historically generated clips across ALL aspect ratios & directions.
   Reject if tIoU >= 0.45 OR R_min >= 0.60.

5. Intra-Pool Deduplication & Alternative Clustering:
   Cluster alternative cuts using tIoU >= 0.50 OR R_min >= 0.60.
   Subordinate overlapping cuts to primary moments.

6. Intra-Batch Selection Loop:
   Iterate scored candidates in descending score order.
   Skip alternative cuts (alternative_of_id is not None).
   Explicitly verify candidate against all ALREADY SELECTED candidates in this batch.
   If tIoU >= 0.50 OR R_min >= 0.60 with any selected candidate, reject from batch.

7. Transactional Persistence:
   Persist accepted candidates, novelty ledger records, and generation run metadata atomically.
```
