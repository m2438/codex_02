from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    market: Mapped[str] = mapped_column(String(80))
    industry: Mapped[str] = mapped_column(String(80), index=True)
    headquarters_location: Mapped[str] = mapped_column(String(120))
    employee_count: Mapped[int] = mapped_column(Integer)
    revenue: Mapped[int] = mapped_column(Integer)
    fiscal_year: Mapped[str] = mapped_column(String(16))
    data_source_type: Mapped[str] = mapped_column(String(20), default="synthetic", index=True)
    listing_country: Mapped[str] = mapped_column(String(80), default="日本")
    is_public_company: Mapped[bool] = mapped_column(Boolean, default=True)
    selection_reason: Mapped[str] = mapped_column(Text, default="合成デモデータ")
    edinet_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    documents: Mapped[list["Document"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    financial_metrics: Mapped[list["FinancialMetric"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    cre_signals: Mapped[list["CRESignal"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    scores: Mapped[list["Score"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    document_fetch_runs: Mapped[list["DocumentFetchRun"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_name: Mapped[str] = mapped_column(String(120), default="サンプルIR文書")
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_note: Mapped[str] = mapped_column(Text, default="")
    document_language: Mapped[str] = mapped_column(String(20), default="ja")
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fiscal_year: Mapped[str] = mapped_column(String(16))
    text_content: Mapped[str] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)
    fetched_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_doc_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    company: Mapped[Company] = relationship(back_populates="documents")
    cre_signals: Mapped[list["CRESignal"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    document_fetch_runs: Mapped[list["DocumentFetchRun"]] = relationship(back_populates="document")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="document")


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    fiscal_year: Mapped[str] = mapped_column(String(16))
    revenue_growth_pct: Mapped[float] = mapped_column(Float)
    operating_margin_pct: Mapped[float] = mapped_column(Float)
    capex_amount: Mapped[int] = mapped_column(Integer)
    cash_and_equivalents: Mapped[int] = mapped_column(Integer)
    segment_change_note: Mapped[str] = mapped_column(Text)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    company: Mapped[Company] = relationship(back_populates="financial_metrics")


class CRESignal(Base):
    __tablename__ = "cre_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    evidence_text: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(String(300))
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    confidence_reason: Mapped[str] = mapped_column(Text)
    extracted_by: Mapped[str] = mapped_column(String(40), default="seed_mock")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    company: Mapped[Company] = relationship(back_populates="cre_signals")
    document: Mapped[Document] = relationship(back_populates="cre_signals")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    total_score: Mapped[int] = mapped_column(Integer)
    priority_label: Mapped[str] = mapped_column(String(20))
    signal_score: Mapped[int] = mapped_column(Integer)
    financial_score: Mapped[int] = mapped_column(Integer)
    strategic_event_score: Mapped[int] = mapped_column(Integer)
    fit_score: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    company: Mapped[Company] = relationship(back_populates="scores")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    markdown_content: Mapped[str] = mapped_column(Text)
    generated_by: Mapped[str] = mapped_column(String(40), default="not_generated")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    company: Mapped[Company] = relationship(back_populates="reports")


class DocumentFetchRun(Base):
    __tablename__ = "document_fetch_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    run_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    saved_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)

    company: Mapped[Company] = relationship(back_populates="document_fetch_runs")
    document: Mapped[Document | None] = relationship(back_populates="document_fetch_runs")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    run_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    saved_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)

    company: Mapped[Company] = relationship(back_populates="analysis_runs")
    document: Mapped[Document | None] = relationship(back_populates="analysis_runs")
