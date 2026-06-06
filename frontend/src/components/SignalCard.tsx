import type { CRESignal } from '@/types/api';

const confidenceLabels: Record<CRESignal['confidence'], string> = {
  high: '高信頼',
  medium: '中信頼',
  low: '低信頼'
};

type SignalCardProps = {
  signal: CRESignal;
};

export function SignalCard({ signal }: SignalCardProps) {
  return (
    <article className="signal-card">
      <div className="signal-card__header">
        <div>
          <p className="signal-card__type">{signal.signal_type}</p>
          <h4>{signal.title}</h4>
        </div>
        <span className={`confidence confidence--${signal.confidence}`}>{confidenceLabels[signal.confidence]}</span>
      </div>
      <p className="signal-card__description">{signal.description}</p>
      <div className="evidence-box">
        <p className="evidence-box__label">根拠テキスト</p>
        <p>{signal.evidence_text}</p>
      </div>
      <dl className="signal-card__meta">
        <div>
          <dt>出典</dt>
          <dd>{signal.source_reference}</dd>
        </div>
        <div>
          <dt>信頼度理由</dt>
          <dd>{signal.confidence_reason}</dd>
        </div>
      </dl>
    </article>
  );
}
