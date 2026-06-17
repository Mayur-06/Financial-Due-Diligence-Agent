#This file includes schemas

from dotenv import load_dotenv
load_dotenv()
import os
print("🔑 KEY LOADED:", os.environ.get("GROQ_API_KEY", "NOT FOUND"))
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, TypedDict, Optional


#main.py
# class AgentState(TypedDict):
#     pdf_path: str
#     extracted_financials: Dict[str, Any]
#     calculated_metrics: Dict[str, Any]
#     investment_memo: str

class AgentState(TypedDict):
    pdf_path: str
    extracted_financials: Dict[str, Any]
    calculated_metrics: Dict[str, Any]
    investment_memo: str
    warnings: list


class FinancialMetrics(BaseModel):

    # Metadata
    company_name: Optional[str] = Field(
        default=None,
        description="Name of the company as stated in the filing"
    )
    filing_type: Optional[str] = Field(
        default=None,
        description="Type of financial filing (e.g., 8-K, 10-Q, 10-K, annual report)"
    )
    currency: Optional[str] = Field(
        default=None,
        description="Reporting currency and unit scale (e.g., 'USD in millions', 'INR in millions')"
    )
    current_period_label: Optional[str] = Field(
        default=None,
        description="Label for the most recent reporting period (e.g., 'Q2 FY2026', 'FY2024')"
    )
    prior_period_label: Optional[str] = Field(
        default=None,
        description="Label for the comparison/prior reporting period found in the document"
    )
    revenue_current_period: Optional[float] = Field(
        default=None,
        description="Total revenue or net sales for the most recent reporting period"
    )
    revenue_prior_period: Optional[float] = Field(
        default=None,
        description="Total revenue or net sales for the prior/comparison reporting period"
    )
    net_income_current_period: Optional[float] = Field(
        default=None,
        description="Net income or net profit/loss for the most recent reporting period"
    )
    net_income_prior_period: Optional[float] = Field(
        default=None,
        description="Net income or net profit/loss for the prior/comparison reporting period"
    )
    gross_margin_current_period: Optional[float] = Field(
        default=None,
        description="Gross profit as a raw dollar/rupee amount for the most recent period"
    )
    diluted_eps_current_period: Optional[float] = Field(
        default=None,
        description="Diluted earnings per share for the most recent reporting period"
    )
    diluted_eps_prior_period: Optional[float] = Field(
        default=None,
        description="Diluted earnings per share for the prior reporting period"
    )
    operating_income_current_period: Optional[float] = Field(
        default=None,
        description="Operating income or EBIT for the most recent reporting period"
    )
    operating_cash_flow: Optional[float] = Field(
        default=None,
        description="Net cash generated from operating activities for the most recent period"
    )
    total_assets: Optional[float] = Field(
        default=None,
        description="Total assets as of the most recent balance sheet date"
    )
    total_debt: Optional[float] = Field(
    default=None,
    description="""Total financial debt only — sum of short-term borrowings 
    and long-term debt/notes payable. Do NOT include trade payables, 
    deferred revenue, lease liabilities, or other non-debt liabilities. 
    Look for line items labeled 'Term debt', 'Notes payable', 
    'Commercial paper', or 'Long-term debt'."""
    )




#api.py
# class AnalysisResponse(BaseModel):
#     company_name: str
#     filing_type: str
#     extracted_financials: dict
#     calculated_metrics: dict
#     investment_memo: str

class AnalysisResponse(BaseModel):
    company_name: str
    filing_type: str
    extracted_financials: dict
    calculated_metrics: dict
    investment_memo: str
    model_version: str
    processing_time_seconds: float
    warnings: list[str]