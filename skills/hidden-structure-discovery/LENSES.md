# Hidden-Structure Lens Pack

This companion note extends `SKILL.md` with additional representation lenses. It is a search-policy document, not proof authority.

## Source discipline

Three kinds of material are deliberately separated below.

1. **Source-backed mathematical concepts**: statements directly supported by cited primary/expository sources.
2. **Research analogies**: ways to transfer those concepts into proof discovery. These are heuristics until tested.
3. **User-supplied world-class-technique portfolio**: a useful brainstorming taxonomy, not treated here as a historically exhaustive account of Fields Medalists' methods.

## Lens A — Chaitin: compression, elegance, and changing the complexity language

Primary source:

- Gregory Chaitin, *Algorithmic Information Theory: Some Recollections*, arXiv:math/0701164v2 (2007).

### Source-backed concepts

Chaitin organizes algorithmic information theory around program-size complexity: the size of a smallest program producing an object. He calls a program `elegant` when no smaller program in the same language produces the same output.

A particularly useful methodological episode is his progression through several complexity formalisms. He reports that one representation made certain structure hard to expose, another made the relevant result almost trivial, and the mature self-delimiting formulation restored useful algebraic properties and produced a cleaner theory.

The lesson is not that mathematically good proofs are literally shortest programs. The source instead supports two narrower search heuristics:

```text
structure often corresponds to compressibility,
and a bad representation can hide that compressibility.
```

### Research translation

When a proof grows large, ask for a **generating description** of all the cases.

Replace:

```text
case_1 proof
case_2 proof
...
case_n proof
```

with:

```text
small mechanism + action/transport/composition rule -> all n cases.
```

Define a non-authoritative compression ratio:

```text
structural_compression =
    obligations explained or generated
    -----------------------------------
    independent mechanism assumptions + mapping obligations.
```

High compression is a clue that a real invariant has been found, but it is not itself evidence of truth.

### Representation-switch trigger

If the theorem is true but every proof in the current language accumulates error terms, branches, or coordinate debt, explicitly create alternate languages and compare them.

Examples:

```text
theta coordinates -> polarized abelian varieties
product-locus zeros -> reducible anti-isometries
reducible anti-isometry -> Kani isogeny diamond
isogeny diamond -> Hom/quaternion lattice
random probe -> rank-one linear map on a 2D module
```

A representation is preferred when it makes more of the desired structure inevitable and fewer facts accidental.

## Lens B — Epiplexity: observer-relative extractable structure

Primary source:

- Marc Finzi, Shikai Qiu, Yiding Jiang, Pavel Izmailov, J. Zico Kolter, Andrew Gordon Wilson, *From Entropy to Epiplexity: Rethinking Information for Computationally Bounded Intelligence*, arXiv:2601.03220v2 (2026).

### Source-backed concepts

The paper distinguishes random/unpredictable information from structural information extractable by a computationally bounded observer. Epiplexity is observer- and compute-dependent. The authors emphasize that deterministic transformations and ordering can change how much useful structure a bounded observer can extract even when classical information measures would not increase.

### Research translation

A proof representation should therefore be judged relative to an actual research observer/toolchain:

```text
observer O = {human mathematician, Lean, Sage, Morph, LEAP, SAT/SMT, lattice solver, ...}
budget T   = time / search / proof complexity budget
representation R
```

Ask:

```text
Under the same O and T, which representation exposes the most reusable
structure that can actually be discovered, falsified, or certified?
```

This gives an **observer-relative structure-yield heuristic**:

```text
structure_yield(O,T,R) =
    reusable certified/falsifiable consequences exposed under budget T
    ------------------------------------------------------------------
    representation + translation + proof debt.
```

This is inspired by epiplexity but is **not** the paper's formal epiplexity unless a coding model and time bound are instantiated exactly.

### Deterministic-transform principle for research

Do not dismiss a representation change because it cannot add logical information to the axioms.

A deterministic transform can still make latent structure computationally accessible:

```text
raw equation
  -> factorization
  -> symmetry visible
  -> invariant guessed
  -> theorem mechanically provable.
```

The transform has not made the theorem truer. It has changed what a bounded solver can see.

### Curriculum/order principle

Proof search order can matter computationally even when the final deductive closure is order-independent.

Prefer dependency orders that expose reusable structure early:

```text
symmetry theorem
-> quotient theorem
-> local certificates
-> implementation refinement
```

rather than proving many downstream instances before discovering the common cause.

## Lens C — Knowledge bang per proof buck

The project already uses `knowledge_bang` in `SKILL.md`. The two information-theoretic lenses sharpen its interpretation.

A proof can be short and still have low knowledge bang if it calls an opaque theorem or tactic that teaches nothing reusable. A somewhat longer structural proof can have higher knowledge bang when it:

- compresses many cases;
- exposes a generator/invariant;
- predicts counterexamples when assumptions are removed;
- transfers across representations;
- creates a reusable formal lemma;
- points directly to the next experiment;
- eliminates future proof obligations.

Add these optional 0–5 research-ranking fields:

- **GC — generative compression:** how many facts are generated by one mechanism?
- **OG — observer gain:** does the representation make the structure substantially easier for the available solver/toolchain to extract?
- **DG — downstream debt reduction:** how many future obligations disappear?
- **ML — mapping/lift debt:** how hard is it to translate the result back to the original problem? (subtract)

One heuristic extension is:

```text
knowledge_bang_plus =
    knowledge_bang + GC + OG + DG - ML.
```

Never use this score as proof authority.

## Lens D — Cross-pollination / dictionary search

User-supplied research portfolio, treated as a heuristic taxonomy.

When a domain is stuck, construct explicit dictionaries into mature neighboring theories.

Candidate dictionaries:

```text
discrete <-> continuous
combinatorial <-> geometric
static <-> dynamical/flow
point/object <-> moduli space of all objects
arithmetic <-> ergodic/spectral
finite combinatorics <-> Hodge/intersection theory
characteristic 0 <-> characteristic p / tilted representation
rough object <-> regularity structure / renormalized expansion
counting <-> geometry of numbers / orbit counting
one-dimensional weight <-> multidimensional optimization
```

For each dictionary require:

```text
forward map
information forgotten
new theorem/solver made available
lift/back-translation
smallest counterexample to the dictionary
```

Cross-pollination is not a license for metaphor. The bridge itself becomes a proof obligation.

## Lens E — Object -> moduli / orbit / family

Instead of studying one object, study the family containing it.

Questions:

- What is the moduli parameter?
- Which strata correspond to exceptional behavior?
- What group acts on presentations?
- Is the difficult event a divisor, orbit closure, singular stratum, or boundary component?
- Can the theorem be restated as avoidance/intersection of a locus?

Current SQIPrime example:

```text
one denominator vanishes
    -> theta null lies on product/decomposable locus
    -> reducible principal polarization
    -> reducible anti-isometry stratum
    -> Kani isogeny-diamond certificate.
```

The new language transforms many denominator checks into one geometric-locus question.

## Lens F — Continuous/discrete and asymptotic bridges

When exact finite structure is jagged, test a smooth or asymptotic surrogate, but preserve a lift obligation.

Useful moves:

- spectral relaxation of a finite graph;
- local-density / geometry-of-numbers approximation of a lattice count;
- continuous optimization for sieve/weight selection;
- limiting distribution or flow for repeated discrete transitions;
- convex relaxation followed by exact rounding verification.

Required safety rule:

```text
continuous result -> candidate mechanism
exact discrete verifier -> authority.
```

## Lens G — Flow/evolution instead of static classification

Introduce a parameter or process and track an invariant through time/steps.

Examples:

```text
isogeny composite -> quotient filtration
proof obligations -> monotone elimination process
lattice vector -> reduction flow
parameter family -> deformation to generic/easier member
bad configuration -> minimal-counterexample descent.
```

Ask whether singular/exceptional steps have a local surgery or normal form.

## Lens H — Structure vs randomness split

For a complicated object or distribution, explicitly decompose:

```text
structured component + pseudorandom/noise component.
```

Then assign different tools:

```text
algebra/geometry/formal proof -> structured component
probability/concentration/cryptographic indistinguishability -> random component.
```

In cryptography this split must respect adversarial observability. A structure that exists but cannot be efficiently extracted by the adversary may still be security-compatible.

## Lens I — Extremes and calibration

Always interrogate limiting and tiny cases:

```text
parameter = 0 or 1
smallest nontrivial prime/group/dimension
parameter -> infinity
rank one / full rank
identity map / zero map
maximal symmetry / generic trivial symmetry.
```

Use the extremes to determine scaling laws, exponents, and which hypotheses are structural.

Tao's trick archive includes the closely related practice of using basic examples to calibrate exponents.

## Lens J — Multidimensional lifting

If a one-parameter ansatz hits a barrier, lift it into a higher-dimensional feasible family and optimize there.

Search pattern:

```text
one scalar/weight
-> vector of weights
-> convex/variational feasible region
-> optimize global objective
-> project solution back to original claim.
```

This is useful beyond sieve theory: parameterized certificates, Lyapunov functions, interpolating invariants, and multi-object couplings can all benefit from this lift.

## Lens K — Invent a language when existing primitives create repeated debt

A new abstraction is justified when it removes recurring proof obligations rather than merely renaming them.

Creation test:

```text
Before new language: N repeated obligations.
After new language: one constructor law + one verifier + N trivial instantiations.
```

Examples already appearing in this project:

- `KernelCertificate` for compositional exact kernels;
- source-automorphism quotient for auxiliary distributions;
- accepted-normal-form criterion for serialization canonicality;
- Kani reducibility portal for theta product loci.

## Lens L — Paired-representation differential testing

Whenever a representation shift is proposed, keep two independent detectors.

Example:

```text
Representation A: theta geometry
  detector: vanishing even theta constants

Representation B: Kani arithmetic
  detector: isogeny-diamond / short Hom-lattice certificate
```

Require on finite controls:

```text
A says phenomenon <-> B says phenomenon.
```

This both tests the bridge and improves understanding. A mismatch is not noise; it identifies the exact semantic seam to investigate.

## Current SQIPrime application: hidden Kani certificate

For the auxiliary response graph on `n=2^e_auxiliary` torsion, write

```text
m = n-q*d,
A = [d*q] sigma,
B = [-q*d^2] tau.
```

All visible degrees/scalars are odd on the two-power torsion. Parameterizing the graph by its first coordinate yields the anti-isometry

```text
psi = B o A^-1 = [-d] tau o sigma^-1.
```

Using the dual relation

```text
sigma_hat o sigma = [deg(sigma)] = [d*m],
```

one obtains on `E0[n]`

```text
[m] psi = -tau o sigma_hat.
```

The right side has degree

```text
deg(tau)*deg(sigma) = q*d*m = (q*d)*m,
```

and

```text
q*d + m = n.
```

This exactly matches the arithmetic shape of Kani's reducibility criterion: the intended final product is explained by an isogeny-diamond certificate rather than by a coincidental theta-coordinate zero.

The next frontier is to determine whether any **proper prefix** admits an additional shorter diamond certificate. That turns the exceptional-locus question into a bounded Hom/quaternion congruence-lattice search, paired against the theta-null detector.

Status: structural reduction / search open. No production failure is claimed.

## Operational checklist

For each hard frontier problem, generate at least one candidate from each applicable family:

1. compression/generative description;
2. symmetry/orbit quotient;
3. moduli/exceptional-locus geometry;
4. duality/polarization;
5. filtration/flow;
6. cross-domain dictionary;
7. structure-vs-randomness decomposition;
8. finite toy / extreme case;
9. higher-dimensional optimization lift;
10. paired independent representation.

Rank candidates by `knowledge_bang_plus`, then falsify the top candidates before formal promotion.
