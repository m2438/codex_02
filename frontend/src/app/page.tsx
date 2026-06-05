import { getHealth } from '@/lib/api';

export default async function Home() {
  const health = await getHealth();
  const modeLabel = health?.mode === 'openai' ? 'OpenAI APIモード' : 'モックモード';

  return (
    <main>
      <div className="container">
        <section className="hero">
          <p className="eyebrow">CRE CONSULTING SALES DEMO</p>
          <h1>CRE Sales Intelligence</h1>
          <p className="description">
            公開IR文書またはサンプル文書から、CRE戦略ニーズの兆候を整理し、営業優先度を可視化するためのローカルデモアプリケーションです。
          </p>
          <span className="badge">Phase 0: ヘルスチェック疎通</span>

          <div className="status-grid">
            <div className="status-card">
              <p className="status-label">バックエンド状態</p>
              <p className="status-value">{health?.status === 'ok' ? '接続済み' : '未接続'}</p>
            </div>
            <div className="status-card">
              <p className="status-label">AIモード</p>
              <p className="status-value">{modeLabel}</p>
            </div>
            <div className="status-card">
              <p className="status-label">データベース</p>
              <p className="status-value">{health?.database ?? '未確認'}</p>
            </div>
          </div>

          <div>
            <p className="status-label">次フェーズで追加する機能</p>
            <ul className="todo">
              <li>20社分のサンプル会社マスタとIR文書データ</li>
              <li>根拠テキスト付きCREシグナル抽出</li>
              <li>説明可能な営業優先度スコアリング</li>
              <li>日本語ダッシュボードとMarkdownレポート生成</li>
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
}
