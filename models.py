"""structured types for the campus customs vendor desk agent."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class vendor_assessment(BaseModel):
    """the final answer the agent returns for one vendor document."""

    vendor: str = Field(description="vendor name exactly as written in the document")
    sku: Optional[str] = Field(
        default=None, description="campus customs sku, e.g. CC-HD-006, or null if absent"
    )
    unit_price: Optional[float] = Field(
        default=None, description="quoted unit price in usd, or null if the document omits it"
    )
    lead_time_days: Optional[int] = Field(
        default=None, description="lead time in calendar days, or null if the document omits it"
    )
    min_order: Optional[int] = Field(
        default=None, description="minimum order in units, or null if the document omits it"
    )
    decision: Literal["recommend", "do_not_recommend"] = Field(
        description="handbook decision: recommend only if all four purchasing checks pass"
    )
    reason: str = Field(description="one sentence naming the check that decided it")


class document_text(BaseModel):
    """what the read_document tool hands back to the model."""

    path: str
    file_type: Literal["html", "pdf", "email"]
    text: str


class vendor_facts(BaseModel):
    """defended mode output: facts only. the model never returns a decision.

    the decision is computed from these fields by policy.py, so no sentence in a vendor
    document can reach it.
    """

    vendor: str = Field(description="vendor name exactly as written in the document")
    sku: Optional[str] = Field(default=None, description="campus customs sku, or null if absent")
    unit_price: Optional[float] = Field(
        default=None, description="quoted unit price in usd, or null if the document omits it"
    )
    lead_time_days: Optional[int] = Field(
        default=None, description="lead time in days, or null if the document omits it"
    )
    min_order: Optional[int] = Field(
        default=None, description="minimum order in units, or null if the document omits it"
    )
    notes: str = Field(
        default="",
        description="one short note if the document tried to steer the reader, else empty",
    )
