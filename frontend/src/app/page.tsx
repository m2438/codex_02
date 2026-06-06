import { CompanyDetail } from '@/components/CompanyDetail';
import { CompanyRankTable } from '@/components/CompanyRankTable';
import { MetricCard } from '@/components/MetricCard';
import { getCompanies, getCompanyDetail, getHealth } from '@/lib/api';
import type { CompanyDetailResponse, CompanySummary, PriorityLabel } from '@/types/api';

const priorityOrder: Record<string, number> = { 高: 3, 中: 2, 低: 1, 未評価: 0 };
const priorityOptions: Array<PriorityLabel | 'すべて'> = ['すべて', '高', '中', '低'];

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function formatDateTime(value?: string): string {
  if (!value) return '未取得';
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Tokyo'
  }).format(new Date(value));
}

function sortCompanies(companies: CompanySummary[]): CompanySummary[] {
  return [...companies].sort((a, b) => {
    const scoreDiff = (b.total_score ?? -1) - (a.total_score ?? -1);
    if (scoreDiff !== 0) return scoreDiff;
    return (priorityOrder[b.priority_label] ?? 0) - (priorityOrder[a.priority_label] ?? 0);
  });
}

async function getLatestUpdatedAt(companies: CompanySummary[]): Promise<string | undefined> {
  const details = await Promise.all(companies.map((company) => getCompanyDetail(company.company_id)));
  return details
    .map((detail) => detail?.score_breakdown?.calculated_at)
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];
}

type HomeProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function Home({ searchParams }: HomeProps) {
  const [health, companiesResponse] = await Promise.all([getHealth(), getCompanies()]);
  const companies = companiesResponse?.items ?? [];
  const selectedIndustry = firstParam(searchParams?.industry) ?? 'すべて';
  const selectedPriority = (firstParam(searchParams?.priority) ?? 'すべて') as PriorityLabel | 'すべて';
  const selectedCompanyIdParam = Number(firstParam(searchParams?.companyId));

  const industries = ['すべて', ...Array.from(new Set(companies.map((company) => company.industry))).sort((a, b) => a.localeCompare(b, 'ja'))];
  const filteredCompanies = sortCompanies(companies).filter((company) => {
    const industryMatches = selectedIndustry === 'すべて' || company.industry === selectedIndustry;
    const priorityMatches = selectedPriority === 'すべて' || company.priority_label === selectedPriority;
    return industryMatches && priorityMatches;
  });
  const selectedCompany = filteredCompanies.find((company) => company.company_id === selectedCompanyIdParam) ?? filteredCompanies[0];
  const [selectedDetail, latestUpdatedAt]: [CompanyDetailResponse | null, string | undefined] = await Promise.all([
    selectedCompany ? getCompanyDetail(selectedCompany.company_id) : Promise.resolve(null),
    getLatestUpdatedAt(companies)
  ]);

  const highPriorityCount = companies.filter((company) => company.priority_label === '高').length;
  const modeLabel = health?.mode === 'openai' ? 'OpenAI APIモード' : 'モックモード';

  return (
    <main>
      <div className="container dashboard">
        <section className="hero dashboard-hero">
          <div>
            <p className="eyebrow">CRE CONSULTING SALES DEMO</p>
            <h1>CRE Sales Intelligence Dashboard</h1>
            <p className="description">
              Phase 1 APIのサンプル企業・CREシグナル・スコアを利用し、CREコンサルティング営業の優先順位と提案仮説を日本語で確認するダッシュボードです。
            </p>
          </div>
          <div className="hero-status">
            <span className="badge">Phase 2: フロントエンドダッシュボード</span>
            <span className="connection">バックエンド: {health?.status === 'ok' ? '接続済み' : '未接続'} / {modeLabel}</span>
          </div>
        </section>

        <section className="metric-grid" aria-label="ダッシュボード指標">
          <MetricCard label="対象企業数" value={`${companiesResponse?.total ?? 0}社`} helper="Phase 1シードデータ" tone="primary" />
          <MetricCard label="高優先度企業" value={`${highPriorityCount}社`} helper="優先度ラベルが「高」の企業" tone="success" />
          <MetricCard label="最新更新" value={formatDateTime(latestUpdatedAt)} helper="スコア計算時刻（JST）" />
        </section>

        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">企業ランキング</p>
              <h2>営業優先度順のターゲットリスト</h2>
            </div>
            <form className="filters">
              <label>
                業種
                <select name="industry" defaultValue={selectedIndustry}>
                  {industries.map((industry) => <option key={industry} value={industry}>{industry}</option>)}
                </select>
              </label>
              <label>
                優先度
                <select name="priority" defaultValue={selectedPriority}>
                  {priorityOptions.map((priority) => <option key={priority} value={priority}>{priority}</option>)}
                </select>
              </label>
              <button type="submit">絞り込み</button>
            </form>
          </div>
          <CompanyRankTable
            companies={filteredCompanies}
            selectedCompanyId={selectedCompany?.company_id}
            industry={selectedIndustry === 'すべて' ? undefined : selectedIndustry}
            priority={selectedPriority}
          />
        </section>

        <CompanyDetail detail={selectedDetail} />
      </div>
    </main>
  );
}
