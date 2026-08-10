# Fourier and Multiscale Hidden-Structure Lens

Status: **research-search policy, not proof authority**.

Use this companion to `SKILL.md` when a problem contains convolution, lattices,
oscillation, periodicity, translation invariance, scale interactions, geometric
tubes, incidence patterns, or a difficult primal constraint whose dual version
may be simpler.

The purpose is not to say “try Fourier analysis” generically.  The purpose is
to generate a small set of explicit representation changes with preservation,
reflection, and falsification obligations.

## Primary-source anchors

### Maryna Viazovska

- Maryna Viazovska, *The sphere packing problem in dimension 8*,
  arXiv:1603.04246.
- IMU Fields Medal 2022 citation: proof of optimality of the E8 packing and
  contributions to interpolation problems in Fourier analysis.

Source-backed mechanisms from the E8 proof include:

- replace packing optimality by the Cohn--Elkies linear-programming auxiliary
  function problem;
- require simultaneous sign constraints on a function and its Fourier
  transform;
- use Poisson summation to force equality conditions and therefore forced
  lattice zeros;
- decompose the construction into Fourier eigenfunctions with eigenvalues
  `+1` and `-1`;
- use modular/quasimodular forms to construct functions with prescribed double
  zeros;
- combine the eigenfunctions to obtain one sharp dual certificate.

### Hong Wang

- IMU Fields Medal 2026 citation: harmonic analysis and geometric measure
  theory, including multiscale and decoupling techniques, Fourier restriction,
  Falconer/Furstenberg problems, and Kakeya in three dimensions.
- Yumeng Ou and Hong Wang, *A cone restriction estimate using polynomial
  partitioning*, arXiv:1704.05485.
- Hong Wang, *A restriction estimate in R^3 using brooms*, arXiv:1802.04312.
- Xiumin Du, Larry Guth, Yumeng Ou, Hong Wang, Bobby Wilson, Ruixiang Zhang,
  *Weighted restriction estimates and application to Falconer distance set
  problem*, arXiv:1802.10186.
- Shaoming Guo, Changkeun Oh, Hong Wang, Shukun Wu, Ruixiang Zhang,
  *The Bochner--Riesz problem: an old approach revisited*, arXiv:2104.11188.

Source-backed mechanisms include polynomial partitioning, broad estimates,
refined Strichartz estimates, geometric structure in wave packets, and
multi-parameter induction on scales.

## Lens F1 -- Physical space <-> frequency space

### Trigger

The problem has one or more of:

```text
convolution
translation invariance
periodicity / lattice structure
oscillation
quadratic or additive energy
correlation
repeated local interactions
```

### Transform

Construct the Fourier-side statement explicitly:

```text
object f
   <-> Fourier transform f_hat

convolution
   <-> multiplication

translation
   <-> phase

periodic/lattice sum
   <-> dual-frequency/lattice sum

correlation/energy
   <-> spectral mass
```

Do not discard the original representation.  Keep a paired differential and
ask which quantities become diagonal, sparse, positive, or local after the
transform.

### Obligations

- state the transform convention and function/distribution class;
- prove inversion or the exact one-way reduction used;
- track normalization constants;
- preserve boundary/decay hypotheses;
- test a finite/discrete analogue where both sides can be computed exactly.

## Lens F2 -- Viazovska dual-certificate design

The high-value move is not merely Fourier transformation.  It is to replace a
hard primal extremal problem by the construction of **one auxiliary object whose
primal and Fourier-side signs certify the optimum**.

Search pattern:

```text
hard extremal problem
 -> valid dual/linear-programming bound
 -> characterize equality conditions
 -> infer forced zeros / multiplicities / interpolation data
 -> construct an object satisfying those conditions
 -> certify the original optimum
```

Questions:

1. Is there a dual inequality whose equality would solve the problem?
2. What must vanish if equality occurs?
3. Do those zeros determine an interpolation problem?
4. Can symmetry force the auxiliary function into a Fourier eigenspace?
5. Is there a mature function space (modular forms, orthogonal polynomials,
   theta functions, characters, automorphic forms) where the interpolation
   constraints become linear algebra?

### Knowledge-bang preference

Prefer a certificate that simultaneously:

- proves the bound;
- explains equality;
- explains uniqueness;
- predicts all forced zeros;
- transports to neighboring extremal problems.

## Lens F3 -- Poisson summation / dual lattice portal

### Trigger

There is a lattice, periodic sum, congruence class, shifted lattice, or repeated
integer translation.

### Transform

Try:

```text
sum over lattice/coset
   <-> sum over dual lattice/characters
```

For a shifted lattice, retain the character/phase induced by the shift.

Use cases:

- count or exclude lattice points on a norm shell;
- expose cancellation invisible in direct enumeration;
- turn congruence restrictions into character weights;
- derive theta-series or shifted-theta-series coefficients;
- compare local neighbor moves through Hecke/Fourier data.

### Fast pre-Poisson geometry check

Before invoking harmonic analysis, compare shell radius with lattice spacing.
For a coset

```text
r + M Z^d
```

and a Euclidean shell of radius `rho`, if `2*rho < M` in each coordinate
spacing direction, at most one centered coset representative can lie in the
ball.  Then the problem is a direct centered-residue norm check, not a spectral
problem.

This detector is especially valuable because it prevents expensive
factorization or Fourier machinery when geometry already forces sparsity.

## Lens F4 -- Fourier eigenspace decomposition

If the Fourier transform has finite order on the chosen function space, split
into eigenspaces before designing the object.

Typical pattern:

```text
f = f_+ + f_-
F(f_+) = +f_+
F(f_-) = -f_-
```

or the appropriate fourth-root-of-unity eigenspaces.

Benefits:

- primal and dual constraints become coupled algebraically;
- interpolation constraints split into smaller systems;
- symmetry becomes explicit;
- a difficult transform identity becomes a scalar eigenvalue relation.

Obligation: prove the decomposition preserves the admissible function class and
that recombination preserves every sign/zero constraint.

## Lens F5 -- Forced-zero / interpolation inversion

When a sharp inequality and a dual identity squeeze to equality, do not stop at
“the bounds match.”  Extract every equality condition.

Search for:

```text
sign inequality + exact dual identity
 -> every nonzero term must vanish
 -> zeros / double zeros / contact points
 -> interpolation problem
 -> constructive basis or finite-dimensional ansatz
```

This is a Noether-style move: the equality is explained by shared vanishing
structure rather than two unrelated numerical bounds.

## Lens W1 -- Wave-packet decomposition

### Trigger

An oscillatory/Fourier object has interacting location and direction/frequency,
or geometric incidence patterns resemble tubes/plates/caps.

### Transform

Decompose into packets localized in both frequency and physical geometry:

```text
frequency cap
 -> spatial tube/plate packet
```

Then classify interactions geometrically.

Research translation outside harmonic analysis:

```text
large global object
 -> localized directional packets
 -> incidence graph / concentration profile
 -> separate generic transverse interactions from clustered/tangent ones
```

Obligations:

- reconstruction/error bound;
- scale and localization definitions;
- no double-counting or uncontrolled packet overlap;
- exact or bounded lift back to the original object.

## Lens W2 -- Polynomial partitioning

### Trigger

The hard part is spatial/geometric concentration and no single coordinate
system makes all incidences simple.

### Transform

Choose a low-degree polynomial whose zero set partitions space into cells.
Separate:

```text
cellular contribution
+
wall / algebraic contribution.
```

Then recurse or apply different tools to the two regimes.

Research translation:

- partition a state space by a learned/algebraic invariant;
- isolate exceptional algebraic strata instead of treating them as scattered
  edge cases;
- solve generic cells with one uniform theorem and reserve specialized
  machinery for the wall.

Obligation: every original configuration must be assigned to a controlled cell
or wall contribution with a quantitative accounting identity/inequality.

## Lens W3 -- Broad / narrow decomposition

Separate configurations with genuinely transverse/diverse directions from
those concentrated near a lower-dimensional family.

```text
broad = many independent directions
narrow = concentrated near one subspace/algebraic family
```

Use different tools:

```text
broad -> multilinear/transversality estimate
narrow -> dimension reduction / induction / specialized structure theorem
```

Research translation:

```text
many independent failure modes -> robust global bound
concentrated failure modes      -> reveal hidden lower-dimensional structure
```

This is a precise version of structure-versus-randomness: concentration is not
noise; it is evidence for a lower-dimensional model.

## Lens W4 -- Induction on scales

### Trigger

The same obstruction reappears after zooming, rescaling, or conditioning.

### Transform

State an explicit recurrence across scales:

```text
Goal(R)
 <= structured term at scale R
  + contraction * Goal(R^theta)
  + controlled error.
```

For multi-parameter problems, allow a vector of scales rather than forcing one
scalar resolution.

Obligations:

- base scale;
- monotone or contractive recurrence;
- constants remain summable;
- rescaling preserves the hypotheses;
- no circular use of the target estimate.

## Lens W5 -- Geometry first, analysis second

Hong Wang's restriction/Kakeya work repeatedly makes geometric organization of
tubes/wave packets part of the proof engine.  General research translation:

```text
analytic inequality
 -> identify geometric support/incidence object
 -> classify its multiscale geometry
 -> feed that geometry back into the analytic estimate.
```

When an inequality appears inexplicably weak, ask whether the missing
information is geometric arrangement rather than a better scalar bound.

## Lens F/W -- Paired frequency and multiscale tournament

When both families apply, run them as independent representations.

Candidate A -- Viazovska style:

```text
dual certificate / Fourier eigenfunction / interpolation / theta series
```

Candidate B -- Wang style:

```text
wave packets / broad-narrow / partitioning / induction on scales
```

Require a common observable or finite model on which both representations can
be tested.

A mismatch is a high-value semantic seam.

## Current isogeny-cryptography application

The supercritical Kani arithmetic currently reduces to

```text
u^2+v^2 = R,
(u,v) == (U0,V0) mod 2L.
```

This is a shifted Gaussian-lattice shell.  The Fourier lens says to view its
indicator coefficient as a shifted theta-series coefficient, with Poisson or
character decomposition available if the direct geometry does not decide it.

Before Fourier expansion, however, use the sparse-shell detector:

```text
R < L^2
 -> sqrt(R) < L
 -> at most one centered representative of the 2L-coset can lie on the shell
 -> existence iff the centered residue has norm exactly R.
```

This can turn a large integer-factorization problem into one exact norm check.

The Wang-style lens then becomes relevant when many nearby shells/scales survive:
organize them by distance past the phase boundary, tail direction/content, and
scale, then use a multiscale recurrence rather than independent searches.

## Research Kernel usage

When storing these moves with `rk_morph` or as `REFORMULATION` atoms, use tags
such as:

```text
fourier_dual
poisson_summation
dual_certificate
fourier_eigenspace
forced_zero_interpolation
shifted_lattice_shell
wave_packet
polynomial_partition
broad_narrow
induction_on_scales
multiscale_geometry
```

Each candidate must record:

```text
forward transform
inverse/lift or reflection condition
information forgotten
new solver/theorem made available
smallest falsifier
translation debt
```

A Fourier or multiscale reformulation is discovery evidence only.  Promotion
still requires independent source/proof/executable evidence under the ordinary
Research Kernel gates.
