import type { CompanyDetailResponse, CompanyReportResponse, StructuredReportSection } from '@/types/api';
import { SignalCard } from './SignalCard';
import { ScoreBreakdown } from './ScoreBreakdown';

const numberFormatter = new Intl.NumberFormat('ja-JP');

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

type CompanyDetailProps = {
  detail: CompanyDetailResponse | null;
  report: CompanyReportResponse | null;
};

export function CompanyDetail({ detail, report }: CompanyDetailProps) {
  if (!detail) {
    return (
      <section className="panel detail-panel">
        <p className="empty-state">企業を選択すると、企業プロフィール、CREシグナル、スコア内訳を確認できます。</p>
      </section>
    );
  }

  const { company, latest_financial_metrics: metrics, score_breakdown: score } = detail;
  const structuredReport = report?.structured_report;
  const scoreSection = structuredReport?.sections.find((section) => section.id === 'score_details');
  const regularSections = structuredReport?.sections.filter((section) => section.id !== 'score_details') ?? [];

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
        <p>本分析は公開情報に基づく営業仮説であり、当該企業の正式なCRE方針や実際の提案機会を断定するものではありません。</p>
        <p>実営業に使用する場合は、一次情報の再確認および個別ヒアリングによる検証が必要です。</p>
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
            <>
              <div className="financial-grid">
                <div><span>売上成長率</span><strong>{metrics.revenue_growth_pct.toFixed(1)}%</strong></div>
                <div><span>営業利益率</span><strong>{metrics.operating_margin_pct.toFixed(1)}%</strong></div>
                <div><span>設備投資額</span><strong>{formatMillionYenToOku(metrics.capex_amount)}</strong></div>
                <div><span>現預金等</span><strong>{formatMillionYenToOku(metrics.cash_and_equivalents)}</strong></div>
              </div>
              <p className="note-box">{metrics.segment_change_note}</p>
            </>
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
              <p>{structuredReport.disclaimer}</p>
              <dl>
                <div><dt>生成日時</dt><dd>{formatDateTime(report.generated_at)}</dd></div>
                <div><dt>根拠シグナル数</dt><dd>{report.signal_count}件</dd></div>
              </dl>
            </div>

            {scoreSection ? (
              <article className="report-section report-section--score">
                <div className="report-section__heading"><span>{scoreSection.number}</span><h4>{scoreSection.title}</h4></div>
                <div className="score-component-grid">
                  {structuredReport.score_components.map((component) => (
                    <div className="score-component-card" key={component.label}>
                      <div className="score-component-card__header"><strong>{component.label}</strong><span>{component.score_text}</span></div>
                      <ul>{component.details.map((detailItem) => <li key={detailItem}>{detailItem}</li>)}</ul>
                    </div>
                  ))}
                </div>
              </article>
            ) : null}

            <div className="report-section-grid">
              {regularSections.map((section) => (
                <article className={`report-section${sectionTone(section)}`} key={section.id}>
                  <div className="report-section__heading"><span>{section.number}</span><h4>{section.title}</h4></div>
                  {section.items.length > 0 ? <ul>{section.items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{section.body}</p>}
                </article>
              ))}
            </div>
          </div>
        ) : report ? (
          <pre className="markdown-report">{report.markdown_content}</pre>
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
