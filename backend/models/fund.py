"""Pydantic models for fund CRUD operations."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class FundCreate(BaseModel):
    """Body when creating a new fund tracker (sent as form fields + file)."""
    name:         str   = Field(..., description="e.g. 'HDFC Flexi Cap Fund'")
    official_nav: float = Field(..., gt=0, description="Previous official NAV in Rs.")
    nav_date:     str   = Field(..., description="YYYY-MM-DD")

    @field_validator("nav_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v.strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"nav_date must be YYYY-MM-DD, got '{v}'")
        return v.strip()

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class FundUpdate(BaseModel):
    """Body when updating fund metadata (PATCH)."""
    name:         Optional[str]   = None
    official_nav: Optional[float] = Field(default=None, gt=0)
    nav_date:     Optional[str]   = None

    @field_validator("nav_date")
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v.strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"nav_date must be YYYY-MM-DD")
        return v.strip()


class FundSummary(BaseModel):
    """A fund row as returned in list / detail responses."""
    id:             int
    name:           str
    official_nav:   float
    nav_date:       str
    portfolio_date: str
    total_holdings: int
    created_at:     str
    updated_at:     str
