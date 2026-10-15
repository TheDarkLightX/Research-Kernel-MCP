# Forgotten-Information Audit for Representation Shifts

Status: **research-search and falsification policy, not proof authority**.

A representation shift is useful only if the information it forgets is
irrelevant to the claim being transferred, or if that information can be
reconstructed by an explicit lift/certificate.

This lens exists because abstraction can make a problem beautifully simple
while silently deleting the very observable that decides correctness.

## Core criterion

Let

```text
A : X -> Y
```

be an abstraction/reformulation map and let

```text
P : X -> O
```

be any predicate/observable used by the downstream theorem, solver, branch, or
promotion gate.

For `P` to be decidable from the abstraction alone, it must be constant on
fibers:

```text
boxed:
A(x)=A(y) -> P(x)=P(y).
```

More generally, if a downstream transition `T` is used, require an appropriate
commuting/refinement square rather than only output equality.

If the fiberwise condition fails, the abstraction is **not semantically
sufficient for that observable**.  It may still be useful for another claim.

## Audit procedure

### 1. Write the abstraction contract

```text
original state X:
abstract state Y:
map A:X->Y:
claim/observable P:
information intentionally forgotten:
```

Never say merely “these representations are equivalent” without naming the
observable and lift obligations.

### 2. Search one abstraction fiber adversarially

Try to construct

```text
x1 != x2
A(x1)=A(x2)
```

but

```text
P(x1) != P(x2).
```

This is often much cheaper than searching for a counterexample to the final
theorem.

Good mutation dimensions:

- coordinate model / isomorphic presentation;
- hidden subgroup/ideal/line data;
- orientation or sign;
- multiplicity;
- path/history producing the same endpoint;
- noncanonical serialization;
- latent state erased by a projection;
- automorphism/isomorphism class data;
- witness lineage.

### 3. Classify every forgotten field

For each deleted feature, label it:

```text
PROVED IRRELEVANT
RECOVERABLE FROM CERTIFICATE
PRESERVED ONLY UP TO GROUP ACTION
OBSERVABLE-DEPENDENT
UNKNOWN
COUNTEREXAMPLE FOUND
```

Unknown is not equivalent to irrelevant.

### 4. Differential-test paired representations

On complete finite controls when possible, compute the deciding observable in
both representations independently.

Require

```text
original detector == abstract detector
```

for every test instance.

A mismatch is not noise.  Minimize it and inspect which forgotten feature
separates the two originals in the same abstraction fiber.

### 5. Repair the abstraction, not the counterexample

Preferred repairs:

```text
add the missing invariant to Y;
replace Y by a quotient that retains the relevant orbit type;
attach a lift/refinement certificate;
change the downstream observable to one genuinely fiber-constant;
use a stronger invariant predicate directly on X.
```

Do not accumulate exceptions around an abstraction known to be insufficient.

## Current SQIPrime example

A simplified 2-adic state machine retained torsion projection matrices and
transported source automorphism data while forgetting the **actual evolving
elliptic curve models and their current isomorphisms**.

It found no unhandled product graph through modulus 32.

A stronger exact elliptic model produced a source-producible `p=127,e=5`
witness whose path ends in

```text
non-E0 factor curves E1,E2
+ an actual isomorphism eta:E1->E2
+ residual top graph = Graph(eta|E1[2]).
```

The coarse abstraction had no way to recognize that current isomorphism, so the
product-locus observable was **not constant on the abstraction fibers**.

The correct repair was not a larger matrix census.  It was to change the local
predicate to the actual invariant:

```text
is the current graph induced by some elliptic isomorphism eta:E1->E2?
```

and use the universal isomorphism-graph quotient.

This is a model example of why smaller representations need semantic-loss
proofs, not only empirical agreement.

## Relation to information/compression lenses

Compression and epiplexity-style observer gain reward representations that make
structure easier to extract.  This audit supplies the complementary penalty:

```text
compression gain
-
semantic information loss relevant to the target.
```

A high-compression representation with an unproved fiber-sufficiency condition
should receive high mapping/lift debt rather than high confidence.

## Research Kernel handling

Recommended atom/edge pattern:

```text
REFORMULATION: A:X->Y
CLAIM: P transfers through A
QUESTION: is P constant on fibers of A?
EXPERIMENT: paired-representation differential
COUNTEREXAMPLE: x1,x2 with same A-image, different P
SUPERSEDES: repaired abstraction A'
```

If a counterexample is found, preserve the failed abstraction as negative
knowledge.  Do not silently delete it: future agents should learn which
information was necessary.

## Morph/LEAP use

Morph should treat this as a precondition audit for any candidate transition
that forgets information.  LEAP can search finite abstraction fibers for pairs
that disagree on the downstream observable.

Suggested tactic name:

```text
audit_forgotten_information
```

## Nonclaims

- Fiberwise empirical agreement on bounded controls does not prove universal
  sufficiency.
- Some abstractions are intentionally one-way reductions; they need the
  corresponding lift theorem rather than full fiber constancy.
- The audit does not forbid lossy representations.  It requires their loss to
  be compatible with the exact claim being transferred.
