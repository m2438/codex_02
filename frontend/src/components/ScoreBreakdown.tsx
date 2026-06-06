import type { ScoreBreakdownResponse } from '@/types/api';

const scoreLabels: Record<keyof ScoreBreakdownResponse['component_scores'], string> = {
  signal_score: 'CREシグナル',
  financial_score: '財務余力',
  strategic_event_score: '戦略イベント',
  fit_score: '提案適合度'
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

  const entries = Object.entries(score.component_scores) as Array<[
    keyof ScoreBreakdownResponse['component_scores'],
    number
  ]>;

  return (
    <div className="score-breakdown">
      <div className="score-breakdown__summary">
        <div>
          <p className="section-kicker">営業優先度スコア</p>
          <p className="score-breakdown__total">{score.total_score}</p>
        </div>
        <span className={`priority ${priorityClass(score.priority_label)}`}>優先度 {score.priority_label}</span>
      </div>
      <div className="score-bars">
        {entries.map(([key, value]) => (
          <div className="score-bar" key={key}>
            <div className="score-bar__label-row">
              <span>{scoreLabels[key]}</span>
              <strong>{value}</strong>
            </div>
            <div className="score-bar__track" aria-hidden="true">
              <span style={{ width: `${Math.min(value, 30) / 30 * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="recommendation-box">
        <p className="recommendation-box__label">推奨アクション</p>
        <p>{score.recommended_action}</p>
      </div>
      <p className="score-breakdown__explanation">{score.explanation}</p>
    </div>
  );
}
