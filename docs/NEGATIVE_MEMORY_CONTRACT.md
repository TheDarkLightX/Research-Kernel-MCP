# Typed negative memory and maximally informative failures

This contract is an **additive research feature**, not an independent mathematical proof
engine. The Python stdio kernel and the hosted companion have distinct trust boundaries.
This document describes the hosted companion's authoritative behavior.

## Two kinds of negative memory

| Class | Origin | Authority | Sound automatic exclusion |
| --- | --- | --- | --- |
| **Hard** | A stored `integer-grid/v1` receipt with `outcome=counterexample` and the exact source/revision/transcript pins | `bounded-check-only` | **Only the exact checked equation/recipe at that revision and on the specified finite grid**, assuming the pinned checker is trusted |
| **Soft** | A structured `rk_negative_record` or legacy user-supplied negative evidence | `unverified` | **None**; may request review or guide the next experiment |

A manually typed proof, a claimed impossibility, an LLM inference, a source quotation,
and a witness **not yet replayed by the checker** are all soft. This also applies
to evidence carrying an artifact hash. Hashes establish byte identity, not truth.

Hard negativity is derivable from a receipt
`r=(revision, recipe, checker, transcript, witness, environment)`:

```text
r.outcome = counterexample
=> exists x in the checked grid: eval(left,x) != eval(right,x)
```

This cannot be promoted to a theorem about an unbounded domain, to a
candidate family, or to another encoding or revision without a **separate proof**.

The original revision and scope remain in the evidence history. A corrected
revision can pass while its historical hard/soft negatives remain queryable.

## What makes a failed attempt maximally informative?

The goal is to extract as much **sound, reusable information** from failure as
possible, *not* to maximize the number of candidates speculatively rejected.

Every proposed negative lesson should answer:

1. **What was tried?** Exact candidate, language/representation and selection criterion.
2. **Under which assumptions/domain?** Record the original version and scope.
3. **What failed, exactly?** Root cause or an honest unresolved hypothesis.
4. **What was observed?** Reproducible input/output witness, trace, or reason to doubt the attempt.
5. **What follows deductively?** Explicitly separate checked exclusion from unproved extrapolation.
6. **Could it generalize?** Specify the candidate family and *new proof obligation* (e.g. SMT unsat core, interpolation, quantified lemma, verified reduction).
7. **When should it be reopened?** Changed assumptions, improved representations, new solvers, stronger oracles.
8. **How would the next test increase knowledge?** Witness minimization, stronger lemma, counterexample search, or a representation shift.

In particular, a single failing program `p` at input `x` never entails
`forall q in C: q fails`. A family-level exclusion requires a checked proof
that each `q in C` fails **within the same declared scope**, with its own
evidence and dependency lineage.

The hosted `rk_negative_memory` tool now returns `insights` sorted by a
deterministic **information-completeness triage rank** (checked receipt first,
then documented fields). It also returns `missing` fields and a
`nextBestAction`. The rank is *not* proof strength, measured Shannon
information, scientific truth, or a guarantee of an optimal lesson.

## Example: missing cross term

For a checked finite-grid equation

```
(x+y)^2 == x^2+y^2
```

the checker finds a mismatching pair such as `x=-5, y=-5`. It supports a
hard exclusion of that exact checked recipe on the finite grid. It does **not**
establish that every additive-only model is impossible.

Separately, the researcher can record a soft hypothesis that "the language is
missing an interaction feature", propose the alternative representation `x*y`,
and specify the trigger "revisit after adding product terms". The same
observation becomes actionable **without** impersonating a proof.

## API

`rk_negative_record` is a version-checked, append-only mutation bound to a
claim's **current** revision hash. It takes a `record` object:

```json
{
  "attempt": "Try eliminating the cross term",
  "failureReason": "The expression disagrees on mixed-sign inputs",
  "scope": "Two-variable additive-only feature language",
  "assumptions": "Integer inputs; no products",
  "observedCounterexample": "A reported input pair (unverified)",
  "candidateGeneralization": "All additive-only encodings may fail (unproved)",
  "alternativeRepresentation": "Introduce x*y",
  "revisitWhen": ["When the feature language permits products"]
}
```

It also requires the standard `workspaceId`, `expectedRevision`,
`requestId`, `claimId`, `expectedHash`, `uri` (possibly empty), and
`artifactHash` (possibly null). The server **always** records this as
`classification=soft`, `authority=unverified`; it cannot accept a
caller-declared hard classification.

`rk_negative_memory(workspaceId, query?, classification?)` returns previous
`claims`, `counterexamples`, `negativeEvidence` fields for compatibility,
plus `insights` containing exact historical scope, both soft/hard classes,
evidence provenance, safe exclusion boundary, information gaps, potential
representation shifts and revisitation conditions.
`classification` is `all` (default), `hard`, or `soft`.

Legacy negative evidence with only a summary remains searchable as **soft**.
Unverified negative records request transitive dependent review, as before,
but never change a source claim's bounded-check status or synthesize a proof.
The snapshot and event journal preserve the original append-only evidence.

## Limitations and next research steps

- The integer-grid checker reports a **deterministic first mismatch**, not a
  minimum-size witness; minimization is a separate task.
- No automatic SMT/Lean certificate for class-wide impossibility exists in
  this pilot. Such an extension must verify proofs before widening pruning.
- No automatic proof that a negative result transfers through an abstraction,
  encoding, or representation shift is provided.
- No correctness guarantee is attached to the triage rank or a suggested
  scientific next step.
- The functional-core source pin includes the negative-memory evaluator.
  Previously stored journals require their exact original source version for
  replay; the new pin does not retroactively verify older journals.

See the hosted regression tests for old revision retention, strict soft
admission, lack of authority escalation, and bounded checker provenance.
