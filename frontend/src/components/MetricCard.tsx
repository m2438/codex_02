type MetricCardProps = {
  label: string;
  value: string;
  helper?: string;
  tone?: 'default' | 'primary' | 'success';
};

export function MetricCard({ label, value, helper, tone = 'default' }: MetricCardProps) {
  return (
    <div className={`metric-card metric-card--${tone}`}>
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__value">{value}</p>
      {helper ? <p className="metric-card__helper">{helper}</p> : null}
    </div>
  );
}
