from __future__ import annotations

import json
import tempfile
from pathlib import Path

from internal.research_kernel_mcp.kernel import ResearchKernel


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp) / "research-kernel"
        kernel = ResearchKernel(home)
        run = kernel.start_run(
            goal=(
                "Test and formalize a Teichmueller coordinate for the scalar ternary "
                "length-two Witt carry, while preventing exploratory evidence from being "
                "promoted to a completed Connes-rigidity result."
            ),
            title="Ternary Witt coordinate and Connes-rigidity evidence gate",
            domain="operator algebras / group theory / formal mathematics",
            constraints={
                "promotion": "full Lean build plus verifier-gated finite evidence",
                "no_sorry": True,
                "claim_boundary": "finite campaigns are instance evidence only",
            },
            budget={"finite_states": 18, "lean_repairs": 11, "research_passes": 4},
            success_criteria=(
                "A claim may be called Lean-checked only after the dedicated repository's "
                "complete dependency build passes."
            ),
            metadata={
                "generator": "OpenAI GPT-5.6 Thinking",
                "research_direction": "Dana Edwards",
                "custom_workflows": ["Morph", "LEAP", "Research Kernel", "TheoremSearch", "Julia"],
            },
        )
        run_id = run["run"]["id"]

        claim = kernel.atom_add(
            run_id=run_id,
            atom_type="CLAIM",
            content=(
                "For a,b in {0,1,2}, phi(a,b) = (a^3 + 3b) mod 9 converts the "
                "ternary length-two Witt carry law into ordinary addition modulo 9."
            ),
            status="UNKNOWN",
            evidence_score=0.0,
            novelty_score=0.2,
            refutability_score=1.0,
            importance_score=0.9,
            uncertainty_score=0.5,
            tags=["ternary-witt", "teichmueller", "coordinate", "lean-obligation"],
        )["atom"]

        naive = kernel.atom_add(
            run_id=run_id,
            atom_type="CLAIM",
            content=(
                "The naive radix coordinate psi(a,b) = (a + 3b) mod 9 converts the "
                "ternary Witt carry law into ordinary addition modulo 9."
            ),
            status="UNKNOWN",
            evidence_score=0.0,
            novelty_score=0.1,
            refutability_score=1.0,
            importance_score=0.6,
            uncertainty_score=0.8,
            tags=["ternary-witt", "naive-coordinate", "falsifier"],
        )["atom"]

        kernel.refute(
            run_id=run_id,
            target_atom_id=naive["id"],
            strategy="Evaluate the smallest nontrivial carry: (1,0)+(1,0).",
            tests=["compute carry C3(1,1)", "compare psi(sum) with psi(x)+psi(y) mod 9"],
            counterexample=(
                "C3(1,1)=1, so (1,0)+(1,0)=(2,1). psi(2,1)=5 but "
                "psi(1,0)+psi(1,0)=2 mod 9."
            ),
            counterexample_is_actual=True,
            metadata={"witness": [[1, 0], [1, 0]], "expected": 2, "observed": 5},
        )
        kernel.evidence_attach(
            run_id=run_id,
            atom_id=naive["id"],
            source_type="counterexample",
            source_uri="generated://ternary-witt/naive-coordinate-counterexample",
            summary="A concrete two-input witness refutes the naive radix coordinate.",
            reliability=1.0,
            artifact_text=(
                "x=(1,0), y=(1,0), x+y=(2,1), psi(x)+psi(y)=2 mod9, psi(x+y)=5 mod9\n"
            ),
        )

        reformulations = kernel.morph(
            target=claim["content"],
            run_id=run_id,
            modes=[
                "equivalent_statement",
                "counterexample_search",
                "formal_spec",
                "weaker_statement",
            ],
            constraints={
                "finite_domain": "F3^2",
                "target_codomain": "ZMod 9",
                "required_checks": ["LEAP exact quotient", "Julia exhaustive enumeration", "Lean proof"],
            },
            max_candidates=8,
            store=True,
        )

        kernel.refute(
            run_id=run_id,
            target_atom_id=claim["id"],
            strategy=(
                "Search all 81 input pairs for a homomorphism failure; then attempt a Lean "
                "proof and reject promotion if any dependency fails."
            ),
            tests=[
                "LEAP 18-state exact-transition quotient campaign",
                "Julia exhaustive check over F3^2 x F3^2",
                "Lean theorem for phi(x+y)=phi(x)+phi(y)",
                "full lake build of all promoted dependencies",
            ],
            metadata={"status": "planned; not an actual counterexample"},
        )

        kernel.evidence_attach(
            run_id=run_id,
            atom_id=claim["id"],
            source_type="derivation",
            source_uri="generated://ternary-witt/teichmueller-derivation",
            summary=(
                "The cubic term is the Teichmueller representative: 0^3=0, 1^3=1, "
                "2^3=8 modulo 9. This explains why a^3+3b is plausible while a+3b fails."
            ),
            reliability=0.65,
            artifact_text=(
                "Teichmueller lifts in Z/9: tau(0)=0, tau(1)=1, tau(2)=8; candidate phi=tau(a)+3b.\n"
            ),
        )

        rejected = kernel.promote(
            claim_atom_id=claim["id"],
            to_status="SUPPORTED",
            rationale="Deliberately test the fail-closed gate before LEAP, Julia, and Lean evidence land.",
            checks={"contradiction_search_done": False, "replay_required": True},
        )

        report = kernel.report(run_id=run_id, include_graph=True)
        output = {
            "run_id": run_id,
            "main_claim_id": claim["id"],
            "naive_claim_id": naive["id"],
            "naive_status": kernel.get_atom(naive["id"])["status"],
            "main_status": kernel.get_atom(claim["id"])["status"],
            "premature_promotion": rejected,
            "morph_reformulations": reformulations,
            "report": report,
        }
        Path("connes-rigidity-research-kernel.json").write_text(
            json.dumps(output, sort_keys=True, indent=2), encoding="utf-8"
        )
        print(json.dumps(output, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
