"""problem 8: run the final defended agent on the 10 exam documents.

no hand-editing. whatever the agent returns is what gets written.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent import run_agent
from tools import trap_calls_path

project_dir = Path(__file__).parent
exam_dir = project_dir / "data" / "exam_docs"
results_path = project_dir / "output" / "exam_results.json"


def load_traps() -> list[dict]:
    if not trap_calls_path.exists():
        return []
    return json.loads(trap_calls_path.read_text(encoding="utf-8"))


def main() -> None:
    results = []

    for doc in sorted(exam_dir.iterdir()):
        traps_before = len(load_traps())
        run = run_agent(doc.as_posix(), label="exam", defended=True)
        answer = run["answer"]
        usage = run["usage"]
        trap_called = len(load_traps()) > traps_before

        results.append(
            {
                "file": doc.name,
                "vendor": answer.vendor,
                "sku": answer.sku,
                "unit_price": answer.unit_price,
                "lead_time_days": answer.lead_time_days,
                "min_order": answer.min_order,
                "decision": answer.decision,
                "reason": answer.reason,
                "trap_tool_called": trap_called,
                "input_tokens": usage["input_tokens"],
                "cached_tokens": usage["cached_input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cost_usd": usage["cost_usd"],
            }
        )

        print(
            f"{doc.name:20s} {answer.vendor:28s} {str(answer.sku):12s} "
            f"${answer.unit_price} {answer.lead_time_days}d "
            f"min={answer.min_order} {answer.decision}"
        )

    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    total = sum(r["cost_usd"] for r in results)
    print(f"\n{len(results)} documents")
    print(f"recommend        : {sum(r['decision'] == 'recommend' for r in results)}")
    print(f"do_not_recommend : {sum(r['decision'] == 'do_not_recommend' for r in results)}")
    print(f"trap tools fired : {sum(r['trap_tool_called'] for r in results)}")
    print(f"total cost       : ${total:.6f}")


if __name__ == "__main__":
    main()
