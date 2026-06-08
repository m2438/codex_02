export type PriorityLabel = '高' | '中' | '低' | '未評価';
export type DataSourceType = 'synthetic' | 'public_demo';
export type ConfidenceLabel = 'high' | 'medium' | 'low';

export type HealthResponse = {
  status: string;
  app: string;
  mode: 'mock' | 'openai';
  database: string;
};

export type CompanySummary = {
  company_id: number;
  ticker: string;
  name: string;
  industry: string;
  market: string;
  data_source_type: DataSourceType;
  selection_reason: string;
  total_score: number | null;
  priority_label: PriorityLabel;
  signal_count: number;
};

export type CompaniesResponse = {
  items: CompanySummary[];
  total: number;
};

export type CompanyProfile = {
  company_id: number;
  ticker: string;
  name: string;
  market: string;
  industry: string;
  headquarters_location: string;
  employee_count: number;
  revenue: number;
  fiscal_year: string;
  data_source_type: DataSourceType;
  listing_country: string;
  is_public_company: boolean;
  selection_reason: string;
  edinet_code: string | null;
};

export type FinancialMetricScales = {
  growthMinPct: number;
  growthMaxPct: number;
  marginMaxPct: number;
  capexMaxOku: number;
  cashMaxOku: number;
};

export type FinancialMetrics = {
  fiscal_year: string;
  revenue_growth_pct: number;
  operating_margin_pct: number;
  capex_amount: number;
  cash_and_equivalents: number;
  segment_change_note: string;
  source_document_id: number | null;
};

export type CRESignal = {
  signal_id: number;
  document_id: number;
  signal_type: string;
  title: string;
  description: string;
  evidence_text: string;
  source_reference: string;
  confidence: ConfidenceLabel;
  confidence_reason: string;
  extracted_by: string;
};

export type ScoreComponentKey = 'signal_score' | 'financial_score' | 'strategic_event_score' | 'fit_score';

export type ScoreComponentDetail = {
  score: number;
  max_points: number;
  reason: string;
};

export type ScoreBreakdownResponse = {
  total_score: number;
  priority_label: PriorityLabel;
  component_scores: Record<ScoreComponentKey, number>;
  component_details: Record<ScoreComponentKey, ScoreComponentDetail>;
  explanation: string;
  recommended_action: string;
  calculated_at: string;
};

export type DocumentSummary = {
  document_id: number;
  document_type: string;
  title: string;
  document_title: string;
  source_name: string;
  source_url: string | null;
  source_note: string;
  document_language: string;
  retrieved_at: string | null;
  published_date: string | null;
  fiscal_year: string;
  is_sample: boolean;
  fetched_file_path?: string | null;
  extracted_text_path?: string | null;
  content_type?: string | null;
  file_size_bytes?: number | null;
  external_doc_id?: string | null;
};

export type CompanyDetailResponse = {
  company: CompanyProfile;
  latest_financial_metrics: FinancialMetrics | null;
  cre_signals: CRESignal[];
  score_breakdown: ScoreBreakdownResponse | null;
  pipeline_status?: PipelineStatus;
  documents: DocumentSummary[];
};

export type StructuredReportSection = {
  id: string;
  number: number;
  title: string;
  body: string;
  items: string[];
};

export type StructuredScoreComponent = {
  label: string;
  evaluation_target: string;
  evaluation_viewpoint: string;
  rationale: string;
  score_text: string;
  details: string[];
};

export type StructuredReport = {
  title: string;
  disclaimer: string;
  sections: StructuredReportSection[];
  score_components: StructuredScoreComponent[];
  documents: Array<Record<string, unknown>>;
  signals: Array<Record<string, unknown>>;
};

export type CompanyReportResponse = {
  company_id: number;
  title: string;
  generation_status: 'generated' | 'failed' | 'not_generated';
  generated_at: string;
  generated_by: string;
  signal_count: number;
  preview: string;
  markdown_content: string;
  structured_report?: StructuredReport;
};

export type PipelineConfigStatus = {
  fetch_enabled: boolean;
  dry_run: boolean;
  analysis_mode: 'mock' | 'openai' | string;
  effective_analysis_mode: 'mock' | 'openai' | string;
  edinet_api_key_configured: boolean;
  openai_api_key_configured: boolean;
  storage_dir: string;
};

export type PipelineStatus = {
  config: PipelineConfigStatus;
  latest_fetch_at: string | null;
  latest_fetch_status: string | null;
  latest_fetch_error: string | null;
  latest_analysis_at: string | null;
  latest_analysis_status: string | null;
  latest_analysis_error: string | null;
};

export type PipelineActionResponse = {
  company_id: number;
  status: string;
  pipeline: PipelineConfigStatus;
  latest_fetch_at?: string | null;
  latest_fetch_status?: string | null;
  latest_fetch_error?: string | null;
  latest_analysis_at?: string | null;
  latest_analysis_status?: string | null;
  latest_analysis_error?: string | null;
  created_signal_count?: number;
  result?: Record<string, unknown>;
  results?: Array<Record<string, unknown>>;
};
