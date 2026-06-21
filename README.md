# 📊 Automated Financial Due Diligence Agent

An AI-powered agent built for **Private Equity** workflows that ingests a company's financial filing (10-K, 10-Q, 8-K, or annual report PDF) and produces a structured **investment memo** — automatically extracting financial metrics, calculating growth and profitability ratios, and generating bull/bear analysis with an investment recommendation.

> Upload a PDF. Get a PE-grade memo. In seconds.

---

## ✨ What It Does

1. **Extracts** financial data from any company's filing PDF (10-K, 10-Q, 8-K, annual reports — US or Indian formats)
2. **Validates** the extracted data for sanity (missing fields, negative revenue, suspicious deltas)
3. **Calculates** growth rates, margins, and debt ratios — context-aware for loss-making vs. profitable companies
4. **Generates** a full Markdown investment memo: Executive Summary, Financial Analysis, Bull Case, Bear Case, and Recommendation
5. **Scores its own confidence** based on how much data was successfully extracted

---

## 🧠 How It Works

```
PDF Upload
    │
    ▼
┌─────────────────────────┐
│  Smart PDF Filtering    │  → Targets ONLY primary financial statement
│  (pdfplumber)            │     pages, skips notes/auditor/ESOP sections
└────────────┬─────────────┘
             ▼
┌─────────────────────────┐
│  NODE 1: Extraction      │  → LLM (Groq Llama 3.3 70B) extracts structured
│  (LangGraph)              │     JSON via Pydantic schema
└────────────┬─────────────┘
             ▼
┌─────────────────────────┐
│  NODE 2: Validation       │  → Sanity checks: missing fields, negative
└────────────┬─────────────┘     revenue, suspicious YoY deltas
             ▼
┌─────────────────────────┐
│  NODE 3: Analysis         │  → Revenue growth, net margin, gross/operating
└────────────┬─────────────┘     margin, EPS growth, debt-to-assets, confidence score
             ▼
┌─────────────────────────┐
│  NODE 4: Memo Generation  │  → LLM writes the final PE investment memo
└────────────┬─────────────┘
             ▼
     Structured JSON + Markdown Memo
```

Built as a **LangGraph** state machine — each node is independently testable and the full pipeline is one `.invoke()` call.

---

## 🗂️ Project Structure

```
financial-due-diligence-agent/
├── app/
│   ├── __init__.py
│   ├── models.py          # Pydantic schemas: FinancialMetrics, AgentState, AnalysisResponse
│   ├── ml_logic.py         # LangGraph pipeline: extraction, validation, analysis, memo nodes
│   └── api.py              # FastAPI app: routes, error handling, request/response wiring
├── main.py                 # Thin entrypoint re-exporting the compiled LangGraph app
├── streamlit_app.py         # Streamlit UI — file upload + memo display
├── Dockerfile
├── requirements.txt
├── .env                     # GROQ_API_KEY (never commit this)
├── .gitignore
└── README.md
```

| File | Responsibility |
|---|---|
| `app/models.py` | All data shapes — `FinancialMetrics` (extraction schema), `AgentState` (LangGraph state), `AnalysisResponse` (API response) |
| `app/ml_logic.py` | PDF text extraction, LLM calls, financial calculations, the compiled LangGraph workflow |
| `app/api.py` | FastAPI routes (`/`, `/health`, `/version`, `/analyze`), CORS, layered error handling |
| `main.py` | Imports and re-exports the compiled graph for direct CLI use |
| `streamlit_app.py` | Browser-based UI for non-technical users |

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/yourusername/financial-due-diligence-agent.git
cd financial-due-diligence-agent
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 2. Set your API key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_key_here
```

> Get a free key at [console.groq.com](https://console.groq.com). Never commit this file — it's already in `.gitignore`.

### 3. Run the API locally

```bash
uvicorn app.api:api --reload
```

Visit:
- `http://127.0.0.1:8000` — API info
- `http://127.0.0.1:8000/health` — health check
- `http://127.0.0.1:8000/docs` — interactive Swagger UI (upload a PDF here to test)

### 4. Or run the Streamlit UI

```bash
streamlit run streamlit_app.py
```

---

## 📡 API Reference

### `GET /`
Returns API metadata and available endpoints.

### `GET /health`
Health check — confirms the service and model are reachable.

### `GET /version`
Returns the current API and model version.

### `POST /analyze`
Upload a financial filing PDF and receive a full analysis.

**Request:**
```bash
curl -X POST 'http://127.0.0.1:8000/analyze' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@apple_8k.pdf;type=application/pdf'
```

**Response:**
```json
{
  "company_name": "Apple Inc.",
  "filing_type": "8-K",
  "extracted_financials": {
    "revenue_current_period": 111184.0,
    "revenue_prior_period": 95359.0,
    "net_income_current_period": 29578.0,
    "net_income_prior_period": 24780.0,
    "currency": "USD in millions",
    "total_assets": 371082.0,
    "total_debt": 264591.0
  },
  "calculated_metrics": {
    "revenue_growth_yoy_%": 16.6,
    "net_income_growth_yoy_%": 19.36,
    "profitability_status": "Profitable",
    "debt_to_assets_ratio": 0.71
  },
  "investment_memo": "# PRIVATE EQUITY INVESTMENT MEMO — Apple Inc. ...",
  "confidence_score": 0.85,
  "model_version": "1.0.0",
  "processing_time_seconds": 4.32,
  "warnings": []
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| `422` | Validation error — required financial fields missing or malformed |
| `502` | Pipeline/LLM error — extraction or memo generation failed |
| `500` | Unexpected server error |

---

## 🧩 Key Design Decisions

### Smart page filtering, not brute-force chunking
Early versions sent every page containing words like *"net income"* to the LLM — this captured 25+ pages of notes, ESOP disclosures, and auditor reports, blowing through free-tier token limits. The pipeline now filters to **primary financial statement pages only** (P&L, balance sheet, cash flow statement) and explicitly excludes notes/annexure pages.

### Schema fields are all `Optional`
Real filings don't always disclose every metric (EPS, operating cash flow, total debt may be absent in an 8-K). Making fields required caused Pydantic validation crashes on partial extractions — every field is now `Optional[float]` / `Optional[str]` with `None` defaults, and required-field checks happen explicitly in the **validation node**, not the schema.

### Negative number handling
Indian filings show losses in brackets — `(1,569)` — which LLMs often strip the sign from. The extraction prompt explicitly instructs the model to convert bracketed/labeled losses into negative floats.

### Context-aware profitability metrics
A company moving from a ₹1,569 Cr loss to a ₹53 Cr loss is *not* "net income growth" — it's **loss reduction**. The analysis node branches on sign combinations (`loss→loss`, `loss→profit`, `profit→profit`) to produce metrics that are actually meaningful to a PE analyst rather than misleading percentage swings.

### Layered error handling
| Exception | HTTP Status | Meaning |
|---|---|---|
| `ValueError` | 422 | Bad/incomplete input data |
| `RuntimeError` | 502 | LLM or pipeline failure |
| `Exception` | 500 | Anything unexpected |

### Confidence scoring
Every response includes a `confidence_score` (0.0–1.0) that decreases for each optional field the extraction failed to find — so consumers of the API know *how much to trust* a given memo, not just receive it blindly.

---

## 🐳 Docker

```bash
docker build -t financial-agent .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key financial-agent
```

---

## ☁️ Deployment (Render)

1. Push this repo to GitHub
2. On [render.com](https://render.com) → **New → Web Service**
3. Connect your repo, select **Docker** as the runtime
4. Add environment variable: `GROQ_API_KEY`
5. Deploy — Render builds the Dockerfile and gives you a live URL

> Free tier spins down after 15 minutes of inactivity; first request after idling may take 30–60s to wake up.

---

## 🛣️ Roadmap

- [ ] Smarter page filter with confidence-weighted keyword scoring
- [ ] Multi-document comparison (compare two filings side by side)
- [ ] Company/sector tiering (`Large Cap` / `Mid Cap` / `Small Cap`) based on extracted revenue
- [ ] Support for chunked extraction on very large filings (10-Ks, 100+ pages) without hitting rate limits
- [ ] Vector-based RAG retrieval (LlamaIndex) for qualitative risk factors beyond raw numbers

---

## ⚠️ Disclaimer

This tool is for educational and research purposes. It does not constitute financial advice. Always verify extracted figures against the source filing before making investment decisions.

---

## 🛠️ Tech Stack

- **LangGraph** — orchestrates the multi-step extraction → validation → analysis → memo pipeline
- **Groq (Llama 3.3 70B)** — LLM backend for extraction and memo generation
- **pdfplumber** — PDF text and table extraction
- **Pydantic** — schema validation and structured output parsing
- **FastAPI** — REST API layer
- **Streamlit** — browser UI
- **Docker + Render** — containerized deployment
