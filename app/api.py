from dotenv import load_dotenv
load_dotenv()
import os
print("🔑 KEY LOADED:", os.environ.get("GROQ_API_KEY", "NOT FOUND"))
VERSION = "1.0.0"


import shutil
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
#from pydantic import BaseModel
from app.model import AnalysisResponse
# Import your existing pipeline
#from main import app as langgraph_app
from app.ml_logic import app as langgraph_app

api = FastAPI(
    title="Financial Due Diligence Agent",
    description="Upload a financial filing PDF and get an investment memo",
    version=VERSION
)

# Allow frontend to call this API
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# class AnalysisResponse(BaseModel):
#     company_name: str
#     filing_type: str
#     extracted_financials: dict
#     calculated_metrics: dict
#     investment_memo: str

#error helper
def make_error(code: int, message: str):
    raise HTTPException(status_code=code, detail={"error": message})

@api.get("/")
def home():
    return {
        "name": "Financial Due Diligence Agent",
        "version": VERSION,
        "endpoints": {
            "home": "GET /",
            "health": "GET /health",
            "analyze": "POST /analyze"
        }
    }

@api.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model": "llama-3.3-70b-versatile",
        "pipeline": "LangGraph + LlamaIndex"
    }

@api.get("/version")
def get_version():
    return {
        "version": VERSION,
        "model": "llama-3.3-70b-versatile",
    }

@api.post("/analyze", response_model=AnalysisResponse)
async def analyze_filing(file: UploadFile = File(...)):

    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Save uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run your LangGraph pipeline
        # inputs = {"pdf_path": temp_path}
        # result = langgraph_app.invoke(inputs)

        inputs = {"pdf_path": temp_path, "warnings": []}
        start_time = time.time()
        result = langgraph_app.invoke(inputs)
        end_time = time.time()

        # return AnalysisResponse(
        #     company_name=result["extracted_financials"].get("company_name", "Unknown"),
        #     filing_type=result["extracted_financials"].get("filing_type", "Unknown"),
        #     extracted_financials=result["extracted_financials"],
        #     calculated_metrics=result["calculated_metrics"],
        #     investment_memo=result["investment_memo"]
        # )

        return AnalysisResponse(
            company_name=result["extracted_financials"].get("company_name", "Unknown"),
            filing_type=result["extracted_financials"].get("filing_type", "Unknown"),
            extracted_financials=result["extracted_financials"],
            calculated_metrics=result["calculated_metrics"],
            investment_memo=result["investment_memo"],
            model_version=VERSION,
            processing_time_seconds=round(end_time - start_time, 2),
            warnings=result.get("warnings", [])
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")

    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Pipeline error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    finally:
        # Always clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)