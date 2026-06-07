import type { ScoreBreakdownResponse, ScoreComponentKey } from '@/types/api';

const scoreLabels: Record<ScoreComponentKey, string> = {
  signal_score: 'CREシグナル',
  financial_score: '財務・投資余力',
  strategic_event_score: '戦略イベント',
  fit_score: '提案適合度'
};

const componentOrder: ScoreComponentKey[] = ['signal_score', 'financial_score', 'strategic_event_score', 'fit_score'];

const fallbackMaxPoints: Record<ScoreComponentKey, number> = {
  signal_score: 35,
  financial_score: 25,
  strategic_event_score: 25,
  fit_score: 15
};

type ScoreBreakdownProps = {
  score: ScoreBreakdownResponse | null;
};

function priorityClass(priority: ScoreBreakdownResponse['priority_label']): string {
  if (priority === '高') return 'priority--high';
  if (priority === '中') return 'priority--medium';
  if (priority === '低') return 'priority--low';
  return 'priority--none';
}

export function ScoreBreakdown({ score }: ScoreBreakdownProps) {
  if (!score) {
    return <p className="empty-state">スコアは未評価です。</p>;
  }

  return (
    <div className="score-breakdown">
      <div className="score-breakdown__summary">
        <div>
          <p className="section-kicker">営業優先度スコア</p>
          <p className="score-breakdown__total">{score.total_score}<span>/100</span></p>
        </div>
        <span className={`priority ${priorityClass(score.priority_label)}`}>優先度 {score.priority_label}</span>
      </div>
      <div className="score-bars">
        {componentOrder.map((key) => {
          const detail = score.component_details?.[key];
          const value = detail?.score ?? score.component_scores[key];
          const maxPoints = detail?.max_points ?? fallbackMaxPoints[key];
          const reason = detail?.reason ?? `${scoreLabels[key]}を最大${maxPoints}点で評価しています。`;
          return (
            <div className="score-bar" key={key}>
              <div className="score-bar__label-row">
                <span>{scoreLabels[key]}</span>
                <strong>{value} / {maxPoints}点</strong>
              </div>
              <div className="score-bar__track" aria-hidden="true">
                <span style={{ width: `${Math.min(value, maxPoints) / maxPoints * 100}%` }} />
              </div>
              <p className="score-bar__reason">{reason}</p>
            </div>
          );
        })}
      </div>
      <div className="recommendation-box">
        <p className="recommendation-box__label">推奨アクション</p>
        <p>{score.recommended_action}</p>
      </div>
      <p className="score-breakdown__explanation">{score.explanation}</p>
    </div>
  );
}
