# CRE Sales Intelligence

CRE Sales Intelligence は、CRE コンサルティング営業チーム向けのローカルデモアプリケーションです。公開 IR 文書またはサンプル文書から CRE 戦略ニーズの兆候を整理し、営業優先度を可視化することを目的としています。

> Phase 0 時点では、FastAPI バックエンド、Next.js フロントエンド、Docker Compose、環境変数テンプレート、ヘルスチェック疎通のみを実装しています。会社マスタ、IR 文書、シグナル抽出、スコアリング、レポート生成は後続 Phase で追加します。

## 技術スタック

- フロントエンド: Next.js + React + TypeScript
- バックエンド: FastAPI + Python
- データベース: SQLite（デモ用途、将来的に PostgreSQL へ置換可能な構成を想定）
- チャート: Recharts（後続 Phase で利用）
- AI: OpenAI API（`OPENAI_API_KEY` 未設定時はモックモード）
- ローカル起動: Docker Compose

## セットアップ

```bash
cp .env.example .env
```

Phase 0 では `.env.example` の値のままでも起動できます。

## ローカル起動

```bash
docker compose up --build
```

起動後、以下にアクセスします。

- フロントエンド: <http://localhost:3000>
- バックエンドヘルスチェック: <http://localhost:8000/api/health>


## ローカル検証コマンド

### バックエンド

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -B -m py_compile app/__init__.py app/config.py app/main.py
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
```

## 環境変数

| 変数名 | 用途 | デフォルト |
|---|---|---|
| `APP_NAME` | アプリケーション名 | `CRE Sales Intelligence` |
| `DATABASE_URL` | SQLite 接続 URL | `sqlite:///./cre_sales_intelligence.db` |
| `BACKEND_CORS_ORIGINS` | フロントエンド許可 Origin | `http://localhost:3000` |
| `OPENAI_API_KEY` | OpenAI API キー。未設定時はモックモード | 空 |
| `NEXT_PUBLIC_API_BASE_URL` | フロントエンドから参照する API ベース URL | `http://localhost:8000/api` |

## Phase 0 デモシナリオ

1. `docker compose up --build` でローカル起動します。
2. ブラウザで `http://localhost:3000` を開きます。
3. 画面上部のステータスで、バックエンド疎通結果と AI モードを確認します。
4. `OPENAI_API_KEY` 未設定の場合は `モックモード` と表示されます。

## 今後の実装予定

1. 20 社分のサンプル会社マスタと IR 文書データを追加します。
2. モック CRE シグナル抽出を追加します。
3. 営業優先度スコアリングを追加します。
4. Recharts を用いたダッシュボードを追加します。
5. 企業詳細画面と Markdown レポート生成を追加します。
6. EDINET アダプタの dry-run モードを追加します。
