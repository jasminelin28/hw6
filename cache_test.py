"""problem 4: measure what caching the handbook is worth.

runs all 12 practice documents twice, once with the handbook prefix held identical so the
provider can reuse it from cache, and once with a unique string at the front of every
prompt so nothing can be reused. records every individual model call.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.messages import ModelResponse

from agent import build_agent, compute_cost, load_prices, model_name

project_dir = Path(__file__).parent
practice_dir = project_dir / "data" / "practice_docs"
cache_test_path = project_dir / "output" / "cache_test.json"


def run_one(doc_path: Path, setup: str, prices: dict) -> list[dict]:
    """run the agent on one document, return one record per model call."""
    cache_buster = uuid.uuid4().hex if setup == "no_cache" else None
    agent = build_agent(include_handbook=True, cache_buster=cache_buster)
    result = agent.run_sync(f"Assess the vendor document at this path: {doc_path.as_posix()}")

    records = []
    call_index = 0
    for message in result.all_messages():
        if not isinstance(message, ModelResponse) or message.usage is None:
            continue
        call_index += 1
        records.append(
            {
                "setup": setup,
                "document": doc_path.name,
                "model": model_name,
                "model_call": call_index,
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "decision": result.output.decision,
                **compute_cost(message.usage, prices),
            }
        )
    return records


def main() -> None:
    prices = load_prices()
    docs = sorted(practice_dir.iterdir())
    all_records: list[dict] = []

    # the no-cache arm runs first so it cannot benefit from a cache the other arm warmed.
    for setup in ("no_cache", "with_cache"):
        print(f"\n=== setup: {setup} ===")
        if setup == "with_cache":
            # one warm-up call writes the handbook prefix into cache so every measured
            # document in this arm reads it back rather than paying to write it.
            print("warming the cache ...")
            run_one(docs[0], setup, prices)
        for doc in docs:
            records = run_one(doc, setup, prices)
            all_records.extend(records)
            cached = sum(r["cached_input_tokens"] for r in records)
            cost = sum(r["cost_usd"] for r in records)
            print(f"  {doc.name:32s} calls={len(records)} cached={cached:6d} ${cost:.6f}")

    cache_test_path.write_text(json.dumps(all_records, indent=2), encoding="utf-8")

    print("\n=== totals ===")
    for setup in ("no_cache", "with_cache"):
        rows = [r for r in all_records if r["setup"] == setup]
        total = sum(r["cost_usd"] for r in rows)
        cached = sum(r["cached_input_tokens"] for r in rows)
        print(
            f"{setup:11s} calls={len(rows):3d} cached_tokens={cached:7d} "
            f"total=${total:.6f} per_doc=${total / 12:.6f}"
        )


if __name__ == "__main__":
    main()
