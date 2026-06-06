# CRE Sales Intelligence

CRE Sales Intelligence は、CRE コンサルティング営業チーム向けのローカルデモアプリケーションです。公開 IR 文書またはサンプル文書から CRE 戦略ニーズの兆候を整理し、営業優先度を可視化することを目的としています。

> Phase 1 では FastAPI / SQLite / SQLAlchemy によるデータモデル、20 社分のサンプル上場企業、CRE シグナル、財務メトリクス、営業優先度スコア、API を実装済みです。Phase 2 では既存 API を利用する Next.js ダッシュボード、企業ランキング、フィルター、企業詳細 UI を追加しています。

## 技術スタック

- フロントエンド: Next.js + React + TypeScript
- バックエンド: FastAPI + Python
- データベース: SQLite（デモ用途、将来的に PostgreSQL へ置換可能な構成を想定）
- チャート: Recharts（後続 Phase で利用）
- AI: OpenAI API（`OPENAI_API_KEY` 未設定時はモックモード。OpenAI API 連携は後続 Phase で実装）
- ローカル起動: Docker Compose

## 現在実装済みの範囲

### Phase 1: バックエンド API / データ基盤

- SQLite / SQLAlchemy モデル
- 20 社分のサンプル上場企業データ
- サンプル IR 文書由来の CRE シグナル
- 最新財務メトリクス
- 営業優先度スコアと説明、推奨アクション
- 以下の API
  - `GET /api/companies`
  - `GET /api/companies/{company_id}`
  - `GET /api/companies/{company_id}/signals`
  - `GET /api/companies/{company_id}/score`

すべての CRE シグナルには、営業仮説の根拠として `evidence_text` と `source_reference` を含めています。

### Phase 2: フロントエンドダッシュボード

- 日本語の CRE 営業ダッシュボード
- 対象企業数、高優先度企業数、最新スコア更新時刻の KPI 表示
- スコア順の会社ランキングテーブル
- 業種フィルターと優先度フィルター
- 企業詳細 UI
  - 企業プロフィール
  - 最新財務メトリクス
  - CRE シグナルカード
  - 根拠テキストと出典参照
  - スコア内訳
  - 推奨アクション

## セットアップ

```bash
cp .env.example .env
```

デモ用途では `.env.example` の値のままでも起動できます。`OPENAI_API_KEY` が未設定の場合、AI モードはモックとして表示されます。

## ローカル起動

```bash
docker compose up --build
```

起動後、以下にアクセスします。

- フロントエンド: <http://localhost:3000>
- バックエンドヘルスチェック: <http://localhost:8000/api/health>
- 企業一覧 API: <http://localhost:8000/api/companies>

## デモシナリオ

1. `docker compose up --build` でローカル起動します。
2. ブラウザで `http://localhost:3000` を開きます。
3. ダッシュボード上部で対象企業数、高優先度企業数、最新更新時刻を確認します。
4. 業種または優先度でターゲット企業を絞り込みます。
5. 企業ランキングから企業名を選択し、企業プロフィール、財務メトリクス、CRE シグナルを確認します。
6. CRE シグナルカードの根拠テキストと出典参照を確認し、営業仮説の説明可能性を確認します。
7. スコア内訳と推奨アクションをもとに、初回アプローチ方針を検討します。

## ローカル検証コマンド

### バックエンド

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -B -m py_compile app/__init__.py app/config.py app/database.py app/main.py app/models.py app/seed.py
pytest
```

### フロントエンド

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

### Docker 検証（ローカルのみ）

Codex cloud では Docker Compose コマンドを必須チェックとして扱いません。Docker 検証は、Docker が利用できるローカル環境でのみ実行してください。

```bash
docker compose config
docker compose up --build
```

起動後、別ターミナルまたはブラウザで以下を確認します。

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/config
curl http://localhost:8000/api/companies
curl http://localhost:8000/api/companies/1
```

## 環境変数

| 変数名 | 用途 | デフォルト |
|---|---|---|
| `APP_NAME` | アプリケーション名 | `CRE Sales Intelligence` |
| `DATABASE_URL` | SQLite 接続 URL | `sqlite:///./cre_sales_intelligence.db` |
| `BACKEND_CORS_ORIGINS` | フロントエンド許可 Origin | `http://localhost:3000` |
| `OPENAI_API_KEY` | OpenAI API キー。未設定時はモックモード | 空 |
| `NEXT_PUBLIC_API_BASE_URL` | フロントエンドから参照する API ベース URL | `http://localhost:8000/api` |

## API 検証観点

依存関係をインストールできるローカル環境では、以下で API 契約を検証します。

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

主な確認対象は以下です。

- `GET /api/companies` が 20 社のサンプル企業を返し、`company_id`、`ticker`、`name`、`industry`、`market`、`total_score`、`priority_label`、`signal_count` を含むこと。
- `GET /api/companies/{company_id}` が企業プロフィール、最新財務指標、CRE シグナル、スコア内訳、文書一覧を返すこと。
- `GET /api/companies/{company_id}/signals` の全シグナルに `evidence_text` と `source_reference` が含まれること。
- `GET /api/companies/{company_id}/score` が `total_score`、`priority_label`、`component_scores`、`explanation`、`recommended_action` を返すこと。

Codex cloud で Python / npm パッケージ取得が 403 になる場合は、依存関係インストールを必要としない構文チェックを実行し、pytest / Next.js build はローカルで確認してください。Docker Compose コマンドも Codex cloud の必須チェックではなく、ローカル検証専用です。

## 今後の実装予定

1. OpenAI API を利用した CRE シグナル抽出を追加します。
2. EDINET アダプタの dry-run モードを追加します。
3. Markdown レポート生成を追加します。
4. Recharts を用いた可視化チャートを追加します。
5. データベースを PostgreSQL に置き換えやすい設定・マイグレーション構成を整備します。
