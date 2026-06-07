import type { CompaniesResponse, CompanyDetailResponse, CompanyReportResponse, HealthResponse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api';

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: 'no-store'
    });

    if (!response.ok) {
      return null;
    }

    return response.json() as Promise<T>;
  } catch {
    return null;
  }
}

export async function getHealth(): Promise<HealthResponse | null> {
  return fetchJson<HealthResponse>('/health');
}

export async function getCompanies(): Promise<CompaniesResponse | null> {
  return fetchJson<CompaniesResponse>('/companies');
}

export async function getCompanyDetail(companyId: number): Promise<CompanyDetailResponse | null> {
  return fetchJson<CompanyDetailResponse>(`/companies/${companyId}`);
}

export async function getCompanyReport(companyId: number): Promise<CompanyReportResponse | null> {
  return fetchJson<CompanyReportResponse>(`/companies/${companyId}/report`);
}
