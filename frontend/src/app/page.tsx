import { CompanyDetail } from '@/components/CompanyDetail';
import { CompanyRankTable } from '@/components/CompanyRankTable';
import { MetricCard } from '@/components/MetricCard';
import { getCompanies, getCompanyDetail, getCompanyReport, getHealth } from '@/lib/api';
import type { CompanyDetailResponse, CompanyReportResponse, CompanySummary, DataSourceType, FinancialMetricScales, PriorityLabel } from '@/types/api';

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

function latestUpdatedAt(details: CompanyDetailResponse[]): string | undefined {
  return details
    .map((detail) => detail.score_breakdown?.calculated_at)
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];
}

function roundedCeil(value: number, step: number): number {
  return Math.max(step, Math.ceil(value / step) * step);
}

function buildFinancialScales(details: CompanyDetailResponse[]): FinancialMetricScales {
  const metrics = details.map((detail) => detail.latest_financial_metrics).filter((metric): metric is NonNullable<typeof metric> => Boolean(metric));
  const maxMargin = Math.max(20, ...metrics.map((metric) => metric.operating_margin_pct));
  const maxCapexOku = Math.max(1000, ...metrics.map((metric) => metric.capex_amount / 100));
  const maxCashOku = Math.max(10000, ...metrics.map((metric) => metric.cash_and_equivalents / 100));

  return {
    growthMinPct: -10,
    growthMaxPct: 20,
    marginMaxPct: roundedCeil(maxMargin, 5),
    capexMaxOku: roundedCeil(maxCapexOku, 1000),
    cashMaxOku: roundedCeil(maxCashOku, 5000)
  };
}

type HomeProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function Home({ searchParams }: HomeProps) {
  const [health, companiesResponse] = await Promise.all([getHealth(), getCompanies()]);
  const companies = companiesResponse?.items ?? [];
  const selectedIndustry = firstParam(searchParams?.industry) ?? 'すべて';
  const selectedPriority = (firstParam(searchParams?.priority) ?? 'すべて') as PriorityLabel | 'すべて';
  const selectedDataSource = (firstParam(searchParams?.dataSource) ?? 'すべて') as DataSourceType | 'すべて';
  const selectedCompanyIdParam = Number(firstParam(searchParams?.companyId));

  const industries = ['すべて', ...Array.from(new Set(companies.map((company) => company.industry))).sort((a, b) => a.localeCompare(b, 'ja'))];
  const filteredCompanies = sortCompanies(companies).filter((company) => {
    const industryMatches = selectedIndustry === 'すべて' || company.industry === selectedIndustry;
    const priorityMatches = selectedPriority === 'すべて' || company.priority_label === selectedPriority;
    const dataSourceMatches = selectedDataSource === 'すべて' || company.data_source_type === selectedDataSource;
    return industryMatches && priorityMatches && dataSourceMatches;
  });
  const selectedCompany = filteredCompanies.find((company) => company.company_id === selectedCompanyIdParam) ?? filteredCompanies[0];
  const allDetails = (await Promise.all(companies.map((company) => getCompanyDetail(company.company_id)))).filter(
    (detail): detail is CompanyDetailResponse => Boolean(detail)
  );
  const selectedDetail = allDetails.find((detail) => detail.company.company_id === selectedCompany?.company_id) ?? null;
  const [selectedReport]: [CompanyReportResponse | null] = await Promise.all([
    selectedCompany ? getCompanyReport(selectedCompany.company_id) : Promise.resolve(null)
  ]);

  const modeLabel = health?.mode === 'openai' ? 'OpenAI APIモード' : 'モックモード';
  const financialScales = buildFinancialScales(allDetails);

  return (
    <main>
      <div className="container dashboard">
        <section className="hero dashboard-hero">
          <div>
            <p className="eyebrow">CRE CONSULTING SALES BI</p>
            <h1>CRE営業支援BI</h1>
            <p className="description">
              日本国内の上場企業について、日本語の公開IR資料に基づくCRE営業仮説、スコアリング理由、根拠資料を確認する営業支援ダッシュボードです。
            </p>
          </div>
          <div className="hero-status">
            <span className="badge">公開情報ベース分析</span>
            <span className="connection">バックエンド: {health?.status === 'ok' ? '接続済み' : '未接続'} / {modeLabel}</span>
          </div>
        </section>

        <section className="metric-grid metric-grid--compact" aria-label="ダッシュボード指標">
          <MetricCard label="対象企業数" value={`${companiesResponse?.total ?? 0}社`} helper="現在のランキング対象" tone="primary" />
          <MetricCard label="最新更新" value={formatDateTime(latestUpdatedAt(allDetails))} helper="スコア計算時刻（JST）" />
        </section>

        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">企業ランキング</p>
              <h2>営業優先度順のターゲットリスト</h2>
              <p className="result-count">表示中: {filteredCompanies.length}社</p>
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
            dataSource={selectedDataSource}
          />
        </section>

        <CompanyDetail detail={selectedDetail} report={selectedReport} financialScales={financialScales} />
      </div>
    </main>
  );
}
