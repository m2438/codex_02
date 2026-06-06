import type { CompanyDetailResponse } from '@/types/api';
import { SignalCard } from './SignalCard';
import { ScoreBreakdown } from './ScoreBreakdown';

const numberFormatter = new Intl.NumberFormat('ja-JP');

function formatYenMillions(value: number): string {
  return `${numberFormatter.format(value)}百万円`;
}

type CompanyDetailProps = {
  detail: CompanyDetailResponse | null;
};

export function CompanyDetail({ detail }: CompanyDetailProps) {
  if (!detail) {
    return (
      <section className="panel detail-panel">
        <p className="empty-state">企業を選択すると、企業プロフィール、CREシグナル、スコア内訳を確認できます。</p>
      </section>
    );
  }

  const { company, latest_financial_metrics: metrics, score_breakdown: score } = detail;

  return (
    <section className="detail-panel">
      <div className="panel detail-panel__header">
        <div>
          <p className="section-kicker">企業詳細</p>
          <h2>{company.name}</h2>
          <p className="detail-panel__subtitle">{company.ticker} / {company.market} / {company.industry}</p>
        </div>
        <div className="profile-grid">
          <div><span>本社</span><strong>{company.headquarters_location}</strong></div>
          <div><span>従業員数</span><strong>{numberFormatter.format(company.employee_count)}人</strong></div>
          <div><span>売上高（{company.fiscal_year}）</span><strong>{formatYenMillions(company.revenue)}</strong></div>
        </div>
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
                <div><span>設備投資額</span><strong>{formatYenMillions(metrics.capex_amount)}</strong></div>
                <div><span>現預金等</span><strong>{formatYenMillions(metrics.cash_and_equivalents)}</strong></div>
              </div>
              <p className="note-box">{metrics.segment_change_note}</p>
            </>
          ) : (
            <p className="empty-state">財務メトリクスは未登録です。</p>
          )}
        </div>

        <div className="panel">
          <ScoreBreakdown score={score} />
        </div>
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
