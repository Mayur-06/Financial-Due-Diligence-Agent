import os
from typing import Dict, Any, TypedDict, Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv
import pdfplumber

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import PydanticOutputParser

# ==========================================
# 🔑 1. CONFIGURATION & ENVIRONMENT SETUP
# ==========================================

load_dotenv()

# ==========================================
# 📦 2. STATE & SCHEMA DEFINITIONS
# ==========================================

class AgentState(TypedDict):
    pdf_path: str
    extracted_financials: Dict[str, Any]
    calculated_metrics: Dict[str, Any]
    investment_memo: str


class FinancialMetrics(BaseModel):

    # Metadata
    company_name: str = Field(
        description="Name of the company as stated in the filing"
    )
    filing_type: str = Field(
        description="Type of financial filing (e.g., 8-K, 10-Q, 10-K, annual report)"
    )
    currency: str = Field(
        description="Reporting currency and unit scale (e.g., 'USD in millions', 'EUR in billions')"
    )

    # Period Labels
    current_period_label: str = Field(
        description="Label for the most recent reporting period (e.g., 'Q2 FY2026', 'FY2024', 'H1 2025')"
    )
    prior_period_label: str = Field(
        description="Label for the comparison/prior reporting period found in the document"
    )

    # Revenue
    revenue_current_period: float = Field(
        description="Total revenue or net sales for the most recent reporting period, in reported currency units"
    )
    revenue_prior_period: float = Field(
        description="Total revenue or net sales for the prior/comparison reporting period, in reported currency units"
    )

    # Net Income
    net_income_current_period: float = Field(
        description="Net income or net profit for the most recent reporting period, in reported currency units"
    )
    net_income_prior_period: float = Field(
        description="Net income or net profit for the prior/comparison reporting period, in reported currency units"
    )

    # Gross Margin
    gross_margin_current_period: Optional[float] = Field(
        default=None,
        description="Gross profit margin percentage for the most recent reporting period, if available"
    )

    # EPS
    diluted_eps_current_period: Optional[float] = Field(
        default=None,
        description="Diluted earnings per share for the most recent reporting period, if disclosed"
    )
    diluted_eps_prior_period: Optional[float] = Field(
        default=None,
        description="Diluted earnings per share for the prior/comparison reporting period, if disclosed"
    )

    # Operating Income
    operating_income_current_period: Optional[float] = Field(
        default=None,
        description="Operating income or EBIT for the most recent reporting period, if disclosed"
    )

    # Cash Flow
    operating_cash_flow: Optional[float] = Field(
        default=None,
        description="Net cash generated from operating activities for the most recent reporting period, if disclosed"
    )

    # Balance Sheet
    total_assets: Optional[float] = Field(
        default=None,
        description="Total assets as of the most recent balance sheet date, if disclosed"
    )
    total_debt: Optional[float] = Field(
        default=None,
        description="Total short-term and long-term debt combined as of the most recent balance sheet date, if disclosed"
    )


# ==========================================
# 🤖 LLM FACTORY
# ==========================================

def get_llm(temp=0.0):
    return ChatOpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        temperature=temp,
    )


# ==========================================
# 📄 PDF TEXT EXTRACTOR
# ==========================================

# REPLACE THIS ENTIRE FUNCTION with the new version below

def extract_pdf_text(pdf_path: str, max_chars: int = 25000) -> str:

    FINANCIAL_KEYWORDS = [
        "balance sheet",
        "statements of operations",
        "income statement",
        "cash flows",
        "net sales",
        "total revenue",
        "net income",
        "earnings per share",
        "total assets",
        "total liabilities",
        "shareholders equity",
    ]

    cover_text = ""
    financial_pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            tables = page.extract_tables()

            page_chunks = [text]
            for table in tables:
                for row in table:
                    if row:
                        row_text = " | ".join(
                            str(cell).strip()
                            for cell in row
                            if cell is not None
                        )
                        if row_text.strip():
                            page_chunks.append(row_text)

            page_text = "\n".join(page_chunks)

            # Always keep first 2 pages (cover + filing info)
            if i < 2:
                cover_text += page_text + "\n"
                continue

            # Keep financial pages only
            page_lower = page_text.lower()
            is_financial_page = any(
                keyword in page_lower
                for keyword in FINANCIAL_KEYWORDS
            )

            if is_financial_page:
                financial_pages_text.append(page_text)

    # Combine cover + financial pages
    if financial_pages_text:
        full_text = cover_text + "\n".join(financial_pages_text)
        print(f"📊 Found {len(financial_pages_text)} financial page(s) + cover")
    else:
        # Fallback: if no financial pages detected, use cover only
        # and warn the user
        full_text = cover_text
        print("⚠️  No financial pages detected, using cover pages only")

    if len(full_text) > max_chars:
        print(f"⚠️  Text truncated to {max_chars} chars (original: {len(full_text)})")
        full_text = full_text[:max_chars]

    return full_text


# ==========================================
# 🔄 NODE 1: FINANCIAL DATA EXTRACTION
# ==========================================

def extraction_node(state: AgentState):

    print("\n╭────────────────────────────────────╮")
    print("│ NODE 1: FINANCIAL EXTRACTION       │")
    print("╰────────────────────────────────────╯")

    full_text = extract_pdf_text(state["pdf_path"])
    llm = get_llm(temp=0.0)
    parser = PydanticOutputParser(pydantic_object=FinancialMetrics)

    prompt = f"""
You are a financial analyst. Extract ONLY values explicitly stated in the SEC filing below.

STRICT RULES:
- Return ONLY a valid JSON object. No explanations, no commentary, no markdown.
- Do not perform any calculations — extract raw numbers only.
- Extract numbers exactly as they appear (e.g. 111,184 → 111184.0, not 111.184)
- If a value is not present, use null
- Your entire response must start with {{ and end with }}

{parser.get_format_instructions()}

TEXT:
{full_text}
"""

    response = llm.invoke(prompt)

    # Clean the response before parsing
    raw = response.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # Extract just the JSON object if there's surrounding text
    import re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        raw = json_match.group()

    result = parser.parse(raw).model_dump()

    print("✅ Extraction Successful")
    print(result)

    return {"extracted_financials": result}


# ==========================================
# 🔄 NODE 2: VALIDATION
# ==========================================

def validation_node(state: AgentState):

    print("\n╭────────────────────────────────────╮")
    print("│ NODE 2: VALIDATION                 │")
    print("╰────────────────────────────────────╯")

    data = state["extracted_financials"]

    # Check required fields exist and are non-zero
    required_fields = [
        "revenue_current_period",
        "revenue_prior_period",
        "net_income_current_period",
        "net_income_prior_period",
    ]

    missing = [
        f for f in required_fields
        if not data.get(f)
    ]

    if missing:
        raise ValueError(
            f"❌ Extraction failed. Missing or zero fields: {missing}"
        )

    # Sanity check: revenue must be positive
    if data["revenue_current_period"] <= 0:
        raise ValueError(
            "❌ Extracted revenue is zero or negative — likely a parsing error"
        )

    # Sanity check: current period revenue should generally be >= prior
    # (just a warning, not a hard stop)
    if data["revenue_current_period"] < data["revenue_prior_period"] * 0.5:
        print(
            "⚠️  Warning: Current period revenue is less than 50% of prior period — verify extraction"
        )

    print(f"✅ Validation Passed for {data['company_name']}")
    print(f"   Period: {data['current_period_label']} vs {data['prior_period_label']}")
    print(f"   Currency: {data['currency']}")

    return state


# ==========================================
# 🔄 NODE 3: CALCULATIONS
# ==========================================

def analysis_node(state: AgentState):

    print("\n╭────────────────────────────────────╮")
    print("│ NODE 3: FINANCIAL ANALYSIS         │")
    print("╰────────────────────────────────────╯")

    data = state["extracted_financials"]

    rev_current = data["revenue_current_period"]
    rev_prior   = data["revenue_prior_period"]
    net_current = data["net_income_current_period"]
    net_prior   = data["net_income_prior_period"]

    current_label = data["current_period_label"]

    metrics = {}

    try:
        # Core growth metrics
        revenue_growth = ((rev_current - rev_prior) / rev_prior) * 100
        income_growth  = ((net_current - net_prior) / abs(net_prior)) * 100
        net_margin     = (net_current / rev_current) * 100

        metrics = {
            "revenue_growth_yoy_%":       round(revenue_growth, 2),
            "net_income_growth_yoy_%":    round(income_growth, 2),
            f"net_margin_{current_label}_%": round(net_margin, 2),
        }

        # Optional: gross margin
        if data.get("gross_margin_current_period"):
            gross_profit = data["gross_margin_current_period"]
            gross_margin_pct = (gross_profit / rev_current) * 100
            metrics["gross_margin_%"] = round(gross_margin_pct, 2)

        # Optional: EPS growth
        eps_current = data.get("diluted_eps_current_period")
        eps_prior   = data.get("diluted_eps_prior_period")

        if eps_current and eps_prior and eps_prior != 0:
            eps_growth = ((eps_current - eps_prior) / abs(eps_prior)) * 100
            metrics["diluted_eps_growth_%"] = round(eps_growth, 2)

        # Optional: operating margin
        op_income = data.get("operating_income_current_period")
        if op_income:
            op_margin = (op_income / rev_current) * 100
            metrics["operating_margin_%"] = round(op_margin, 2)

        # Optional: debt-to-assets ratio
        total_assets = data.get("total_assets")
        total_debt   = data.get("total_debt")

        if total_assets and total_debt and total_assets > 0:
            metrics["debt_to_assets_ratio"] = round(
                total_debt / total_assets, 2
            )

    except Exception as e:
        print(f"⚠️  Calculation Error: {e}")
        metrics = {
            "revenue_growth_yoy_%":    0,
            "net_income_growth_yoy_%": 0,
            "net_margin_%":            0,
        }

    print("✅ Metrics Calculated")
    print(metrics)

    return {
        "calculated_metrics": metrics
    }


# ==========================================
# 🔄 NODE 4: INVESTMENT MEMO GENERATION
# ==========================================

def reporting_node(state: AgentState):

    print("\n╭────────────────────────────────────╮")
    print("│ NODE 4: MEMO GENERATION            │")
    print("╰────────────────────────────────────╯")

    llm = get_llm(temp=0.2)

    data          = state["extracted_financials"]
    company_name  = data["company_name"]
    current_label = data["current_period_label"]
    prior_label   = data["prior_period_label"]
    currency      = data["currency"]
    filing_type   = data["filing_type"]
    is_profitable = data["net_income_current_period"] > 0
    prompt = f"""
You are a senior Private Equity analyst writing an investment memo for {company_name}.

Context:
- Filing Type     : {filing_type}
- Reporting Period: {current_label} vs {prior_label}
- Currency/Units  : {currency}

Use ONLY the verified financial data below. Do not invent or assume any numbers.

Raw Financials:
{state["extracted_financials"]}

Calculated Metrics:
{state["calculated_metrics"]}

Generate the memo in Markdown using exactly this structure:

# PRIVATE EQUITY INVESTMENT MEMO — {company_name}

## 1. Executive Summary
- Company overview based on filing
- Key financial highlights for {current_label}
- Notable observations vs {prior_label}

## 2. Financial Performance Analysis
- Revenue growth and drivers
- Profitability trends
- Margin performance
- Cash flow and balance sheet health (if data available)

## 3. Bull Case
List specific reasons supporting investment, grounded in the provided metrics.

## 4. Bear Case
List specific risks and concerns, grounded in the provided metrics.

## 5. Investment Recommendation
Choose one: Strong Buy | Buy | Hold | Avoid
Justify using only the provided data.
"""

    response = llm.invoke(prompt)

    print("✅ Memo Generated")

    return {
        "investment_memo": response.content
    }


# ==========================================
# 🗺️ BUILD LANGGRAPH WORKFLOW
# ==========================================

workflow = StateGraph(AgentState)

workflow.add_node("extract_data",  extraction_node)
workflow.add_node("validate_data", validation_node)
workflow.add_node("analyze_data",  analysis_node)
workflow.add_node("generate_memo", reporting_node)

workflow.set_entry_point("extract_data")

workflow.add_edge("extract_data",  "validate_data")
workflow.add_edge("validate_data", "analyze_data")
workflow.add_edge("analyze_data",  "generate_memo")
workflow.add_edge("generate_memo", END)

app = workflow.compile()

print("\n🏁 Graph Pipeline Successfully Compiled!")


# ==========================================
# 🚀 EXECUTION
# ==========================================

if __name__ == "__main__":

    inputs = {
        "pdf_path": "meshoo_2023-2024 annual report.pdf"   # replace with any company's filing
    }

    print("\n🚀 Invoking Financial Due Diligence Agent...")

    final_output = app.invoke(inputs)

    print("\n" + "=" * 70)
    print("📄 GENERATED PRIVATE EQUITY MEMO")
    print("=" * 70 + "\n")

    print(final_output["investment_memo"])