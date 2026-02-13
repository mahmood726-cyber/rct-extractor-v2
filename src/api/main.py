"""
RCT Extractor REST API
======================

FastAPI-based REST API for effect estimate extraction from RCT publications.

Endpoints:
    POST /extract          - Extract from text
    POST /extract/pdf      - Extract from PDF file
    GET  /validate/{id}    - Validate extraction against CTG
    GET  /health           - Health check

Usage:
    # Start server
    uvicorn src.api.main:app --reload --port 8000

    # Or with CLI
    python -m src.api.main

Requirements:
    pip install fastapi uvicorn python-multipart
"""

import os
import sys
import json
import tempfile
import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("FastAPI not installed. Run: pip install fastapi uvicorn python-multipart")

# Import extractors — try relative imports first, fall back to absolute
try:
    from ..core.enhanced_extractor_v3 import EnhancedExtractor, Extraction, EffectType, AutomationTier
    from .. import __version__
except ImportError:
    from src.core.enhanced_extractor_v3 import EnhancedExtractor, Extraction, EffectType, AutomationTier
    from src import __version__

# Maximum PDF upload size: 50 MB
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024


# =============================================================================
# Pydantic Models
# =============================================================================

class ExtractionRequest(BaseModel):
    """Request body for text extraction"""
    text: str = Field(..., description="Text to extract effects from", max_length=500_000)
    include_raw: bool = Field(False, description="Include raw extraction details")


class ConfidenceIntervalResponse(BaseModel):
    """Confidence interval in response"""
    lower: float
    upper: float
    level: float = 0.95


class ExtractionResponse(BaseModel):
    """Single extraction result"""
    effect_type: str
    point_estimate: float
    ci: Optional[ConfidenceIntervalResponse] = None
    p_value: Optional[float] = None
    standard_error: Optional[float] = None
    source_text: str = ""
    confidence: float
    automation_tier: str
    has_complete_ci: bool
    warnings: List[str] = []


class ExtractResponse(BaseModel):
    """Response for extraction endpoint"""
    success: bool
    extraction_count: int
    extractions: List[ExtractionResponse]
    processing_time_ms: float
    version: str


class ValidationRequest(BaseModel):
    """Request body for CTG validation"""
    nct_id: str = Field(..., description="ClinicalTrials.gov NCT ID")
    extractions: List[ExtractionResponse]


class ValidationMatch(BaseModel):
    """Single validation match result"""
    outcome: str
    expected_type: str
    expected_value: float
    extracted_value: Optional[float]
    value_match: bool
    type_match: bool
    ci_match: bool


class ValidationResponse(BaseModel):
    """Response for validation endpoint"""
    nct_id: str
    matches_found: int
    total_expected: int
    accuracy: float
    matches: List[ValidationMatch]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    components: Dict[str, str]


# =============================================================================
# API Application
# =============================================================================

def create_app() -> "FastAPI":
    """Create and configure the FastAPI application"""

    if not HAS_FASTAPI:
        raise ImportError("FastAPI not installed")

    app = FastAPI(
        title="RCT Extractor API",
        description="Extract effect estimates (HR, OR, RR, MD, SMD) from RCT publications",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware — do not use allow_origins=["*"] with credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Initialize extractor
    extractor = EnhancedExtractor()

    # ==========================================================================
    # Endpoints
    # ==========================================================================

    @app.get("/", include_in_schema=False)
    async def root():
        """Root redirect to docs"""
        return {"message": "RCT Extractor API. Visit /docs for documentation."}

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """
        Health check endpoint.

        Returns system status and component availability.
        """
        components = {
            "extractor": "healthy",
            "pdf_parser": "unknown",
            "ctg_validator": "unknown",
        }

        # Check PDF parser
        try:
            from src.pdf.pdf_parser import PDFParser
            components["pdf_parser"] = "healthy"
        except ImportError:
            components["pdf_parser"] = "unavailable"

        # Check CTG validator
        try:
            from scripts.ctg_validator import CTGValidator
            components["ctg_validator"] = "healthy"
        except ImportError:
            components["ctg_validator"] = "unavailable"

        return HealthResponse(
            status="healthy",
            version=__version__,
            timestamp=datetime.utcnow().isoformat(),
            components=components
        )

    @app.post("/extract", response_model=ExtractResponse, tags=["Extraction"])
    async def extract_from_text(request: ExtractionRequest):
        """
        Extract effect estimates from text.

        Supports:
        - Hazard Ratio (HR)
        - Odds Ratio (OR)
        - Risk Ratio / Relative Risk (RR)
        - Mean Difference (MD)
        - Standardized Mean Difference (SMD)
        - Incidence Rate Ratio (IRR)
        - Absolute Risk Difference (ARD)
        """
        import time
        start_time = time.time()

        try:
            # Extract
            results = extractor.extract(request.text)

            # Convert to response format
            extractions = []
            for r in results:
                ci_response = None
                if r.ci:
                    ci_response = ConfidenceIntervalResponse(
                        lower=r.ci.lower,
                        upper=r.ci.upper,
                        level=r.ci.level
                    )

                extractions.append(ExtractionResponse(
                    effect_type=r.effect_type.value,
                    point_estimate=r.point_estimate,
                    ci=ci_response,
                    p_value=r.p_value,
                    standard_error=r.standard_error,
                    source_text=r.source_text if request.include_raw else "",
                    confidence=r.calibrated_confidence,
                    automation_tier=r.automation_tier.value,
                    has_complete_ci=r.has_complete_ci,
                    warnings=r.warnings
                ))

            processing_time = (time.time() - start_time) * 1000

            return ExtractResponse(
                success=True,
                extraction_count=len(extractions),
                extractions=extractions,
                processing_time_ms=round(processing_time, 2),
                version=__version__
            )

        except Exception as e:
            logger.exception("Extraction failed")
            raise HTTPException(status_code=500, detail="Internal extraction error")

    @app.post("/extract/pdf", response_model=ExtractResponse, tags=["Extraction"])
    async def extract_from_pdf(
        file: UploadFile = File(..., description="PDF file to extract from"),
        include_raw: bool = Query(False, description="Include raw extraction details")
    ):
        """
        Extract effect estimates from a PDF file.

        Supports both born-digital and scanned PDFs (via OCR).
        """
        import time
        start_time = time.time()

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        try:
            # Import PDF parser
            try:
                from ..pdf.pdf_parser import PDFParser
            except ImportError:
                from src.pdf.pdf_parser import PDFParser
            parser = PDFParser()

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                content = await file.read()
                if len(content) > MAX_PDF_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"PDF exceeds maximum size of {MAX_PDF_SIZE_BYTES // (1024*1024)} MB"
                    )
                tmp.write(content)
                tmp_path = tmp.name

            try:
                # Parse PDF
                pdf_content = parser.parse(tmp_path)
                full_text = "\n".join(p.full_text for p in pdf_content.pages)

                # Extract effects
                results = extractor.extract(full_text)

                # Convert to response format
                extractions = []
                for r in results:
                    ci_response = None
                    if r.ci:
                        ci_response = ConfidenceIntervalResponse(
                            lower=r.ci.lower,
                            upper=r.ci.upper,
                            level=r.ci.level
                        )

                    extractions.append(ExtractionResponse(
                        effect_type=r.effect_type.value,
                        point_estimate=r.point_estimate,
                        ci=ci_response,
                        p_value=r.p_value,
                        standard_error=r.standard_error,
                        source_text=r.source_text if include_raw else "",
                        confidence=r.calibrated_confidence,
                        automation_tier=r.automation_tier.value,
                        has_complete_ci=r.has_complete_ci,
                        warnings=r.warnings
                    ))

                processing_time = (time.time() - start_time) * 1000

                return ExtractResponse(
                    success=True,
                    extraction_count=len(extractions),
                    extractions=extractions,
                    processing_time_ms=round(processing_time, 2),
                    version=__version__
                )

            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF parsing not available. Install pdfplumber."
            )
        except Exception as e:
            logger.exception("PDF extraction failed")
            raise HTTPException(status_code=500, detail="Internal PDF extraction error")

    @app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
    async def validate_extraction(request: ValidationRequest):
        """
        Validate extractions against ClinicalTrials.gov results.

        Compares extracted effect estimates with published CTG results
        for accuracy assessment.
        """
        try:
            from scripts.ctg_scraper import CTGScraper
            from scripts.ctg_validator import CTGValidator

            scraper = CTGScraper()
            validator = CTGValidator()

            # Fetch CTG data
            study = scraper.fetch_study(request.nct_id)
            if not study:
                raise HTTPException(
                    status_code=404,
                    detail=f"Study {request.nct_id} not found on ClinicalTrials.gov"
                )

            # Convert study to dict format for validator
            ctg_data = study.to_dict()

            # Create simple validation by matching effects
            matches = []
            ctg_effects = ctg_data.get("effect_estimates", [])

            for ctg_effect in ctg_effects:
                # Find best matching extraction
                best_match = None
                best_score = 0

                for ext in request.extractions:
                    score = 0
                    # Type match
                    if ctg_effect.get("effect_type", "").upper() == ext.effect_type.upper():
                        score += 0.4
                    # Value match (within 2%)
                    ctg_val = ctg_effect.get("value", 0)
                    if ctg_val > 0:
                        rel_diff = abs(ctg_val - ext.point_estimate) / ctg_val
                        if rel_diff <= 0.02:
                            score += 0.6

                    if score > best_score:
                        best_score = score
                        best_match = ext

                # Calculate match flags
                value_match = False
                type_match = False
                ci_match = False

                if best_match:
                    ctg_val = ctg_effect.get("value", 0)
                    if ctg_val > 0:
                        rel_diff = abs(ctg_val - best_match.point_estimate) / ctg_val
                        value_match = rel_diff <= 0.02
                    type_match = ctg_effect.get("effect_type", "").upper() == best_match.effect_type.upper()

                    # CI match (if available)
                    if best_match.ci:
                        ctg_lower = ctg_effect.get("ci_lower")
                        ctg_upper = ctg_effect.get("ci_upper")
                        if ctg_lower and ctg_upper:
                            lower_diff = abs(ctg_lower - best_match.ci.lower) / max(abs(ctg_lower), 0.01)
                            upper_diff = abs(ctg_upper - best_match.ci.upper) / max(abs(ctg_upper), 0.01)
                            ci_match = lower_diff <= 0.05 and upper_diff <= 0.05

                matches.append(ValidationMatch(
                    outcome=ctg_effect.get("outcome_title", "")[:50],
                    expected_type=ctg_effect.get("effect_type", ""),
                    expected_value=ctg_effect.get("value", 0),
                    extracted_value=best_match.point_estimate if best_match else None,
                    value_match=value_match,
                    type_match=type_match,
                    ci_match=ci_match
                ))

            # Calculate accuracy
            total = len(ctg_effects)
            matched = sum(1 for m in matches if m.value_match and m.type_match)
            accuracy = matched / total if total > 0 else 0

            return ValidationResponse(
                nct_id=request.nct_id,
                matches_found=matched,
                total_expected=total,
                accuracy=round(accuracy, 4),
                matches=matches
            )

        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="CTG validation not available. Check scripts/ctg_validator.py"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Validation failed")
            raise HTTPException(status_code=500, detail="Internal validation error")

    @app.get("/stats", tags=["System"])
    async def get_stats():
        """
        Get extraction statistics and capabilities.
        """
        return {
            "supported_effect_types": [e.value for e in EffectType],
            "automation_tiers": [t.value for t in AutomationTier],
            "pattern_counts": {
                "HR": len(extractor.HR_PATTERNS),
                "OR": len(extractor.OR_PATTERNS),
                "RR": len(extractor.RR_PATTERNS),
                "MD": len(extractor.MD_PATTERNS),
                "SMD": len(extractor.SMD_PATTERNS),
            },
            "features": [
                "multi_language_support",
                "ocr_preprocessing",
                "table_extraction",
                "forest_plot_parsing",
                "ctg_validation",
            ]
        }

    return app


# Create default app instance
if HAS_FASTAPI:
    app = create_app()
else:
    app = None


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run the API server"""
    if not HAS_FASTAPI:
        print("Error: FastAPI not installed")
        print("Run: pip install fastapi uvicorn python-multipart")
        sys.exit(1)

    import uvicorn

    print("Starting RCT Extractor API...")
    print("Documentation: http://localhost:8000/docs")

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
