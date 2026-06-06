import Link from 'next/link';
import type { CompanySummary, PriorityLabel } from '@/types/api';

type CompanyRankTableProps = {
  companies: CompanySummary[];
  selectedCompanyId?: number;
  industry?: string;
  priority?: PriorityLabel | 'すべて';
};

function formatScore(score: number | null): string {
  return score === null ? '未評価' : `${score}点`;
}

function priorityClass(priority: PriorityLabel): string {
  if (priority === '高') return 'priority--high';
  if (priority === '中') return 'priority--medium';
  if (priority === '低') return 'priority--low';
  return 'priority--none';
}

export function CompanyRankTable({ companies, selectedCompanyId, industry, priority }: CompanyRankTableProps) {
  if (companies.length === 0) {
    return <p className="empty-state">条件に一致する企業がありません。フィルター条件を変更してください。</p>;
  }

  return (
    <div className="table-wrap">
      <table className="rank-table">
        <thead>
          <tr>
            <th>順位</th>
            <th>企業</th>
            <th>業種</th>
            <th>市場</th>
            <th>優先度</th>
            <th>スコア</th>
            <th>シグナル</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company, index) => {
            const params = new URLSearchParams();
            params.set('companyId', String(company.company_id));
            if (industry) params.set('industry', industry);
            if (priority && priority !== 'すべて') params.set('priority', priority);

            return (
              <tr className={company.company_id === selectedCompanyId ? 'is-selected' : undefined} key={company.company_id}>
                <td>{index + 1}</td>
                <td>
                  <Link className="company-link" href={`/?${params.toString()}`}>
                    <strong>{company.name}</strong>
                    <span>{company.ticker}</span>
                  </Link>
                </td>
                <td>{company.industry}</td>
                <td>{company.market}</td>
                <td><span className={`priority ${priorityClass(company.priority_label)}`}>{company.priority_label}</span></td>
                <td className="rank-table__score">{formatScore(company.total_score)}</td>
                <td>{company.signal_count}件</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
