from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import Base, engine, get_db
from app.models import CRESignal, Company, FinancialMetric, Report, Score
from app.seed import seed_database
from app.services.reporting import CompanyReportResult, generate_company_report
from app.services.scoring import build_component_details

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_database(db)
    yield


app = FastAPI(
    title=settings.app_name,
    description="CRE コンサルティング営業向けローカルデモアプリケーションの API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def latest_score(company: Company) -> Score | None:
    return max(company.scores, key=lambda score: score.calculated_at, default=None)


def latest_financial_metric(company: Company) -> FinancialMetric | None:
    return max(company.financial_metrics, key=lambda metric: metric.fiscal_year, default=None)


def score_response(score: Score | None) -> dict[str, object] | None:
    if score is None:
        return None
    component_scores = {
        "signal_score": score.signal_score,
        "financial_score": score.financial_score,
        "strategic_event_score": score.strategic_event_score,
        "fit_score": score.fit_score,
    }
    component_details = build_component_details(component_scores=component_scores)
    return {
        "total_score": score.total_score,
        "priority_label": score.priority_label,
        "component_scores": component_scores,
        "component_details": {
            key: {"score": detail.score, "max_points": detail.max_points, "reason": detail.reason}
            for key, detail in component_details.items()
        },
        "explanation": score.explanation,
        "recommended_action": score.recommended_action,
        "calculated_at": score.calculated_at.isoformat(),
    }



def report_response(report: CompanyReportResult) -> dict[str, object]:
    preview = report.markdown_content[:600]
    return {
        "company_id": report.company_id,
        "title": report.title,
        "generation_status": report.generation_status,
        "generated_at": report.generated_at.isoformat(),
        "generated_by": report.generated_by,
        "signal_count": report.signal_count,
        "preview": preview,
        "markdown_content": report.markdown_content,
    }

def signal_response(signal: CRESignal) -> dict[str, object]:
    return {
        "signal_id": signal.id,
        "document_id": signal.document_id,
        "signal_type": signal.signal_type,
        "title": signal.title,
        "description": signal.description,
        "evidence_text": signal.evidence_text,
        "source_reference": signal.source_reference,
        "confidence": signal.confidence,
        "confidence_reason": signal.confidence_reason,
        "extracted_by": signal.extracted_by,
    }


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Return service status for frontend/backend connectivity checks."""

    return {
        "status": "ok",
        "app": settings.app_name,
        "mode": settings.ai_mode,
        "database": "sqlite",
    }


@app.get("/api/config")
def frontend_config() -> dict[str, str]:
    """Return non-sensitive configuration values for the browser UI."""

    return {
        "appName": settings.app_name,
        "aiMode": settings.ai_mode,
        "language": "ja",
    }


@app.get("/api/companies")
def list_companies(db: Session = Depends(get_db)) -> dict[str, object]:
    companies = (
        db.query(Company)
        .options(selectinload(Company.cre_signals), selectinload(Company.scores))
        .order_by(Company.id)
        .all()
    )
    items = []
    for company in companies:
        score = latest_score(company)
        items.append(
            {
                "company_id": company.id,
                "ticker": company.ticker,
                "name": company.name,
                "industry": company.industry,
                "market": company.market,
                "total_score": score.total_score if score else None,
                "priority_label": score.priority_label if score else "未評価",
                "signal_count": len(company.cre_signals),
            }
        )
    return {"items": items, "total": len(items)}


@app.get("/api/companies/{company_id}")
def get_company_detail(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = (
        db.query(Company)
        .options(
            selectinload(Company.documents),
            selectinload(Company.financial_metrics),
            selectinload(Company.cre_signals),
            selectinload(Company.scores),
        )
        .filter(Company.id == company_id)
        .first()
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    metric = latest_financial_metric(company)
    score = latest_score(company)
    return {
        "company": {
            "company_id": company.id,
            "ticker": company.ticker,
            "name": company.name,
            "market": company.market,
            "industry": company.industry,
            "headquarters_location": company.headquarters_location,
            "employee_count": company.employee_count,
            "revenue": company.revenue,
            "fiscal_year": company.fiscal_year,
        },
        "latest_financial_metrics": None
        if metric is None
        else {
            "fiscal_year": metric.fiscal_year,
            "revenue_growth_pct": metric.revenue_growth_pct,
            "operating_margin_pct": metric.operating_margin_pct,
            "capex_amount": metric.capex_amount,
            "cash_and_equivalents": metric.cash_and_equivalents,
            "segment_change_note": metric.segment_change_note,
            "source_document_id": metric.source_document_id,
        },
        "cre_signals": [signal_response(signal) for signal in sorted(company.cre_signals, key=lambda item: item.id)],
        "score_breakdown": score_response(score),
        "documents": [
            {
                "document_id": document.id,
                "document_type": document.document_type,
                "title": document.title,
                "source_name": document.source_name,
                "published_date": document.published_date.isoformat() if document.published_date else None,
                "fiscal_year": document.fiscal_year,
                "is_sample": document.is_sample,
            }
            for document in sorted(company.documents, key=lambda item: item.id)
        ],
    }


@app.get("/api/companies/{company_id}/signals")
def get_company_signals(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    signals = db.query(CRESignal).filter(CRESignal.company_id == company_id).order_by(CRESignal.id).all()
    return {"company_id": company_id, "items": [signal_response(signal) for signal in signals], "total": len(signals)}


@app.get("/api/companies/{company_id}/score")
def get_company_score(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = db.query(Company).options(selectinload(Company.scores)).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    score = score_response(latest_score(company))
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"company_id": company_id, **score}


@app.get("/api/companies/{company_id}/report")
def get_company_report(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = (
        db.query(Company)
        .options(
            selectinload(Company.documents),
            selectinload(Company.financial_metrics),
            selectinload(Company.cre_signals),
            selectinload(Company.scores),
            selectinload(Company.reports),
        )
        .filter(Company.id == company_id)
        .first()
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    generated_report = generate_company_report(
        company=company,
        latest_metric=latest_financial_metric(company),
        latest_score=latest_score(company),
    )
    latest_stored_report = max(company.reports, key=lambda report: report.created_at, default=None)
    if latest_stored_report is None:
        db.add(
            Report(
                company_id=company.id,
                title=generated_report.title,
                markdown_content=generated_report.markdown_content,
                generated_by=generated_report.generated_by,
                created_at=generated_report.generated_at,
            )
        )
    else:
        latest_stored_report.title = generated_report.title
        latest_stored_report.markdown_content = generated_report.markdown_content
        latest_stored_report.generated_by = generated_report.generated_by
        latest_stored_report.created_at = generated_report.generated_at
    db.commit()
    return report_response(generated_report)
