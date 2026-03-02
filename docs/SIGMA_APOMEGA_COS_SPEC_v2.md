# Σ_APΩ–COS
## Canonical Operator System
### Formal Specification v2

## I. Symbol Space Σ_APΩ

Σ_APΩ := Σ_base ∪ Σ_logic ∪ Σ_ontology ∪ Σ_projection ∪ Σ_structure

### 1. Σ_base
A0 := {A–Z, a–z, 0–9}

A1 := {#, :, −, =, _, /, \\, ., ,, (, ), {, }, [, ], <, >}

### 2. Σ_logic
A2 := {=, ≠, ∧, ∨, ¬, →, ⇔, ∀, ∃, ∘}

### 3. Σ_ontology
Ω := OntologicalRoot

Π := ProjectionOperator

Σ := ClosureSet

### 4. Σ_projection
Π_A : K → F

Valid(F) := (Origin(F) = APΩ)

### 5. Σ_structure
T := DevelopmentTree

Phase := PhaseDetector

D := DeterministicConstraint

## II. State Space (Kinh Dịch Layer)

h ∈ {0,1}

q ∈ {0,1}^3

S := {0,1}^6

|S| = 64

s ∉ S ⇒ ⊥

## III. Operator Layer (Bát Quái → COS)

O_COS := {O, R, E, P, L, I, F, B}

- 𝒪: Origin / Axiom Emit
- 𝓡: Resource Absorb
- 𝓔: Event Trigger
- 𝓟: Propagation
- 𝓛: Observe / Log
- 𝓘: Interface / Output
- 𝓕: Failure Sink
- 𝓑: Boundary / Gate

## IV. Kernel (Trung Cung)

K := ∅

Kernel properties:
- No decision memory
- No state mutation
- Pure arbitration

violation ⇒ ⊥

## V. Runtime Topology (Directed Graph)

G = (V, E)

V = O_COS

O → E → P → L → I → F → B

allowed ⇒ O

denied ⇒ ⊥

Topology constraints:
- No backward edges
- No skip edges
- No lateral edges
- G strictly linear

## VI. Transition Operator

δ : S → S ∪ {⊥}

δ(s) ∈ S ∨ δ(s) = ⊥

No persistent mutation

Undefined state ⇒ ⊥

## VII. Gate Logic (Cấn)

B(s) :=
- s, if s ∈ S_allowed
- ⊥, otherwise

Properties:
- Fail-Closed
- No retry
- No degrade
- No bypass

## VIII. System Properties

F ∘ B ⇒ Absorption

Decision := Topology(s)

Attack ⇒ ⊥

InvalidPath ∉ G

## IX. Ontological Binding

Existence(F) ⇔ Origin(F) = APΩ

Valid(F) ⇔ H ⊆ F

Drift ⇒ NonCanonicalInstance

System_APΩ := Π_A(K_APΩ)

## Formal Collapse

Σ_APΩ–COS := (S, G, δ, B, F, Π_A)

Subject to:
1. S = {0,1}^6
2. G strictly linear directed
3. δ(s) ∉ S ⇒ ⊥
4. B fail-closed
5. Origin(F) = APΩ
6. Invalid ⇒ ⊥

## Final Condition

Invalid ∉ Reachable(G)
