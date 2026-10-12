"""design layer: the purchasing decision, computed in python from the handbook.

the model extracts facts. it does not decide. the four checks in handbook section 4 run
here, over the vendor lists and catalogue parsed straight out of shop_handbook.md, so no
sentence in a vendor document can reach the decision no matter what it says.
"""

from __future__ import annotations

import re
from pathlib import Path

handbook_path = Path(__file__).parent / "data" / "shop_handbook.md"

max_lead_time_days = 21
max_min_order_units = 600


def _rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def _section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}.*?(?=^## |\Z)", re.M | re.S)
    match = pattern.search(text)
    return match.group(0) if match else ""


class handbook_policy:
    """the purchasing rules, loaded once from the handbook."""

    def __init__(self, text: str | None = None):
        text = text or handbook_path.read_text(encoding="utf-8")

        approved = _rows(_section(text, "5. Approved vendors"))[1:]
        self.approved_vendors = {row[1].lower(): row[1] for row in approved if len(row) > 1}

        removed = _rows(_section(text, "6. Removed and pending vendors"))[1:]
        self.blocked_vendors = {row[0].lower(): row[1] for row in removed if len(row) > 1}

        catalogue = _rows(_section(text, "9. Product catalogue"))[1:]
        self.max_unit_cost = {}
        self.item_name = {}
        for row in catalogue:
            if len(row) < 5 or not row[0].startswith("CC-"):
                continue
            self.max_unit_cost[row[0].upper()] = float(row[4].replace("$", "").replace(",", ""))
            self.item_name[row[0].upper()] = row[1]

    def _match_vendor(self, vendor: str | None) -> tuple[str, str | None]:
        """classify a vendor name as approved, blocked, or unknown."""
        if not vendor:
            return "unknown", None
        name = vendor.strip().lower()
        if name in self.blocked_vendors:
            return "blocked", self.blocked_vendors[name]
        if name in self.approved_vendors:
            return "approved", None
        # a document may spell the vendor loosely. substring matching in both directions
        # catches "Blue Hen Apparel Inc." without letting a removed vendor slip through
        # under a longer name.
        for blocked, status in self.blocked_vendors.items():
            if blocked in name or name in blocked:
                return "blocked", status
        for approved in self.approved_vendors:
            if approved in name or name in approved:
                return "approved", None
        return "unknown", None

    def decide(self, facts) -> tuple[str, str]:
        """run the four checks in handbook order. returns (decision, reason)."""
        status, note = self._match_vendor(facts.vendor)
        if status == "blocked":
            return (
                "do_not_recommend",
                f"Approved-vendor check failed: {facts.vendor} is on the removed or pending "
                f"list ({note}).",
            )
        if status == "unknown":
            return (
                "do_not_recommend",
                f"Approved-vendor check failed: {facts.vendor or 'the vendor'} is not on the "
                "approved vendor list.",
            )

        sku = (facts.sku or "").upper()
        if not sku or sku not in self.max_unit_cost:
            return (
                "do_not_recommend",
                f"Price check failed: {facts.sku or 'no SKU'} is not in the Campus Customs "
                "catalogue, so there is no max unit cost to compare against.",
            )

        cap = self.max_unit_cost[sku]
        if facts.unit_price is None:
            return (
                "do_not_recommend",
                "Price check failed: the document does not state a unit price.",
            )
        if facts.unit_price > cap:
            return (
                "do_not_recommend",
                f"Price check failed: ${facts.unit_price:.2f} is above the ${cap:.2f} max unit "
                f"cost for {sku}.",
            )

        if facts.lead_time_days is None:
            return (
                "do_not_recommend",
                "Lead-time check failed: the document does not state a lead time.",
            )
        if facts.lead_time_days > max_lead_time_days:
            return (
                "do_not_recommend",
                f"Lead-time check failed: {facts.lead_time_days} days is over the "
                f"{max_lead_time_days}-day limit.",
            )

        if facts.min_order is None:
            return (
                "do_not_recommend",
                "Minimum-order check failed: the document does not state a minimum order.",
            )
        if facts.min_order > max_min_order_units:
            return (
                "do_not_recommend",
                f"Minimum-order check failed: {facts.min_order} units is over the "
                f"{max_min_order_units}-unit limit.",
            )

        return (
            "recommend",
            f"All four checks pass: approved vendor, ${facts.unit_price:.2f} at or under the "
            f"${cap:.2f} max unit cost, {facts.lead_time_days}-day lead time, and a "
            f"{facts.min_order}-unit minimum.",
        )
