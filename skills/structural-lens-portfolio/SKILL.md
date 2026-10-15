# Structural Lens Portfolio

## Purpose

Use this skill when the current representation is plausible but not obviously the highest-knowledge route to the theorem.

The skill generates a portfolio of candidate lenses drawn from algorithmic information theory, algorithmic statistics, computationally bounded structural information, Fourier/harmonic analysis, geometry, dynamics, and cross-field dictionaries.

It is an **advisory search skill**, not a proof rule. Every representation shift remains a `REFORMULATION`/`HYPOTHESIS` atom until its semantic relation to the root problem is checked.

## Core distinction

Separate three questions that are often conflated:

```text
1. Is the object compressible in principle?
2. Is there a compact model that explains the relevant regularity?
3. Can our bounded solver/toolchain actually extract and exploit that model?
```

AIT speaks primarily to (1). Algorithmic statistics/structure functions sharpen (2). Epiplexity motivates making (3) explicit.

## Lens A — Algorithmic statistic / explanatory compression

Primary sources:

- Chaitin, *Algorithmic Information Theory: Some Recollections*, arXiv:math/0701164.
- Gács, Tromp, Vitányi, *Algorithmic Statistics*, IEEE TIT 47(6), 2001.
- Vereshchagin, Vitányi, *Kolmogorov's Structure Functions and Model Selection*, IEEE TIT / arXiv:cs/0204037.

The algorithmic-statistics picture is a two-part description:

```text
object/evidence = model carrying regularity + residual specification.
```

Research translation:

```text
proof/case corpus
  -> structural theorem/invariant
  + explicit residual assumptions/exceptions.
```

Questions:

- What single theorem makes the largest fraction of current checks corollaries?
- Which assumptions are stored in the model, and which remain case-specific residue?
- Does a representation shift shrink the residual obligation set without inflating the model into an opaque black box?
- Can deleted-premise counterexamples describe exactly why the model is minimal?

Never claim to compute Kolmogorov complexity. Exact complexity is uncomputable. Literal source length, AST size, proof-term size, number of assumptions, and residual-obligation size are transparent proxies only.

## Lens B — Epiplexity / bounded-observer structure

Primary source:

- Finzi et al., *From Entropy to Epiplexity: Rethinking Information for Computationally Bounded Intelligence*, arXiv:2601.03220 (2026).

The paper defines epiplexity with a compute bound `T`: among `T`-time probabilistic models, choose the model minimizing two-part MDL; epiplexity is the optimal model-program length and time-bounded entropy is the residual code length.

Research translation:

```text
problem representation R
+ solver set S
+ budget T
  -> structure extractable by S within T.
```

Use this lens to compare representations relative to the actual toolchain:

```text
Lean
Sage/PARI
Julia/numerics
SMT/SAT
finite enumeration
lattice/CVP
Fourier/spectral routines
Morph/LEAP portals.
```

Ask:

- Which representation turns the hard insight into a standard solver portal?
- Does a deterministic preprocessing step increase solver-visible structure?
- Is a short mathematical description computationally inaccessible, while a larger equivalent representation is easy to solve?
- Where is the phase boundary as the compute budget grows?

Do not call a heuristic score "epiplexity" unless the exact model class/runtime definition is instantiated. Use names like `bounded-structure proxy` or `epiplexity-inspired ranking`.

## Lens C — Structure versus pseudorandomness

Primary source:

- Terence Tao, *Structure and randomness in Fourier analysis and number theory* (Simons Lecture I, 2007).

Search for

```text
object = structured component + pseudorandom residual.
```

The residual is not "random" absolutely. It is pseudorandom relative to a declared family of tests/statistics.

Desired proof shape:

```text
classify every structured obstruction
+ prove residual is orthogonal/uniform for the target statistic
------------------------------------------------------------
reduce the theorem to finitely many structured cases.
```

This is especially useful for distributions, graphs, hint samplers, lattice shells, and additive patterns.

## Lens D — Fourier / spectral diagonalization

Use when the native problem contains:

- convolution;
- translation;
- periodicity;
- correlations;
- repeated local interactions;
- group actions;
- lattice point counts;
- oscillation;
- a structured/random decomposition.

Representation shift:

```text
object domain
 -> characters / Fourier coefficients / eigenfunctions / theta series
 -> diagonal or sparse obstruction data.
```

High-value moves:

1. **Finite-group Fourier transform.** For a finite abelian quotient, use characters to diagonalize convolution and count residue-class constraints.
2. **Poisson summation.** Replace primal lattice sums with dual-lattice sums when one side has better decay or arithmetic structure.
3. **Theta series.** Encode shell counts/minimal norms as coefficients of a generating function.
4. **Major/minor or low/high frequency split.** Isolate a finite family of structured modes and prove cancellation elsewhere.
5. **Auxiliary-function certificate.** Search for a function and Fourier transform with complementary sign/zero constraints, in the spirit of linear-programming bounds.

Primary exemplars:

- Cohn--Elkies linear programming bounds for sphere packing.
- Viazovska, *The sphere packing problem in dimension 8*, Annals of Mathematics 185 (2017): a modular/Fourier auxiliary-function construction makes the optimal linear-programming bound exact.
- Tao's Fourier structure/randomness lectures.

Hong Wang's 2026 Fields Medal work is rooted in harmonic analysis and geometric measure theory; Kakeya is central to Fourier restriction theory. The lesson is not that every problem should be Fourier transformed, but that geometry can be the hidden structure controlling a Fourier-analytic obstruction.

## Lens E — Cross-field dictionary

Try to map the problem into a field with stronger mature theorems.

Examples of dictionary types:

```text
combinatorics <-> algebraic geometry / Hodge theory
number theory <-> dynamics / ergodic theory
discrete objects <-> continuous limits
cryptographic ideals <-> lattices / quadratic forms
isogeny graphs <-> module homomorphisms
product theta locus <-> reducible polarization <-> Kani diamonds.
```

A dictionary must have explicit lift obligations. Analogy alone has no authority.

## Lens F — Moduli / family space

Replace one difficult object by the space of all such objects.

Look for:

- generic strata;
- exceptional divisors/loci;
- stabilizers;
- degenerations;
- flows through parameter space.

A recurring gain is converting many denominator exceptions into membership in one named geometric exceptional locus.

## Lens G — Continuous-discrete bridge

Use a continuous relaxation or scaling limit only when there is a quantitative lift back.

Needed artifact:

```text
continuous solution
+ stability/error theorem
+ rounding/discretization certificate
-> discrete conclusion.
```

## Lens H — Flow / evolution

Instead of classifying static objects, evolve them toward a canonical form while tracking a monovariant or conserved structure.

The singularities/events in the flow may be easier to classify than arbitrary starting states.

## Lens I — Extremes and phase boundaries

For a parameter `N`, test:

```text
N=1
smallest nontrivial N
first degenerate N
N -> infinity
threshold where one proof mechanism stops working.
```

Do not extrapolate from extremes without a stability or monotonicity argument. The purpose is to discover the correct phase diagram.

## Knowledge-bang integration

Combine this skill with `hidden-structure-discovery`.

Prefer representations which produce:

- high explanatory compression;
- low residual obligation count;
- high theorem fanout;
- high invariance under coordinates/bases;
- strong deleted-premise counterexamples;
- short reusable formal lemmas;
- reachable solver portals under the real compute budget.

A larger formal object may be superior if it has higher **bounded extractability** for the current solver set.

## Research Kernel workflow

For a hard frontier atom:

1. `rk_retrieve` prior failures and analogous structures.
2. Instantiate at least four distinct lenses, not four variations of one lens.
3. Store each as a `REFORMULATION` with `CANDIDATE` status.
4. State the semantic edge that would connect it to the original claim.
5. Run cheap falsifiers on the edge before investing in the child problem.
6. Score/rank by evidence potential and expected reduction in residual obligations.
7. Use Morph/LEAP to search inside the best representation.
8. Attach source-bound evidence and formal proofs to the *mechanism*.
9. Keep the original representation as an independent differential test.
10. Promote only through the normal fail-closed Research Kernel gate.

## Preferred artifact for an AIT/epiplexity comparison

```text
REPRESENTATION A
model/mechanism:
residual obligations:
available solvers:
measured runtime/proof effort:
failed assumptions:

REPRESENTATION B
model/mechanism:
residual obligations:
available solvers:
measured runtime/proof effort:
failed assumptions:

WHY B EXPOSES MORE STRUCTURE
state the invariant/portal, not merely the lower runtime.

NONCLAIMS
state clearly that proxy description lengths are not Kolmogorov complexity or formal epiplexity.
```
