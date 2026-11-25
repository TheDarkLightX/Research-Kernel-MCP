# Independent Congruence Lattices as a Sparsification Lens

Status: **research-search policy, not proof authority**.

Use this lens when a hard arithmetic/geometric problem has already been reduced
to a lattice shell or affine congruence class, but the remaining shell still
contains too many candidate points for direct enumeration.

## Core move

Do not solve the first congruence lattice in isolation.

Search for every other **exact, independently sourced congruence or dual
constraint** and intersect them before invoking factorization, CVP, Poisson
summation, or lattice enumeration.

Generic pattern:

```text
hard shell:
    Q(x)=R,
    x in r1 + Lambda1

additional exact structure:
    x in r2 + Lambda2

combine first:
    x in (r1+Lambda1) intersect (r2+Lambda2)
      = r + Lambda_intersection

then compare:
    shell radius
    versus
    minimum spacing / covering geometry of Lambda_intersection.
```

The intersection may have much larger determinant/spacing than either lattice
alone.  A dense shell can become a one-point test.

## Trigger conditions

Invoke this lens when one or more apply:

1. a modular or torsion relation gives one affine lattice;
2. an ideal, kernel/image line, dual map, conservation law, parity law, or
   second modulus gives another;
3. the first lattice shell is too dense for the sparse-shell detector;
4. factorization or representation enumeration is becoming the bottleneck;
5. different parts of the proof naturally live at coprime primes/moduli;
6. the object belongs to a proper ideal/submodule that has not yet been used by
   the shell solver.

## Coprime-modulus portal

The highest-yield special case is

```text
x == a mod M,
x == b mod N,
gcd(M,N)=1.
```

CRT gives one residue modulo `MN`.  The coordinate spacing multiplies from
roughly `M` or `N` to `MN`.

Before doing anything more sophisticated, test whether

```text
2 * shell_radius < combined_spacing.
```

If yes, only the centered CRT representative can survive.

This is the arithmetic analogue of Viazovska-style dual certification: adding a
second exact dual/congruence condition can make the equality case rigid enough
that construction/enumeration disappears.

## Ideal / kernel-line translation

An algebraic ideal constraint often has a simpler finite-field shadow.

Examples:

```text
alpha in ideal J
 -> alpha mod p has image in a fixed line/subspace
 -> one or more linear congruences on coordinates
```

or

```text
alpha factors through phi
 -> ker(phi) <= ker(alpha)
 -> finite torsion action satisfies a rank/image condition.
```

Prefer the lowest-dimensional exact shadow that retains the ideal membership.
A rank-four ideal condition may become a 2-by-2 linear system modulo one prime.

## Exceptional-rank audit

If the added linear system is expected to be invertible generically, classify
exactly when it loses rank.

Search for:

```text
coefficient rows become dependent
<-> distinguished line/subspace is invariant under a symmetry
<-> exceptional geometric/arithmetic stratum.
```

Do not hide singular cases inside generic code.  They often correspond to the
same exceptional locus already seen elsewhere in the problem.

## Multiscale use

At each scale `L`:

```text
local congruence at scale L
+
scale-independent ideal/dual congruence
 -> combined lattice at scale L
 -> sparse/non-sparse decision.
```

If the second modulus is fixed and coprime to every scale modulus, the combined
spacing grows proportionally with `L`; this can turn an entire multiscale family
into uniformly sparse shells.

## Current SQIPrime example

Direction-first Kani arithmetic gives

```text
u^2+v^2=R,
(u,v)==(U2,V2) mod 2L.
```

For the degree-q secret isogeny `tau`, a real Kani core satisfies

```text
alpha=tau_hat o g,
im(alpha mod q) <= K_tau=ker(tau).
```

For an ordinary non-loop secret, fixing the non-Gaussian tail makes that image-
line condition a nonsingular 2-by-2 system for the Gaussian coefficients
`(a,b) mod q`.  Therefore it supplies one residue

```text
(u,v)==(Uq,Vq) mod q.
```

CRT yields

```text
(u,v)==(U,V) mod 2Lq.
```

while every Kani residual has

```text
R < q L^2 < (qL)^2.
```

Thus the combined shell is automatically sparse: existence reduces to the norm
of one centered CRT point.

The key methodological lesson is broader than isogenies:

```text
a dense lattice shell may be an artifact of forgetting an independent ideal,
dual, or congruence constraint.
```

## Required obligations

Before trusting this move:

1. prove each congruence/ideal condition independently;
2. prove the constraints refer to the same coordinate/model convention, or
   prove common-conjugacy invariance;
3. verify CRT/copime assumptions exactly;
4. compute the true combined lattice spacing, not a heuristic determinant;
5. classify singular/exceptional rank cases;
6. keep a positive control where the unique centered point really lies on the
   shell and a mutation control where it does not;
7. treat a surviving point as a candidate until the original semantic object is
   reconstructed and verified.

## Research-Kernel tags

Suggested tags:

```text
congruence_intersection
crt_sparsification
ideal_shadow
kernel_line
independent_constraint
shifted_lattice_shell
sparse_shell
rank_exception
```

This lens ranks search actions; it does not promote claims or replace formal,
source-bound, or executable evidence.
