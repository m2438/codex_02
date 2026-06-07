import type { ReactNode } from 'react';
import type { CompanyDetailResponse, CompanyReportResponse, FinancialMetricScales, StructuredReportSection } from '@/types/api';
import { SignalCard } from './SignalCard';
import { ScoreBreakdown } from './ScoreBreakdown';

const numberFormatter = new Intl.NumberFormat('ja-JP');
const defaultFinancialScales: FinancialMetricScales = {
  growthMinPct: -10,
  growthMaxPct: 20,
  marginMaxPct: 20,
  capexMaxOku: 5000,
  cashMaxOku: 30000
};

function dataSourceLabel(value: 'synthetic' | 'public_demo'): string {
  return value === 'public_demo' ? '公開情報ベース' : '合成デモデータ';
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
};

function MetricGauge({ label, valueText, minLabel, maxLabel, percent, zeroPercent }: MetricGaugeProps) {
  return (
    <div className="financial-metric-card">
      <div className="financial-metric-card__header"><span>{label}</span><strong>{valueText}</strong></div>
      <div className="metric-gauge" aria-label={`${label}: ${valueText}`}>
        {zeroPercent !== undefined ? <i className="metric-gauge__zero" style={{ left: `${clampPct(zeroPercent)}%` }} /> : null}
        <span style={{ width: `${clampPct(percent)}%` }} />
      </div>
      <div className="metric-gauge__scale"><span>{minLabel}</span><span>{maxLabel}</span></div>
    </div>
  );
}

type CompanyDetailProps = {
  detail: CompanyDetailResponse | null;
  report: CompanyReportResponse | null;
  financialScales?: FinancialMetricScales;
};

export function CompanyDetail({ detail, report, financialScales = defaultFinancialScales }: CompanyDetailProps) {
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
          <p className="section-kicker">企業詳細</p>
          <h2>{company.name}</h2>
          <p className="detail-panel__subtitle">{company.ticker} / {company.market} / {company.industry}</p>
          <span className={`data-source-badge data-source-badge--${company.data_source_type}`}>{dataSourceLabel(company.data_source_type)}</span>
        </div>
        <div className="profile-grid">
          <div><span>本社</span><strong>{company.headquarters_location}</strong></div>
          <div><span>従業員数</span><strong>{numberFormatter.format(company.employee_count)}人</strong></div>
          <div><span>売上高（{company.fiscal_year}）</span><strong>{formatMillionYenToOku(company.revenue)}</strong></div>
        </div>
      </div>

      <div className="panel caution-panel">
        <strong>公開情報ベースの営業仮説に関する注意</strong>
        <p>本分析は公開情報に基づく営業仮説であり、当該企業の正式なCRE方針や実際の提案機会を断定するものではありません。実営業では一次情報確認と個別ヒアリングによる検証が必要です。</p>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">最新財務メトリクス</p>
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
              />
              <MetricGauge
                label="営業利益率"
                valueText={`${metrics.operating_margin_pct.toFixed(1)}%`}
                minLabel="0%"
                maxLabel={`${financialScales.marginMaxPct}%`}
                percent={metrics.operating_margin_pct / financialScales.marginMaxPct * 100}
              />
              <MetricGauge
                label="設備投資額"
                valueText={formatMillionYenToOku(metrics.capex_amount)}
                minLabel="0億円"
                maxLabel={formatOku(financialScales.capexMaxOku)}
                percent={(metrics.capex_amount / 100) / financialScales.capexMaxOku * 100}
              />
              <MetricGauge
                label="現預金等"
                valueText={formatMillionYenToOku(metrics.cash_and_equivalents)}
                minLabel="0億円"
                maxLabel={formatOku(financialScales.cashMaxOku)}
                percent={(metrics.cash_and_equivalents / 100) / financialScales.cashMaxOku * 100}
              />
            </div>
          ) : <p className="empty-state">財務メトリクスは未登録です。</p>}
        </div>

        <div className="panel">
          <ScoreBreakdown score={score} />
        </div>
      </div>

      <div className="panel documents-panel">
        <div className="section-heading">
          <div>
            <p className="section-kicker">根拠資料</p>
            <h3>参照IR資料・出典URL</h3>
          </div>
          <span className="pill">{detail.documents.length}件</span>
        </div>
        <div className="document-list">
          {detail.documents.map((document) => (
            <article className="document-card" key={document.document_id}>
              <h4>{document.document_title ?? document.title}</h4>
              <p>{document.document_type} / FY{document.fiscal_year} / {document.source_name} / 言語: {languageLabel(document.document_language)}</p>
              {document.source_url ? <a href={document.source_url} target="_blank" rel="noreferrer">資料URLを開く</a> : <span>URLなし</span>}
              {document.source_note ? <p className="document-card__note">{document.source_note}</p> : null}
            </article>
          ))}
        </div>
      </div>

      <div className="panel report-panel">
        <div className="section-heading">
          <div>
            <p className="section-kicker">分析レポート</p>
            <h3>企業別CRE営業仮説レポート</h3>
          </div>
          <span className={`pill report-status report-status--${report?.generation_status ?? 'not_generated'}`}>
            {report?.generation_status === 'generated' ? '生成済み' : '未生成'}
          </span>
        </div>
        {report && structuredReport ? (
          <div className="rich-report">
            <div className="report-meta-card">
              <p>{renderInlineMarkdown(structuredReport.disclaimer)}</p>
              <dl>
                <div><dt>生成日時</dt><dd>{formatDateTime(report.generated_at)}</dd></div>
                <div><dt>根拠シグナル数</dt><dd>{report.signal_count}件</dd></div>
              </dl>
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
          <p className="empty-state">構造化レポートを取得できませんでした。バックエンドのレポートAPI設定を確認してください。</p>
        ) : (
          <p className="empty-state">レポートはまだ生成されていません。バックエンドのレポートAPI接続状態を確認してください。</p>
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
    </section>
  );
}
