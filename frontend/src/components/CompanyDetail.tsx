'use client';

import { useCallback, useEffect, useState, type ReactNode } from 'react';
import type { CompanyDetailResponse, CompanyReportResponse, FinancialMetricScales, PipelineStatus, StructuredReportSection } from '@/types/api';
import { SignalCard } from './SignalCard';
import { ScoreBreakdown } from './ScoreBreakdown';
import { IRPipelinePanel } from './IRPipelinePanel';
import { getCompanyAnalysisRuns, getCompanyDetail, getCompanyDocuments, getCompanyFetchRuns, getCompanyReport } from '@/lib/api';

const numberFormatter = new Intl.NumberFormat('ja-JP');
const defaultFinancialScales: FinancialMetricScales = {
  growthMinPct: -10,
  growthMaxPct: 20,
  marginMaxPct: 20,
  capexMaxOku: 5000,
  cashMaxOku: 100000
};

function dataSourceLabel(value: 'synthetic' | 'public_demo'): string {
  return value === 'public_demo' ? '公開IR情報' : '参考データ';
}

function languageLabel(value?: string): string {
  return value === 'ja' ? '日本語' : value ? value.toUpperCase() : '未設定';
}

function formatMillionYenToOku(value: number): string {
  const oku = value / 100;
  if (oku >= 10000) return `${(oku / 10000).toFixed(1)}兆円`;
  return `${numberFormatter.format(Math.round(oku))}億円`;
}

function formatOku(value: number): string {
  if (value >= 10000) return `${(value / 10000).toFixed(1)}兆円`;
  return `${numberFormatter.format(Math.round(value))}億円`;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Tokyo'
  }).format(new Date(value));
}

function sectionTone(section: StructuredReportSection): string {
  if (section.id === 'caveats') return ' report-section--caution';
  if (section.id === 'evidence') return ' report-section--evidence';
  if (section.id === 'score_details') return ' report-section--score';
  return '';
}

function renderInlineMarkdown(value: string): ReactNode[] {
  return value.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part.replaceAll('**', '');
  });
}

function sortedSections(sections: StructuredReportSection[]): StructuredReportSection[] {
  return [...sections].sort((a, b) => a.number - b.number);
}

function clampPct(value: number): number {
  return Math.max(0, Math.min(100, value));
}

type MetricGaugeProps = {
  label: string;
  valueText: string;
  minLabel: string;
  maxLabel: string;
  percent: number;
  zeroPercent?: number;
  midpointLabel?: string;
};

function MetricGauge({ label, valueText, minLabel, maxLabel, percent, zeroPercent, midpointLabel }: MetricGaugeProps) {
  return (
    <div className="financial-metric-card">
      <div className="financial-metric-card__header"><span>{label}</span><strong>{valueText}</strong></div>
      <div className="metric-gauge" aria-label={`${label}: ${valueText}`}>
        <i className="metric-gauge__tick metric-gauge__tick--start" />
        <i className="metric-gauge__tick metric-gauge__tick--middle" />
        <i className="metric-gauge__tick metric-gauge__tick--end" />
        {zeroPercent !== undefined ? <i className="metric-gauge__zero" style={{ left: `${clampPct(zeroPercent)}%` }} /> : null}
        <span style={{ width: `${clampPct(percent)}%` }} />
      </div>
      <div className="metric-gauge__scale"><span>{minLabel}</span><span>{midpointLabel ?? '中間'}</span><span>{maxLabel}</span></div>
    </div>
  );
}

type CompanyDetailProps = {
  detail: CompanyDetailResponse | null;
  report: CompanyReportResponse | null;
  financialScales?: FinancialMetricScales;
};

export function CompanyDetail({ detail, report, financialScales = defaultFinancialScales }: CompanyDetailProps) {
  const [currentDetail, setCurrentDetail] = useState(detail);
  const [currentReport, setCurrentReport] = useState(report);

  useEffect(() => {
    setCurrentDetail(detail);
    setCurrentReport(report);
  }, [detail, report]);

  const refreshCompanyData = useCallback(async (): Promise<PipelineStatus | undefined> => {
    const companyId = currentDetail?.company.company_id ?? detail?.company.company_id;
    if (!companyId) return undefined;
    const [nextDetail, nextReport] = await Promise.all([
      getCompanyDetail(companyId),
      getCompanyReport(companyId),
      getCompanyDocuments(companyId),
      getCompanyFetchRuns(companyId),
      getCompanyAnalysisRuns(companyId)
    ]);
    if (nextDetail) setCurrentDetail(nextDetail);
    if (nextReport) setCurrentReport(nextReport);
    return nextDetail?.pipeline_status;
  }, [currentDetail?.company.company_id, detail?.company.company_id]);

  detail = currentDetail;
  report = currentReport;

  if (!detail) {
    return (
      <section className="panel detail-panel">
        <p className="empty-state">企業を選択すると、企業プロフィール、CREシグナル、スコア内訳を確認できます。</p>
      </section>
    );
  }

  const { company, latest_financial_metrics: metrics, score_breakdown: score } = detail;
  const structuredReport = report?.structured_report;
  const sections = structuredReport ? sortedSections(structuredReport.sections) : [];

  return (
    <section className="detail-panel">
      <div className="panel detail-panel__header">
        <div>
          <p className="section-kicker">1. 企業を選択</p>
          <h2>{company.name}</h2>
          <p className="detail-panel__subtitle">{company.ticker} / {company.market} / {company.industry} / EDINET: {company.edinet_code ?? '未登録'}</p>
          <span className={`data-source-badge data-source-badge--${company.data_source_type}`}>{dataSourceLabel(company.data_source_type)}</span>
        </div>
        <div className="profile-grid">
          <div><span>本社</span><strong>{company.headquarters_location}</strong></div>
          <div><span>従業員数</span><strong>{numberFormatter.format(company.employee_count)}人</strong></div>
          <div><span>売上高（{company.fiscal_year}）</span><strong>{formatMillionYenToOku(company.revenue)}</strong></div>
        </div>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">2. 財務関連指標</p>
              <h3>投資余力と事業変化</h3>
            </div>
            {metrics ? <span className="pill">FY{metrics.fiscal_year}</span> : null}
          </div>
          {metrics ? (
            <div className="financial-grid">
              <MetricGauge
                label="売上成長率"
                valueText={`${metrics.revenue_growth_pct.toFixed(1)}%`}
                minLabel={`${financialScales.growthMinPct}%`}
                maxLabel={`${financialScales.growthMaxPct}%`}
                percent={(metrics.revenue_growth_pct - financialScales.growthMinPct) / (financialScales.growthMaxPct - financialScales.growthMinPct) * 100}
                zeroPercent={(0 - financialScales.growthMinPct) / (financialScales.growthMaxPct - financialScales.growthMinPct) * 100}
                midpointLabel="0%"
              />
              <MetricGauge
                label="営業利益率"
                valueText={`${metrics.operating_margin_pct.toFixed(1)}%`}
                minLabel="0%"
                maxLabel={`${financialScales.marginMaxPct}%`}
                percent={metrics.operating_margin_pct / financialScales.marginMaxPct * 100}
                midpointLabel={`${financialScales.marginMaxPct / 2}%`}
              />
              <MetricGauge
                label="設備投資額"
                valueText={formatMillionYenToOku(metrics.capex_amount)}
                minLabel="0億円"
                maxLabel={formatOku(financialScales.capexMaxOku)}
                percent={(metrics.capex_amount / 100) / financialScales.capexMaxOku * 100}
                midpointLabel={formatOku(financialScales.capexMaxOku / 2)}
              />
              <MetricGauge
                label="現預金等"
                valueText={formatMillionYenToOku(metrics.cash_and_equivalents)}
                minLabel="0億円"
                maxLabel={formatOku(financialScales.cashMaxOku)}
                percent={(metrics.cash_and_equivalents / 100) / financialScales.cashMaxOku * 100}
                midpointLabel={formatOku(financialScales.cashMaxOku / 2)}
              />
            </div>
          ) : <p className="empty-state">財務メトリクスは未登録です。</p>}
        </div>

        <div className="panel">
          <ScoreBreakdown score={score} />
        </div>
      </div>

      <IRPipelinePanel companyId={company.company_id} initialStatus={detail.pipeline_status} onRefresh={refreshCompanyData} />

      <div className="panel report-panel">
        <div className="section-heading">
          <div>
            <p className="section-kicker">6. 分析レポート</p>
            <h3>企業別CRE営業仮説レポート</h3>
          </div>
          <span className={`pill report-status report-status--${report?.generation_status ?? 'not_generated'}`}>
            {report?.generation_status === 'generated' ? '生成済み' : '未生成'}
          </span>
        </div>
        {report && structuredReport ? (
          <div className="rich-report">
            <div className="report-meta-line" aria-label="分析レポートのメタ情報">
              <span>生成日時: <strong>{formatDateTime(report.generated_at)}</strong></span>
              <span>根拠シグナル数: <strong>{report.signal_count}件</strong></span>
            </div>

            <div className="report-section-grid">
              {sections.map((section) => section.id === 'score_details' ? (
                <article className={`report-section${sectionTone(section)}`} key={section.id}>
                  <div className="report-section__heading"><span>{section.number}</span><h4>{section.title}</h4></div>
                  <div className="score-detail-table-wrap">
                    <table className="score-detail-table">
                      <thead>
                        <tr>
                          <th>評価対象</th>
                          <th>評価観点</th>
                          <th>根拠・判断理由</th>
                          <th>点数/満点</th>
                        </tr>
                      </thead>
                      <tbody>
                        {structuredReport.score_components.map((component) => (
                          <tr key={component.label}>
                            <th><strong>{component.label}</strong><span>{renderInlineMarkdown(component.evaluation_target)}</span></th>
                            <td>{renderInlineMarkdown(component.evaluation_viewpoint)}</td>
                            <td>{renderInlineMarkdown(component.rationale)}</td>
                            <td><strong>{component.score_text}</strong></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>
              ) : (
                <article className={`report-section${sectionTone(section)}`} key={section.id}>
                  <div className="report-section__heading"><span>{section.number}</span><h4>{section.title}</h4></div>
                  {section.items.length > 0 ? <ul>{section.items.map((item) => <li key={item}>{renderInlineMarkdown(item)}</li>)}</ul> : <p>{renderInlineMarkdown(section.body)}</p>}
                </article>
              ))}
            </div>
          </div>
        ) : report ? (
          <p className="empty-state">分析レポートの表示に必要な構造化データを取得できませんでした。少し時間を置いて再読み込みしてください。</p>
        ) : (
          <p className="empty-state">分析レポートはまだ生成されていません。「分析実行」後にこの欄へ章立てで表示されます。</p>
        )}
      </div>

      <div className="panel">
        <div className="section-heading">
          <div>
            <p className="section-kicker">CREシグナル</p>
            <h3>根拠付き営業仮説</h3>
          </div>
          <span className="pill">{detail.cre_signals.length}件</span>
        </div>
        <div className="signal-list">
          {detail.cre_signals.map((signal) => <SignalCard key={signal.signal_id} signal={signal} />)}
        </div>
      </div>

      <div className="panel documents-panel">
        <div className="section-heading">
          <div>
            <p className="section-kicker">7. 根拠資料</p>
            <h3>参照IR資料・出典URL</h3>
          </div>
          <span className="pill">{detail.documents.length}件</span>
        </div>
        <div className="document-list">
          {detail.documents.map((document) => (
            <article className="document-card" key={document.document_id}>
              <h4>{document.document_title ?? document.title}</h4>
              <p>{document.document_type} / FY{document.fiscal_year} / {document.source_name} / 言語: {languageLabel(document.document_language)}</p>
              {document.source_url?.startsWith('http') ? <a href={document.source_url} target="_blank" rel="noreferrer">資料URLを開く</a> : document.external_doc_id ? <span>EDINET docID: {document.external_doc_id}</span> : <span>URLなし</span>}
              <small>取得状況: {document.fetched_file_path ? '資料取得済み' : '未取得'} / 本文抽出: {document.extracted_text_path ? '抽出済み' : '未抽出'}</small>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
