'use client';

import { useState } from 'react';
import type { PipelineActionResponse, PipelineStatus } from '@/types/api';
import { postAnalyze, postDocumentFetch, postEdinetFetch } from '@/lib/api';

function formatDateTime(value?: string | null): string {
  if (!value) return '未実行';
  return new Intl.DateTimeFormat('ja-JP', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Tokyo' }).format(new Date(value));
}

function statusLabel(value?: string | null): string {
  if (!value) return '未実行';
  const labels: Record<string, string> = { success: '成功', failed: '失敗', skipped: 'スキップ', dry_run: 'dry-run' };
  return labels[value] ?? value;
}

type Props = {
  companyId: number;
  initialStatus?: PipelineStatus;
};

export function IRPipelinePanel({ companyId, initialStatus }: Props) {
  const [status, setStatus] = useState<PipelineStatus | undefined>(initialStatus);
  const [lastResponse, setLastResponse] = useState<PipelineActionResponse | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  async function runAction(kind: 'manual' | 'edinet' | 'analyze') {
    setRunning(kind);
    const response = kind === 'manual' ? await postDocumentFetch(companyId) : kind === 'edinet' ? await postEdinetFetch(companyId) : await postAnalyze(companyId);
    setLastResponse(response);
    if (response) {
      setStatus((current) => ({
        config: response.pipeline ?? current?.config ?? initialStatus!.config,
        latest_fetch_at: response.latest_fetch_at ?? current?.latest_fetch_at ?? null,
        latest_fetch_status: response.latest_fetch_status ?? current?.latest_fetch_status ?? null,
        latest_fetch_error: response.latest_fetch_error ?? current?.latest_fetch_error ?? null,
        latest_analysis_at: response.latest_analysis_at ?? current?.latest_analysis_at ?? null,
        latest_analysis_status: response.latest_analysis_status ?? current?.latest_analysis_status ?? null,
        latest_analysis_error: response.latest_analysis_error ?? current?.latest_analysis_error ?? null
      }));
    }
    setRunning(null);
  }

  const config = status?.config;
  const disabledMessage = !config?.fetch_enabled ? '外部取得は無効です（IR_FETCH_ENABLED=false）。既存public_demoデータで表示します。' : config.dry_run ? 'dry-runです。外部API・外部URLには接続せず実行予定のみ返します。' : '外部取得が有効です。公開IR URLとEDINETのみを対象にします。';

  return (
    <div className="panel ir-pipeline-panel">
      <div className="section-heading">
        <div>
          <p className="section-kicker">IR資料取得・分析</p>
          <h3>Phase 4B 操作パネル</h3>
          <p className="ir-pipeline-panel__note">公開情報に基づく営業仮説生成用です。企業IRサイト全体のクロールは行いません。</p>
        </div>
        <span className={`pill ir-mode ir-mode--${config?.dry_run ? 'dry' : config?.fetch_enabled ? 'enabled' : 'disabled'}`}>{disabledMessage}</span>
      </div>
      <div className="ir-status-grid">
        <div><span>EDINET APIキー</span><strong>{config?.edinet_api_key_configured ? '設定済み' : '未設定'}</strong></div>
        <div><span>OpenAI APIキー</span><strong>{config?.openai_api_key_configured ? '設定済み' : '未設定'}</strong></div>
        <div><span>分析モード</span><strong>{config?.effective_analysis_mode ?? 'mock'}</strong></div>
        <div><span>最新取得</span><strong>{formatDateTime(status?.latest_fetch_at)}</strong><em>{statusLabel(status?.latest_fetch_status)}</em></div>
        <div><span>最新分析</span><strong>{formatDateTime(status?.latest_analysis_at)}</strong><em>{statusLabel(status?.latest_analysis_status)}</em></div>
      </div>
      <div className="ir-actions">
        <button type="button" onClick={() => runAction('manual')} disabled={Boolean(running)}>{running === 'manual' ? '取得中...' : '資料取得'}</button>
        <button type="button" onClick={() => runAction('edinet')} disabled={Boolean(running)}>{running === 'edinet' ? '取得中...' : 'EDINET取得'}</button>
        <button type="button" onClick={() => runAction('analyze')} disabled={Boolean(running)}>{running === 'analyze' ? '分析中...' : '分析実行'}</button>
      </div>
      {(status?.latest_fetch_error || status?.latest_analysis_error || lastResponse) ? (
        <div className="ir-result-box">
          {status?.latest_fetch_error ? <p><strong>取得エラー:</strong> {status.latest_fetch_error}</p> : null}
          {status?.latest_analysis_error ? <p><strong>分析メッセージ:</strong> {status.latest_analysis_error}</p> : null}
          {lastResponse ? <p><strong>直近実行:</strong> {statusLabel(lastResponse.status)} / {lastResponse.created_signal_count !== undefined ? `生成シグナル ${lastResponse.created_signal_count}件` : 'レスポンス取得済み'}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
