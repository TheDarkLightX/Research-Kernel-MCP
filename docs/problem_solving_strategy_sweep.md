# Deterministic problem-solving strategy sweep

`tools/research_strategy_sweep.py` turns a collection of general mathematical problem-solving heuristics into explicit, auditable Research Kernel reformulation candidates.

The strategy vocabulary is inspired in part by Terence Tao's expository post:

> Terence Tao, *245A: Problem solving strategies* (2010).

Source:

```text
https://terrytao.wordpress.com/2010/10/21/245a-problem-solving-strategies/
```

The templates are adapted for an evidence-first research workflow; they are not quotations from the post.

## Authority boundary

Every output is marked:

```text
schema = research_kernel/strategy_sweep/v1
epistemic_role = strategy_only
does_not_support_claims = true
```

A strategy suggestion is **not evidence** that a proposition is true, novel, important, or even useful.

The intended pipeline is:

```text
problem / claim
    |
strategy sweep
    |
REFORMULATION / QUESTION / RISK candidates
    |
small exact model + prior-failure retrieval
    |
refutation attempt
    |
primary evidence / proof / experiment
    |
rk_promote
```

Strategy output must never satisfy the support-evidence portion of the Research Kernel promotion gate.

## Usage

Default bounded sweep:

```bash
python tools/research_strategy_sweep.py \
  'Recover a hidden prime-degree kernel line from a compact isogeny evaluator.'
```

Select particular modes:

```bash
python tools/research_strategy_sweep.py \
  'Recover a hidden prime-degree kernel line from a compact isogeny evaluator.' \
  --mode simpler_case \
  --mode abstract_irrelevant \
  --mode exploit_symmetry \
  --mode interchange_operations
```

List all modes:

```bash
python tools/research_strategy_sweep.py x --list-modes
```

## Strategy modes

### `split_goal`

Split an equality/equivalence or composite conclusion into separately falsifiable obligations.

### `approximate_first`

Allow explicit epsilon/bounded-error slack, then identify the missing limiting or amplification step.

### `simpler_case`

Remove distracting generality while preserving the suspected hard mechanism.

### `localize`

Replace a global problem by the sharpest local, prime-power, neighborhood, or component problem that can later be patched.

### `exceptional_set`

Separate generic and exceptional strata rather than forcing one theorem to treat both identically.

### `counterexample_picture`

Build the smallest exact model in which the conclusion could fail while preserving the hypotheses.

### `abstract_irrelevant`

Forget suspected irrelevant domain structure and test the abstract information-theoretic core.

### `expand_definitions`

Expand hypotheses/conclusions into primitive definitions and compare them directly.

### `exploit_symmetry`

Identify the exact symmetry group, normalize representatives, and quotient redundancy before searching.

### `linearize`

Perturb around a structured point and extract first-/second-order necessary conditions.

### `interchange_operations`

Exchange the order of sums, traces, expectations, searches, products, or quantifiers to expose a compressed invariant.

### `average_vs_pointwise`

Move between pointwise, moment, trace, average, and exceptional-set formulations when justified.

### `generators_and_closure`

Prove a property on a small generating family and show it is preserved under the relevant closure operation.

### `parameter_later`

Keep parameters symbolic until all inequalities and dependencies are visible, then optimize once.

## Example: prime-degree Isogeny Problem 6

Starting target:

```text
Recover ker(phi) for a sufficiently explicit large-prime-degree isogeny
phi:E->E' when End(E) is known.
```

A useful strategy sweep produces the following research transformations.

### Simpler case

Restrict first to

```text
ell+1 = 2^k
```

(Mersenne prime degree when `ell` is prime). This removes factorization and duplicate-exponent distractions while retaining the large hidden projective-line problem.

### Abstract away irrelevant structure

Restrict the Borel-HSP push-forward oracle to a nonsplit projective torus. The hidden kernel becomes one cyclic hidden shift

```text
F_phi(e) = F_0(e+x),   e,x in C_(ell+1).
```

This abstract model has an exact opaque-label baseline of `Theta(sqrt(ell))` queries.

### Exploit symmetry

The nonsplit torus acts simply transitively on `P^1(F_ell)`, replacing `ell+1` unrelated kernel candidates by one exponent `x`.

### Interchange operations

For field-valued labels `J(e)=j(F(e))`, Fourier-transform the torus orbit:

```text
Jhat_phi(r) = zeta^(r*x) Jhat_0(r).
```

This turns hidden translation into a multiplicative phase and creates the positive target:

```text
compute one informative toric period/Fourier coefficient without enumerating
all ell+1 curve labels.
```

### Counterexample discipline

The same workflow rejected two superficially attractive constructions:

```text
1. products of invertible torus elements cannot lie in the hidden annihilator
   ideal; a rank-one singular seed is required;

2. literal powers of one global lift have exponentially growing norm bitlength;
   independent small lifts are required for a complexity-preserving family.
```

The point of the strategy sweep is exactly this: generate transformations, then **try to kill them quickly**.

## Relationship to `rk_morph`

`rk_morph` remains the deterministic kernel-side reformulation primitive. This companion sweep is deliberately client-side while the strategy vocabulary is being evaluated.

If the modes prove broadly useful and stable, a later change may add selected modes directly to the `rk_morph` template dictionary. Until then, keeping them outside the kernel makes the authority boundary and experimentation status explicit.

## Nonclaims

- The strategy list is not claimed to be complete or optimal.
- Tao's heuristics are expository problem-solving advice, not a formal inference system.
- A reformulation can lose decisive structure; semantic preservation must be tested.
- A successful special case does not prove a general theorem.
- Strategy receipts are reproducibility metadata, not mathematical evidence.
