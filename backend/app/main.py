from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import Base, engine, get_db
from app.models import AnalysisRun, CRESignal, Company, Document, DocumentFetchRun, FinancialMetric, Report, Score
from app.seed import seed_database
from app.services.cre_document_analyzer import extract_rule_based, extract_with_openai
from app.services.document_text_extractor import DocumentTextExtractor
from app.services.edinet_client import EdinetClient
from app.services.ir_document_fetcher import IRDocumentFetcher
from app.services.ir_settings import build_ir_settings
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
        "structured_report": report.structured_report,
    }


def sanitize_user_message(message: str | None) -> str | None:
    if not message:
        return None
    lowered = message.lower()
    if "sk-" in message or "api_key" in lowered or "apikey" in lowered:
        return "分析または資料取得の接続設定を確認してください。認証情報は画面には表示していません。"
    if "no such file" in lowered or "/workspace/" in message or "\\" in message:
        return "取得済みファイルを参照できませんでした。資料取得を再実行し、保存先設定を確認してください。"
    if "pdfファイルサイズが上限" in message:
        return message + " IR_FETCH_MAX_FILE_MBを調整するか、対象資料を確認してください。"
    if "htmlページ内のpdf候補数0件" in message:
        return "資料PDFを取得できませんでした。対象URLがPDF直リンクではない、またはページ内にPDFリンクが見つからない可能性があります。資料URLを確認してください。"
    if "選択urlがpdfではありません" in message.lower():
        return "資料PDFを取得できませんでした。対象URLがPDF直リンクではない可能性があります。資料URLを確認してください。"
    if "fetch failed" in lowered or "urlopen" in lowered or "timed out" in lowered or "http error" in lowered:
        return "資料PDFを取得できませんでした。対象URL、ネットワーク接続、または公開サイト側の応答状況を確認してください。"
    if "docid" in lowered and ("見つ" in message or "なし" in message):
        return "EDINETで対象書類を特定できませんでした。EDINETコード、検索期間、書類種別を確認してください。"
    return message


def run_response(run: DocumentFetchRun | AnalysisRun) -> dict[str, object]:
    return {
        "run_id": run.id,
        "company_id": run.company_id,
        "document_id": run.document_id,
        "run_type": run.run_type,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": sanitize_user_message(run.error_message),
        "target_url": run.target_url,
        "saved_path": run.saved_path,
        "input_summary": run.input_summary,
        "analysis_input_source": getattr(run, "analysis_input_source", None),
        "output_summary": run.output_summary,
        "dry_run": run.dry_run,
    }


def latest_run_summary(company_id: int, db: Session) -> dict[str, object]:
    fetch_run = db.query(DocumentFetchRun).filter(DocumentFetchRun.company_id == company_id).order_by(DocumentFetchRun.started_at.desc()).first()
    analysis_run = db.query(AnalysisRun).filter(AnalysisRun.company_id == company_id).order_by(AnalysisRun.started_at.desc()).first()
    return {
        "latest_fetch_at": fetch_run.completed_at.isoformat() if fetch_run and fetch_run.completed_at else None,
        "latest_fetch_status": fetch_run.status if fetch_run else None,
        "latest_fetch_error": sanitize_user_message(fetch_run.error_message) if fetch_run else None,
        "latest_analysis_at": analysis_run.completed_at.isoformat() if analysis_run and analysis_run.completed_at else None,
        "latest_analysis_status": analysis_run.status if analysis_run else None,
        "latest_analysis_error": sanitize_user_message(analysis_run.error_message) if analysis_run else None,
    }


def add_extraction_failure_run(
    db: Session,
    *,
    company_id: int,
    document_id: int | None,
    started_at: datetime,
    target_url: str | None,
    saved_path: str | None,
    input_summary: str,
    error_message: str | None,
) -> None:
    db.add(DocumentFetchRun(
        company_id=company_id,
        document_id=document_id,
        run_type="pdf_text_extract",
        status="extract_failed",
        started_at=started_at,
        completed_at=datetime.now(UTC),
        error_message=error_message or "PDF取得は成功しましたが、テキスト抽出に失敗しました。",
        target_url=target_url,
        saved_path=saved_path,
        input_summary=input_summary,
        output_summary="PDF取得成功・テキスト抽出失敗",
        dry_run=False,
    ))

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
                "data_source_type": company.data_source_type,
                "selection_reason": company.selection_reason,
                "edinet_code": company.edinet_code,
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
            "data_source_type": company.data_source_type,
            "listing_country": company.listing_country,
            "is_public_company": company.is_public_company,
            "selection_reason": company.selection_reason,
            "edinet_code": company.edinet_code,
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
        "pipeline_status": {"config": build_ir_settings(settings).public_status(), **latest_run_summary(company_id, db)},
        "documents": [
            {
                "document_id": document.id,
                "document_type": document.document_type,
                "title": document.title,
                "document_title": document.title,
                "source_name": document.source_name,
                "source_url": document.source_url,
                "source_note": document.source_note,
                "document_language": document.document_language,
                "retrieved_at": document.retrieved_at.isoformat() if document.retrieved_at else None,
                "published_date": document.published_date.isoformat() if document.published_date else None,
                "fiscal_year": document.fiscal_year,
                "is_sample": document.is_sample,
                "fetched_file_path": document.fetched_file_path,
                "extracted_text_path": document.extracted_text_path,
                "content_type": document.content_type,
                "file_size_bytes": document.file_size_bytes,
                "external_doc_id": document.external_doc_id,
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


@app.get("/api/companies/{company_id}/documents")
def get_company_documents(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    documents = db.query(Document).filter(Document.company_id == company_id).order_by(Document.id).all()
    return {"company_id": company_id, "items": [
        {
            "document_id": document.id, "document_type": document.document_type, "title": document.title,
            "source_url": document.source_url, "source_name": document.source_name,
            "retrieved_at": document.retrieved_at.isoformat() if document.retrieved_at else None,
            "published_date": document.published_date.isoformat() if document.published_date else None,
            "fiscal_year": document.fiscal_year, "is_sample": document.is_sample,
            "fetched_file_path": document.fetched_file_path, "extracted_text_path": document.extracted_text_path,
            "content_type": document.content_type, "file_size_bytes": document.file_size_bytes,
            "external_doc_id": document.external_doc_id,
        } for document in documents], "total": len(documents), "pipeline": build_ir_settings(settings).public_status(), **latest_run_summary(company_id, db)}


@app.get("/api/companies/{company_id}/fetch-runs")
def get_fetch_runs(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    runs = db.query(DocumentFetchRun).filter(DocumentFetchRun.company_id == company_id).order_by(DocumentFetchRun.started_at.desc()).all()
    return {"company_id": company_id, "items": [run_response(run) for run in runs], "total": len(runs)}


@app.get("/api/companies/{company_id}/analysis-runs")
def get_analysis_runs(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    runs = db.query(AnalysisRun).filter(AnalysisRun.company_id == company_id).order_by(AnalysisRun.started_at.desc()).all()
    return {"company_id": company_id, "items": [run_response(run) for run in runs], "total": len(runs)}


@app.post("/api/companies/{company_id}/documents/fetch")
def fetch_company_documents(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = db.query(Company).options(selectinload(Company.documents)).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    ir_settings = build_ir_settings(settings)
    fetcher = IRDocumentFetcher(ir_settings)
    results = []
    for document in sorted(company.documents, key=lambda item: item.id):
        if document.source_name == "EDINET" or not (document.source_url or "").lower().startswith(("http://", "https://")):
            continue
        started_at = datetime.now(UTC)
        result = fetcher.fetch_document(company, document)
        if result.status == "success":
            document.fetched_file_path = result.saved_path
            document.content_type = result.content_type
            document.file_size_bytes = result.file_size_bytes
            document.retrieved_at = datetime.now(UTC)
            if result.selected_pdf_url:
                document.source_url = result.selected_pdf_url
            extraction = DocumentTextExtractor(ir_settings).extract_pdf_text(company, document, result.saved_path or "")
            if extraction.status == "success" and extraction.saved_path:
                document.extracted_text_path = extraction.saved_path
            else:
                add_extraction_failure_run(
                    db,
                    company_id=company.id,
                    document_id=document.id,
                    started_at=datetime.now(UTC),
                    target_url=result.target_url,
                    saved_path=result.saved_path,
                    input_summary=f"manual_url PDF抽出 status={extraction.status}",
                    error_message=extraction.error_message,
                )
        run = DocumentFetchRun(
            company_id=company.id, document_id=document.id, run_type="manual_url", status=result.status,
            started_at=started_at, completed_at=datetime.now(UTC), error_message=result.error_message,
            target_url=result.target_url, saved_path=result.saved_path,
            input_summary=f"source_url={document.source_url or '未登録'} original_html_url={result.original_html_url or 'なし'} selected_pdf_url={result.selected_pdf_url or 'なし'} pdf_candidate_count={result.pdf_candidate_count if result.pdf_candidate_count is not None else '未探索'}",
            output_summary=f"HTTP={result.http_status} Content-Type={result.content_type} size={result.file_size_bytes} saved_path={result.saved_path or 'なし'}",
            dry_run=result.dry_run,
        )
        db.add(run)
        results.append(result.as_dict())
    edinet_result = EdinetClient(ir_settings).fetch_latest_securities_report(company)
    if edinet_result.status == "success" and edinet_result.saved_path:
        document = db.query(Document).filter(Document.company_id == company.id, Document.external_doc_id == edinet_result.doc_id).first()
        if document is None:
            document = Document(
                company_id=company.id, document_type=edinet_result.document_type,
                title=f"{company.name} {edinet_result.document_type} {edinet_result.search_end_date}",
                source_url=None, source_name="EDINET", retrieved_at=datetime.now(UTC),
                source_note=f"EDINET docID={edinet_result.doc_id}", fiscal_year=company.fiscal_year,
                text_content="", is_sample=False, external_doc_id=edinet_result.doc_id,
            )
            db.add(document)
            db.flush()
        document.fetched_file_path = edinet_result.saved_path
        document.content_type = "application/pdf"
        document.retrieved_at = datetime.now(UTC)
        extraction = DocumentTextExtractor(ir_settings).extract_pdf_text(company, document, edinet_result.saved_path)
        if extraction.status == "success" and extraction.saved_path:
            document.extracted_text_path = extraction.saved_path
            document.text_content = Path(extraction.saved_path).read_text(encoding="utf-8")[:200000]
        else:
            add_extraction_failure_run(
                db, company_id=company.id, document_id=document.id, started_at=datetime.now(UTC),
                target_url="EDINET 書類取得API", saved_path=edinet_result.saved_path,
                input_summary=f"edinet PDF抽出 status={extraction.status}", error_message=extraction.error_message,
            )
        document_id = document.id
    else:
        document_id = None
    db.add(DocumentFetchRun(
        company_id=company.id, document_id=document_id, run_type="edinet", status=edinet_result.status,
        started_at=datetime.now(UTC), completed_at=datetime.now(UTC), error_message=edinet_result.error_message,
        target_url="EDINET 書類一覧API/書類取得API", saved_path=edinet_result.saved_path,
        input_summary=f"edinet_code={company.edinet_code or '未登録'} document_type={edinet_result.document_type} search_start_date={edinet_result.search_start_date} search_end_date={edinet_result.search_end_date} lookback_days={edinet_result.lookback_days}",
        output_summary=f"docID={edinet_result.doc_id or 'なし'} status={edinet_result.status} saved_path={edinet_result.saved_path or 'なし'}", dry_run=edinet_result.dry_run,
    ))
    if edinet_result.status not in {"skipped", "dry_run"}:
        results.append({"status": edinet_result.status, "run_type": "edinet", "doc_id": edinet_result.doc_id, "error_message": edinet_result.error_message})
    db.commit()
    status = "success" if any(item["status"] == "success" for item in results) else ("dry_run" if any(item["status"] == "dry_run" for item in results) else "skipped")
    return {"company_id": company_id, "status": status, "pipeline": ir_settings.public_status(), "results": results, **latest_run_summary(company_id, db)}


@app.post("/api/companies/{company_id}/documents/fetch-edinet")
def fetch_company_edinet(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    ir_settings = build_ir_settings(settings)
    started_at = datetime.now(UTC)
    result = EdinetClient(ir_settings).fetch_latest_securities_report(company)
    document_id = None
    extraction_summary = ""
    if result.status == "success" and result.saved_path:
        document = db.query(Document).filter(Document.company_id == company.id, Document.external_doc_id == result.doc_id).first()
        if document is None:
            document = Document(
                company_id=company.id,
                document_type=result.document_type,
                title=f"{company.name} {result.document_type} {result.search_end_date}",
                source_url=None,
                source_name="EDINET",
                retrieved_at=datetime.now(UTC),
                source_note=f"EDINET docID={result.doc_id}",
                fiscal_year=company.fiscal_year,
                text_content="",
                is_sample=False,
                external_doc_id=result.doc_id,
            )
            db.add(document)
            db.flush()
        document.fetched_file_path = result.saved_path
        document.content_type = "application/pdf"
        document.retrieved_at = datetime.now(UTC)
        document_id = document.id
        extraction = DocumentTextExtractor(ir_settings).extract_pdf_text(company, document, result.saved_path)
        extraction_summary = f" PDF抽出 status={extraction.status} chars={extraction.extracted_char_count}"
        if extraction.status == "success" and extraction.saved_path:
            document.extracted_text_path = extraction.saved_path
            document.text_content = Path(extraction.saved_path).read_text(encoding="utf-8")[:200000]
        else:
            add_extraction_failure_run(
                db, company_id=company.id, document_id=document.id, started_at=datetime.now(UTC),
                target_url="EDINET 書類取得API", saved_path=result.saved_path,
                input_summary=f"edinet PDF抽出 status={extraction.status}", error_message=extraction.error_message,
            )
    run = DocumentFetchRun(
        company_id=company.id, document_id=document_id, run_type="edinet", status=result.status,
        started_at=started_at, completed_at=datetime.now(UTC), error_message=result.error_message,
        target_url="EDINET 書類一覧API/書類取得API", saved_path=result.saved_path,
        input_summary=f"edinet_code={company.edinet_code or '未登録'} document_type={result.document_type} search_start_date={result.search_start_date} search_end_date={result.search_end_date} lookback_days={result.lookback_days}",
        output_summary=f"docID={result.doc_id or 'なし'} status={result.status} saved_path={result.saved_path or 'なし'}{extraction_summary}", dry_run=result.dry_run,
    )
    db.add(run)
    db.commit()
    return {"company_id": company_id, "status": result.status, "pipeline": ir_settings.public_status(), "result": result.as_dict(), **latest_run_summary(company_id, db)}


@app.post("/api/companies/{company_id}/analyze")
def analyze_company_documents(company_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    company = db.query(Company).options(selectinload(Company.documents)).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    ir_settings = build_ir_settings(settings)
    created_signals = 0
    results = []
    for document in sorted(company.documents, key=lambda item: item.id):
        started_at = datetime.now(UTC)
        analysis_input_source = "existing_db_text"
        extraction_summary = "analysis_input_source=existing_db_text: 既存DBテキストを分析"
        if document.extracted_text_path and Path(document.extracted_text_path).exists():
            analysis_input_source = "extracted_pdf_text"
            extraction_summary = f"analysis_input_source=extracted_pdf_text: 抽出済みPDFテキストを分析 path={document.extracted_text_path}"
            document.text_content = Path(document.extracted_text_path).read_text(encoding="utf-8")[:200000]
        elif document.fetched_file_path and Path(document.fetched_file_path).exists():
            extraction = DocumentTextExtractor(ir_settings).extract_pdf_text(company, document, document.fetched_file_path)
            if extraction.status == "success" and extraction.saved_path:
                document.extracted_text_path = extraction.saved_path
                analysis_input_source = "extracted_pdf_text"
                extraction_summary = f"analysis_input_source=extracted_pdf_text: PDF抽出 status={extraction.status} chars={extraction.extracted_char_count} path={extraction.saved_path}"
                document.text_content = Path(extraction.saved_path).read_text(encoding="utf-8")[:200000]
            else:
                extraction_summary = f"analysis_input_source=existing_db_text: PDF抽出失敗のため既存DBテキストへフォールバック status={extraction.status} error={extraction.error_message}"
        elif document.is_sample:
            analysis_input_source = "mock_seed_text"
            extraction_summary = "analysis_input_source=mock_seed_text: サンプル/シードテキストを分析"
        candidates = extract_rule_based(document)
        extracted = extract_with_openai(ir_settings, document, candidates)
        for item in extracted:
            if not item.evidence_text:
                continue
            exists = db.query(CRESignal).filter(
                CRESignal.company_id == company.id,
                CRESignal.document_id == document.id,
                CRESignal.signal_type == item.signal_type,
                CRESignal.evidence_text == item.evidence_text,
            ).first()
            if exists:
                continue
            db.add(CRESignal(
                company_id=company.id, document_id=document.id, signal_type=item.signal_type,
                title=f"{item.signal_type}の確認候補", description=item.summary, evidence_text=item.evidence_text,
                source_reference=f"{item.source_document} / {item.source_url or 'URL未登録'}", confidence=item.confidence,
                confidence_reason="公開IR資料の本文候補から抽出。正式方針や提案機会を断定せず、一次情報確認が必要です。",
                extracted_by=item.extracted_by,
            ))
            created_signals += 1
        status = "success" if extracted else "skipped"
        run = AnalysisRun(
            company_id=company.id, document_id=document.id, run_type=ir_settings.effective_analysis_mode, status=status,
            started_at=started_at, completed_at=datetime.now(UTC), error_message=None if extracted else "CRE関連キーワード候補が見つかりませんでした。",
            target_url=document.source_url, saved_path=document.extracted_text_path, input_summary=extraction_summary,
            analysis_input_source=analysis_input_source, output_summary=f"抽出シグナル数={len(extracted)}", dry_run=False,
        )
        db.add(run)
        results.append({"document_id": document.id, "status": status, "signals": [item.as_dict() for item in extracted], "input_summary": extraction_summary, "analysis_input_source": analysis_input_source})
    db.commit()
    return {"company_id": company_id, "status": "success" if created_signals else "skipped", "pipeline": ir_settings.public_status(), "created_signal_count": created_signals, "analysis_input_source": results[0]["analysis_input_source"] if results else None, "results": results, **latest_run_summary(company_id, db)}


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
