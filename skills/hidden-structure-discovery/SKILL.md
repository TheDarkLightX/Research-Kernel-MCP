# Hidden-Structure Discovery

## Purpose

Use this skill when a proof, research problem, or implementation audit is becoming coordinate-heavy, case-heavy, assumption-heavy, or conceptually opaque.

The goal is not merely to prove the current proposition. The goal is to find a representation in which the proposition is *forced by a small structural mechanism*, so that one theorem explains many cases at once.

This combines three methodological ideas:

- **Noetherian inner-ground principle:** prefer a proof that discloses the mechanism producing an equality or invariant over two unrelated bounds or a long case split.
- **Tao-style problem-solving tricks:** counterexample pressure, essential special cases, abstraction of irrelevant data, alternate special cases of the abstraction, symmetry audits, operation reordering, approximation, and strengthening/reframing.
- **Tricki-style navigation:** classify techniques by the difficulty being faced rather than only by mathematical subject; record reusable triggers so the next problem can reach the right technique faster.

Primary methodological sources:

- Terence Tao, “245A: Problem solving strategies”: https://terrytao.wordpress.com/2010/10/21/245a-problem-solving-strategies/
- Terence Tao, tricks category: https://terrytao.wordpress.com/category/expository/tricks/
- Tricki static archive: https://tricki.sisask.com/
- Timothy Gowers, “The forthcoming launch of the Tricki”: https://gowers.wordpress.com/2008/10/15/the-forthcoming-launch-of-the-tricki/

For additional compression, epiplexity, cross-domain, moduli, flow, structure/randomness, and Fields-Medalist-style representation lenses, also read:

- `skills/hidden-structure-discovery/LENSES.md`

## Core rule

Do not ask only:

```text
Can I prove P?
```

Also ask:

```text
What is the smallest invariant, symmetry, quotient, universal property,
conservation law, filtration, or functorial mechanism that makes P inevitable?
```

A proof with the same truth value can still be substantially better if it:

- explains more examples;
- uses fewer accidental coordinates;
- survives more representation changes;
- exposes exactly which assumptions matter;
- generates useful corollaries;
- makes counterexamples easier to classify;
- creates smaller formal proof obligations;
- transfers to neighboring problems.

## Trigger conditions

Invoke this skill especially when one or more of these symptoms appears.

1. The proof is mostly coordinate manipulation.
2. Several arbitrary choices appear: basis, sign, square root, ordering, gauge, representative, normalization, or chart.
3. The same argument is repeated in many cases.
4. Equality is established by unrelated upper and lower bounds even though a direct structure might identify both sides.
5. A theorem is invariant under a symmetry, but an intermediate quantity is not.
6. The implementation has many branches but the mathematical output should be canonical up to isomorphism.
7. Exhaustive computation repeatedly succeeds but has not explained why.
8. One exceptional case dominates the complexity.
9. The statement changes little under a representation shift but the proof changes dramatically.
10. A long end-to-end proof can plausibly be replaced by local certificates plus composition.
11. The conclusion and hypotheses live in visibly different representations.
12. A constant or degree relation looks numerological rather than forced.

These symptoms usually indicate **representation debt**: the proof is paying for distinctions that the theorem itself does not care about.

## Hidden-structure search loop

### 1. Freeze the exact claim

Write:

```text
CLAIM:
ASSUMPTIONS:
OBSERVABLE/OUTPUT:
NONCLAIMS:
```

Do not let a representation shift silently strengthen or weaken the research target.

### 2. Try to falsify it first

Prefer the smallest hostile examples:

- smallest field/group/ring;
- degenerate or boundary parameters;
- exceptional automorphism classes;
- repeated roots or zero divisors;
- deleted-premise mutants;
- wrong basis/sign/order/gauge;
- one-dimensional or rank-one reductions;
- exhaustive finite models when available.

When the counterexample attempt fails, record **why it failed**. That obstruction is often the desired invariant.

Tao-style question:

```text
What prevented my attempted counterexample from existing?
```

Promote the obstruction, not the failed example, into the next theorem candidate.

### 3. Make an essential toy, not a trivial toy

Delete everything except one unresolved difficulty.

A useful special case preserves the obstruction. If the special case becomes trivial, it has probably deleted the phenomenon instead of isolating it.

Calibrate with several toys that vary one feature at a time:

```text
same obstruction + fewer coordinates
same symmetry + smaller dimension
same kernel + simpler codomain
same distribution + finite group
same quotient + canonical representative
```

### 4. Forget irrelevant information

Apply a forgetful abstraction deliberately.

Candidate deletions:

- coordinates -> abstract object;
- object -> isomorphism class;
- point -> orbit;
- map formula -> kernel/image/universal property;
- chosen basis -> subspace/submodule;
- probability sampler -> orbit/fiber counts;
- implementation branch -> semantic contract;
- long composite -> local transition certificates;
- elliptic coordinates -> module homomorphism;
- matrix entries -> rank/determinant/conjugacy class.

Then ask whether the theorem is still meaningful. If yes, the forgotten structure was probably not part of the inner ground.

### 5. Use Tao's alternate-special-case move

After abstracting, choose a **new special case of the abstraction that is not merely the original problem made smaller**.

Examples:

```text
elliptic torsion problem
  -> finite rank-two module problem
  -> test on F_q^2 matrices

coordinate square-root ambiguity
  -> action of an abstract sign group
  -> test an arbitrary pointed set with an injective common post-map

long isogeny chain
  -> filtered kernel composition
  -> test arbitrary finite abelian groups
```

This move is valuable because the alternate setting can reveal which statement is representation-independent.

### 6. Perform a symmetry audit

List the symmetries of the claim and compare them with the symmetries of the proof.

```text
statement symmetries:
proof/intermediate symmetries:
missing symmetry:
```

If the statement is invariant under a group action but the proof depends heavily on a representative, suspect an inefficient proof.

Try:

- quotient by the action;
- average over the action;
- fix a gauge/canonical representative;
- conjugate to a convenient basis;
- replace representative equality by orbit equality;
- transport the claim along an isomorphism;
- amplify an asymmetric intermediate statement into a symmetric one.

A recurring pattern is:

```text
arbitrary choice
    -> group action / gauge freedom
    -> common invertible transport
    -> invariant fiber/kernel/law
```

### 7. Search a representation portfolio

Use Research Kernel `rk_morph`, Morph, or LEAP to generate several explicit candidate representations before committing to one proof route.

High-yield modes:

- `equivalent_statement`
- `stronger_statement`
- `weaker_statement`
- `counterexample_search`
- `invariant_form`
- `dual_problem`
- `graph_form`
- `formal_spec`
- `implementation_obligation`
- `symmetry_quotient`
- `gauge_fixing`
- `filtration_form`
- `polarization_duality`
- `alternate_special_case`
- `universal_property`
- `operation_reorder`

Representation shifts to consider:

```text
coordinates <-> invariant algebra
maps <-> kernels/images
sets <-> indicator functions
objects <-> quotient/orbit classes
local formulas <-> universal property
composite <-> filtration
primal <-> dual/polarized dual
probabilities <-> finite fiber counts
graph <-> matrix <-> module <-> logic
```

Every shift is a candidate until its relation to the original problem is checked.

### 8. Reorder operations

When a proof contains two nested operations, try swapping or combining them.

Examples:

- sum/integral order;
- quotient then transport versus transport then quotient;
- average then pushforward versus pushforward then average;
- compose maps locally rather than expand global coordinates;
- combine factor problems into a product space to expose a symmetry;
- prove a kernel statement before an explicit map identity.

The product representation often reveals symmetry that neither factor exposes alone.

### 9. Dualize, complement, or polarize

When a relation has an unexplained complementary quantity, search for a dual identity.

Examples:

```text
subobject <-> quotient
kernel <-> image of dual
upper bound <-> complement lower bound
map <-> adjoint/dual map
isogeny <-> dual isogeny
component degrees <-> polarization identity
```

A relation such as

```text
a + b = N
```

is often better explained by one conservation/polarization law than by calculating `a` and `b` separately.

### 10. Look for a filtration or local certificate

Replace a monolithic proof with repeated local structure when possible.

Desired shape:

```text
K0 --local quotient--> K1 --local quotient--> ... --local quotient--> Kn
```

Prove one reusable composition theorem, then instantiate a small local contract at every step.

Prefer:

```text
local invariant + composition law -> global theorem
```

over:

```text
expand the entire composite and simplify.
```

### 11. Strengthen toward the invariant theorem

Sometimes the easiest theorem to prove is stronger because the stronger statement removes accidental distinctions.

Examples:

```text
one chosen basis works
  -> every basis works

one square-root branch has the same kernel
  -> every branch differs by common invertible postcomposition

one finite census has no counterexample
  -> all instances are forced by an orbit/cardinality theorem
```

The stronger theorem is desirable when it is *more symmetric and simpler*, not merely stronger for its own sake.

### 12. Add epsilon/perturbation room when degeneracy blocks structure

If a theorem is correct away from a degenerate boundary, first prove the robust nearby statement. Separate:

```text
generic structural mechanism
+
degenerate limiting/exceptional argument.
```

Do not contaminate the main invariant with exceptional bookkeeping unless necessary.

### 13. Follow definitions when the gap is already local

Abstraction is not always the answer. If the hypothesis and conclusion differ by only one definition, expand the definitions and close the exact local gap.

The skill should *reduce representation debt*, not create abstraction for its own sake.

## Knowledge-bang score

When multiple correct proof routes exist, score each from 0 to 5 on:

- **EC — explanatory compression:** how much computation/casework becomes one mechanism?
- **AC — assumption compression:** does the proof reveal which hypotheses are actually necessary?
- **TF — theorem fanout:** how many neighboring claims become corollaries?
- **RI — representation invariance:** does the proof survive basis/coordinate/model changes?
- **CF — counterfactual clarity:** does it predict exactly how the theorem fails when assumptions are deleted?
- **FL — formalization leverage:** does it reduce the machine-checked proof to reusable lemmas?
- **TR — transferability:** can the method move to another problem/domain?
- **FD — falsification density:** does it naturally generate strong negative controls?

Subtract 0 to 5 each for:

- **CD — coordinate debt**;
- **KD — case debt**;
- **OD — opaque-dependency debt**.

A simple ranking heuristic is:

```text
knowledge_bang = EC + AC + TF + RI + CF + FL + TR + FD - CD - KD - OD
```

This score is for research prioritization only. It is not proof authority.

`LENSES.md` adds optional generative-compression, bounded-observer, downstream-debt, and mapping-debt refinements to this score.

## Research Kernel workflow

For a durable run:

1. `rk_retrieve` similar claims, prior failures, contradictions, and open frontier.
2. Add the exact claim and current bottleneck as atoms.
3. `rk_morph` through at least three structurally different representations.
4. Add promising mechanisms as `REFORMULATION` or `HYPOTHESIS` atoms, status `CANDIDATE`/`UNKNOWN`.
5. Link each mechanism to the observations it would explain.
6. `rk_refute` each high-value mechanism with deleted-premise, edge-case, and alternate-representation tests.
7. Attach executable, source-bound evidence independently of the proof sketch.
8. Formalize the mechanism in Lean/another prover where useful.
9. Map the theorem back to the production/source semantics separately.
10. Call `rk_promote` only after provenance, refutation, contradiction search, dependencies, and replay gates pass.

Never use a Morph/LEAP reformulation itself as evidence that the original claim is true. The representation edge must be checked.

## LEAP use

Use LEAP when the hidden structure can be exposed in a finite symbolic model.

Good LEAP targets:

- quotient-state discovery;
- invariant synthesis;
- finite countermodels;
- diagram completion;
- canonical language extensions;
- portal reductions whose witnesses can be lifted to the original finite domain.

The best LEAP result is not merely a solved toy. It is a **transparent language extension or quotient that explains why the toy becomes mechanical** and whose lift reveals a theorem candidate for the original domain.

## Morph use

Use Morph when several sound representation shifts compete.

A useful search tree should include moves that intentionally *change what is visible*:

```text
raw coordinates
 -> quotient by irrelevant symmetry
 -> kernel/image contract
 -> filtration
 -> dual/polarization form
 -> finite/cardinality or universal-property portal.
```

Retain proof obligations on every edge. A route is valuable when it reaches a representation in which a standard solver or short theorem applies and the result maps back cleanly.

## Preferred final artifact

For every important discovery, write a compact structure card:

```text
PHENOMENON
What repeatedly happens?

FAILED COUNTEREXAMPLE
What did we try, and what obstruction stopped it?

IRRELEVANT DATA REMOVED
What coordinates/choices were forgotten?

REPRESENTATION SHIFT
What new language makes the mechanism visible?

HIDDEN STRUCTURE
What symmetry/invariant/quotient/filtration/duality forces the result?

STRUCTURAL THEOREM
State the strongest clean theorem justified by that mechanism.

FALSIFICATION CONTROLS
Which deleted assumptions must produce counterexamples?

FORMALIZATION
What is machine-checked, and under which assumptions?

SOURCE/IMPLEMENTATION LIFT
What remains to connect the abstract theorem to actual code/data?

NONCLAIMS
What has not been established?
```

## Success criterion

The skill has succeeded when the project can replace a sentence like

```text
We checked a large number of cases and they all agree.
```

with something like

```text
All cases agree because they are representatives of one orbit / fibers of one
quotient / stages of one filtration / consequences of one duality identity;
the exhaustive computation remains as an independent falsification and
regression harness.
```

That is the desired division of labor:

```text
experiments discover and attack the pattern;
structure explains the pattern;
formal proof certifies the structure;
source refinement certifies that the implementation instantiates it.
```