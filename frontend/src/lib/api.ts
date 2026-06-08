import type { CompaniesResponse, CompanyDetailResponse, CompanyReportResponse, HealthResponse, PipelineActionResponse } from '@/types/api';

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

export async function getCompanyDocuments(companyId: number): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>(`/companies/${companyId}/documents`);
}

export async function getCompanyFetchRuns(companyId: number): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>(`/companies/${companyId}/fetch-runs`);
}

export async function getCompanyAnalysisRuns(companyId: number): Promise<Record<string, unknown> | null> {
  return fetchJson<Record<string, unknown>>(`/companies/${companyId}/analysis-runs`);
}


async function postJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST' });
    if (!response.ok) return null;
    return response.json() as Promise<T>;
  } catch {
    return null;
  }
}

export async function postDocumentFetch(companyId: number): Promise<PipelineActionResponse | null> {
  return postJson<PipelineActionResponse>(`/companies/${companyId}/documents/fetch`);
}

export async function postEdinetFetch(companyId: number): Promise<PipelineActionResponse | null> {
  return postJson<PipelineActionResponse>(`/companies/${companyId}/documents/fetch-edinet`);
}

export async function postAnalyze(companyId: number): Promise<PipelineActionResponse | null> {
  return postJson<PipelineActionResponse>(`/companies/${companyId}/analyze`);
}
