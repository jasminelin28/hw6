"""campus customs vendor desk agent, built with pydantic-ai on gpt-6-luna."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from models import vendor_assessment, vendor_facts
from policy import handbook_policy
from tools import (
    _append_json,
    approve_payment,
    audit_trail_path,
    gated_approve_payment,
    gated_send_email,
    read_document,
    read_document_safe,
    send_email,
)

project_dir = Path(__file__).parent
data_dir = project_dir / "data"
output_dir = project_dir / "output"
usage_log_path = output_dir / "usage_log.json"

model_name = "gpt-6-luna"


def load_prices() -> dict:
    return json.loads((data_dir / "prices.json").read_text(encoding="utf-8"))[model_name]


def build_agent(
    include_handbook: bool = True,
    cache_buster: str | None = None,
    strip_security: bool = False,
    defended: bool = False,
) -> Agent:
    """build the vendor desk agent. the handbook rides along in the system prompt.

    defended=False is the problem 3 agent: it reads raw document text and returns the
    decision itself. defended=True adds the three layers from problem 6.
    """
    load_dotenv(project_dir / ".env")
    load_dotenv(project_dir.parent / ".env")

    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set; copy .env.example to .env")

    client = AsyncOpenAI(
        base_url="https://api.portkey.ai/v1",
        api_key=api_key,
        default_headers={"x-portkey-api-key": api_key, "x-portkey-provider": "openai"},
    )
    model = OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))

    prompt_file = "prompt.md" if defended else "prompt_undefended.md"
    instructions = (project_dir / "prompts" / prompt_file).read_text(encoding="utf-8")
    if strip_security:
        # problem 5 baseline: the same agent with the security section removed, to
        # show what the documents do to an agent that was never warned about them.
        instructions = instructions.split("## Security rules")[0].rstrip()
    if include_handbook:
        handbook = (data_dir / "shop_handbook.md").read_text(encoding="utf-8")
        instructions = (
            f"{instructions}\n\n"
            "# Campus Customs Shop Handbook (authoritative policy)\n\n"
            f"{handbook}"
        )

    if cache_buster:
        # no-cache arm of the problem 4 experiment. instructions are rebuilt on every
        # model request, so returning a fresh id at the very front of the prompt changes
        # the prefix the provider hashes on every single call, including the second call
        # inside one run, so nothing can be reused from cache.
        static_instructions = instructions

        def instructions_arg() -> str:
            return "<!-- call id " + uuid.uuid4().hex + " -->\n" + static_instructions
    else:
        instructions_arg = instructions

    agent = Agent(
        model,
        # design layer: in defended mode the model's only job is extraction. it cannot
        # return a decision, because the decision is not a field it can write.
        output_type=vendor_facts if defended else vendor_assessment,
        instructions=instructions_arg,
        model_settings=OpenAIChatModelSettings(openai_reasoning_effort="none"),
        retries=2,
    )
    agent.tool_plain(read_document_safe if defended else read_document)

    # send_email and approve_payment stay registered in both modes. in defended mode they
    # are wrapped in a human sign-off gate that refuses and logs; the underlying tools are
    # still there for the day the shop wires in a real approver.
    if defended:
        agent.tool_plain(gated_send_email)
        agent.tool_plain(gated_approve_payment)
    else:
        agent.tool_plain(send_email)
        agent.tool_plain(approve_payment)
    return agent


def compute_cost(usage, prices: dict) -> dict:
    """turn reported token counts into dollars using prices.json."""
    cached = getattr(usage, "cache_read_tokens", 0) or 0
    cache_write = getattr(usage, "cache_write_tokens", 0) or 0
    total_input = usage.input_tokens or 0
    fresh_input = max(total_input - cached - cache_write, 0)
    output_tokens = usage.output_tokens or 0

    cost = (
        fresh_input / 1e6 * prices["input_per_1m"]
        + cached / 1e6 * prices["cached_input_per_1m"]
        + cache_write / 1e6 * prices["cache_write_per_1m"]
        + output_tokens / 1e6 * prices["output_per_1m"]
    )
    return {
        "input_tokens": total_input,
        "cached_input_tokens": cached,
        "cache_write_tokens": cache_write,
        "uncached_input_tokens": fresh_input,
        "output_tokens": output_tokens,
        "total_tokens": total_input + output_tokens,
        "cost_usd": round(cost, 6),
    }


def run_agent(
    doc_path: str,
    label: str = "baseline",
    include_handbook: bool = True,
    strip_security: bool = False,
    defended: bool = False,
) -> dict:
    """run the agent on one document and log usage plus the audit trail."""
    agent = build_agent(
        include_handbook=include_handbook,
        strip_security=strip_security,
        defended=defended,
    )
    result = agent.run_sync(f"Assess the vendor document at this path: {doc_path}")

    if defended:
        # design layer: the decision is computed here, in python, from the handbook. the
        # model only supplied the facts.
        facts = result.output
        decision, reason = handbook_policy().decide(facts)
        answer = vendor_assessment(
            vendor=facts.vendor,
            sku=facts.sku,
            unit_price=facts.unit_price,
            lead_time_days=facts.lead_time_days,
            min_order=facts.min_order,
            decision=decision,
            reason=reason,
        )
    else:
        answer = result.output

    prices = load_prices()
    usage_entry = {
        "document": doc_path,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_label": label,
        "model": model_name,
        **compute_cost(result.usage, prices),
    }
    output_dir.mkdir(exist_ok=True)
    _append_json(usage_log_path, usage_entry)
    _append_json(
        audit_trail_path,
        {
            "time": usage_entry["time"],
            "kind": "final_answer",
            "document": doc_path,
            "run_label": label,
            "answer": answer.model_dump(),
        },
    )
    return {
        "answer": answer,
        "usage": usage_entry,
        "model_notes": getattr(result.output, "notes", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs vendor desk agent")
    parser.add_argument("--doc", required=True, help="path to one vendor document")
    parser.add_argument("--label", default="baseline", help="label written to the usage log")
    parser.add_argument(
        "--undefended",
        action="store_true",
        help="run the problem 3 agent with no defenses (kept for problem 7)",
    )
    parser.add_argument(
        "--no-handbook",
        action="store_true",
        help="skip the handbook in the prompt (used for cost comparisons)",
    )
    args = parser.parse_args()

    run = run_agent(
        args.doc,
        label=args.label,
        include_handbook=not args.no_handbook,
        defended=not args.undefended,
    )
    answer, usage = run["answer"], run["usage"]

    print(f"\nDocument: {args.doc}")
    print(f"  vendor         : {answer.vendor}")
    print(f"  sku            : {answer.sku}")
    print(f"  unit price     : {answer.unit_price}")
    print(f"  lead time days : {answer.lead_time_days}")
    print(f"  min order      : {answer.min_order}")
    print(f"  decision       : {answer.decision}")
    print(f"  reason         : {answer.reason}")
    print(
        f"  tokens         : {usage['input_tokens']} in "
        f"({usage['cached_input_tokens']} cached), {usage['output_tokens']} out"
    )
    print(f"  cost           : ${usage['cost_usd']:.6f}\n")


if __name__ == "__main__":
    main()
