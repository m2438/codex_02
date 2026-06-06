export type PriorityLabel = '高' | '中' | '低' | '未評価';
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

export type ScoreBreakdownResponse = {
  total_score: number;
  priority_label: PriorityLabel;
  component_scores: {
    signal_score: number;
    financial_score: number;
    strategic_event_score: number;
    fit_score: number;
  };
  explanation: string;
  recommended_action: string;
  calculated_at: string;
};

export type DocumentSummary = {
  document_id: number;
  document_type: string;
  title: string;
  source_name: string;
  published_date: string | null;
  fiscal_year: string;
  is_sample: boolean;
};

export type CompanyDetailResponse = {
  company: CompanyProfile;
  latest_financial_metrics: FinancialMetrics | null;
  cre_signals: CRESignal[];
  score_breakdown: ScoreBreakdownResponse | null;
  documents: DocumentSummary[];
};
