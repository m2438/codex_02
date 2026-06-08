'use client';

import { useState } from 'react';
import type { PipelineActionResponse, PipelineStatus } from '@/types/api';
import { postAnalyze, postDocumentFetch } from '@/lib/api';

function formatDateTime(value?: string | null): string {
  if (!value) return '未実行';
  return new Intl.DateTimeFormat('ja-JP', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Tokyo' }).format(new Date(value));
}

function analysisInputLabel(value?: string | null): string {
  const labels: Record<string, string> = {
    extracted_pdf_text: '取得済みPDFの抽出テキスト',
    existing_db_text: '保存済みIR本文',
    mock_seed_text: '登録済みサンプル本文'
  };
  return value ? labels[value] ?? '分析対象テキスト' : '未実行';
}

function analysisModeLabel(value?: string | null): string {
  return value === 'openai' ? 'AI分析' : 'ルールベース分析';
}

function statusLabel(value?: string | null): string {
  if (!value) return '未実行';
  const labels: Record<string, string> = { success: '完了', failed: '要確認', skipped: '見送り', dry_run: '事前確認', extract_failed: '取得済み・本文抽出要確認' };
  return labels[value] ?? value;
}

const fallbackConfig = {
  fetch_enabled: false,
  dry_run: true,
  analysis_mode: 'mock',
  effective_analysis_mode: 'mock',
  edinet_api_key_configured: false,
  openai_api_key_configured: false,
  storage_dir: '',
  edinet_lookback_days: 365
};

type Props = {
  companyId: number;
  initialStatus?: PipelineStatus;
  onRefresh?: () => Promise<PipelineStatus | undefined>;
};

export function IRPipelinePanel({ companyId, initialStatus, onRefresh }: Props) {
  const [status, setStatus] = useState<PipelineStatus | undefined>(initialStatus);
  const [lastResponse, setLastResponse] = useState<PipelineActionResponse | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  async function runAction(kind: 'manual' | 'analyze') {
    setRunning(kind);
    try {
      const response = kind === 'manual' ? await postDocumentFetch(companyId) : await postAnalyze(companyId);
      setLastResponse(response);
      if (response) {
        setStatus((current) => ({
          config: response.pipeline ?? current?.config ?? initialStatus?.config ?? fallbackConfig,
          latest_fetch_at: response.latest_fetch_at ?? current?.latest_fetch_at ?? null,
          latest_fetch_status: response.latest_fetch_status ?? current?.latest_fetch_status ?? null,
          latest_fetch_error: response.latest_fetch_error ?? current?.latest_fetch_error ?? null,
          latest_analysis_at: response.latest_analysis_at ?? current?.latest_analysis_at ?? null,
          latest_analysis_status: response.latest_analysis_status ?? current?.latest_analysis_status ?? null,
          latest_analysis_error: response.latest_analysis_error ?? current?.latest_analysis_error ?? null
        }));
      }
    } finally {
      const refreshedStatus = await onRefresh?.();
      if (refreshedStatus) setStatus(refreshedStatus);
      setRunning(null);
    }
  }

  const config = status?.config;
  const disabledMessage = !config?.fetch_enabled
    ? '資料取得は停止中です。登録済みの公開IR情報で確認できます。'
    : config.dry_run
      ? '資料取得は事前確認設定です。外部接続前の操作確認として利用できます。'
      : '公開IR資料とEDINETを対象に資料取得を実行できます。';

  return (
    <div className="panel ir-pipeline-panel">
      <div className="section-heading">
        <div>
          <p className="section-kicker">資料取得・分析実行</p>
          <h3>次に行う操作</h3>
        </div>
        <span className={`pill ir-mode ir-mode--${config?.dry_run ? 'dry' : config?.fetch_enabled ? 'enabled' : 'disabled'}`}>{disabledMessage}</span>
      </div>
      <div className="ir-status-grid">
        <div><span>EDINET接続</span><strong>{config?.edinet_api_key_configured ? '利用可能' : '未接続'}</strong></div>
        <div><span>AI分析接続</span><strong>{config?.openai_api_key_configured ? '利用可能' : '未接続'}</strong></div>
        <div><span>分析方式</span><strong>{analysisModeLabel(config?.effective_analysis_mode)}</strong></div>
        <div><span>EDINET検索期間</span><strong>過去{config?.edinet_lookback_days ?? 365}日</strong></div>
        <div><span>最新取得</span><strong>{formatDateTime(status?.latest_fetch_at)}</strong><em>{statusLabel(status?.latest_fetch_status)}</em></div>
        <div><span>最新分析</span><strong>{formatDateTime(status?.latest_analysis_at)}</strong><em>{statusLabel(status?.latest_analysis_status)}</em></div>
      </div>
      <div className="ir-actions">
        <button type="button" onClick={() => runAction('manual')} disabled={Boolean(running)}>{running === 'manual' ? '資料を取得しています...' : '4. 資料取得を実行'}</button>
        <button type="button" onClick={() => runAction('analyze')} disabled={Boolean(running)}>{running === 'analyze' ? '分析しています...' : '5. 分析実行'}</button>
      </div>
      {(status?.latest_fetch_error || status?.latest_analysis_error || lastResponse) ? (
        <div className="ir-result-box">
          {status?.latest_fetch_error ? <p><strong>資料取得の確認事項:</strong> {status.latest_fetch_error}</p> : null}
          {status?.latest_analysis_error ? <p><strong>分析実行の確認事項:</strong> {status.latest_analysis_error}</p> : null}
          {lastResponse ? <p><strong>直近実行:</strong> {statusLabel(lastResponse.status)} / {lastResponse.created_signal_count !== undefined ? `抽出シグナル ${lastResponse.created_signal_count}件` : '結果を更新しました'}</p> : null}
          {lastResponse?.analysis_input_source ? <p><strong>分析対象:</strong> {analysisInputLabel(lastResponse.analysis_input_source)}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
