# CRE営業支援BI

CRE営業支援BI は、CRE コンサルティング営業チーム向けのローカルデモアプリケーションです。日本国内の実在上場企業10社の `public_demo` データを対象に、日本語の公開IR資料からCRE戦略ニーズの兆候を整理し、営業優先度を可視化することを目的としています。

> Phase 1〜4Aで構築したデータモデル、API、Next.jsダッシュボード、CREシグナル抽出、レポート生成を前提に、Phase 4A修正では合成デモ企業20社をseed対象から削除し、日本国内の実在上場企業10社のpublic_demoデータを中心に営業デモを行う構成へ移行しました。

## 技術スタック

- フロントエンド: Next.js + React + TypeScript
- バックエンド: FastAPI + Python
- データベース: SQLite（デモ用途、将来的に PostgreSQL へ置換可能な構成を想定）
- チャート: Recharts（後続 Phase で利用）
- AI: OpenAI API（`OPENAI_API_KEY` 未設定時はモックモード。ローカルデモ起動に OpenAI API は必須ではありません）
- ローカル起動: Docker Compose

## 現在実装済みの範囲

### Phase 1: バックエンド API / データ基盤

- SQLite / SQLAlchemy モデル
- 10 社分の日本国内実在上場企業 `public_demo` データ（公開IR資料に基づく営業仮説）
- 合成デモ企業20社はseed対象から削除済み（後方互換のため `data_source_type` フィールドは維持）
- サンプル IR 文書由来の CRE シグナル
- 財務関連指標（売上成長率、営業利益率、設備投資額、現預金等の軸・目盛り付き軽量ゲージ）（内部値は百万円単位、UI / レポートでは億円・兆円表示）
- 営業優先度スコアと説明、推奨アクション
- 以下の API
  - `GET /api/companies`
  - `GET /api/companies/{company_id}`
  - `GET /api/companies/{company_id}/signals`
  - `GET /api/companies/{company_id}/score`

すべての CRE シグナルには、営業仮説の根拠として `evidence_text` と `source_reference` を含めています。

### Phase 2: フロントエンドダッシュボード

- 日本語の CRE営業支援BI ダッシュボード
- 対象企業数と最新スコア更新時刻の控えめなサマリー表示
- スコア順の会社ランキングテーブル
- 業種フィルターと優先度フィルター
- 企業詳細 UI
  - 企業プロフィール
  - 財務関連指標（売上成長率、営業利益率、設備投資額、現預金等の軸・目盛り付き軽量ゲージ）
  - CRE シグナルカード
  - 根拠テキストと出典参照
  - スコア内訳（コンポーネント別スコア、バー表示。詳細理由は構造化レポートの表で表示）

### Phase 3: シグナル抽出 / レポート生成

- CRE シグナル抽出サービス
  - `OPENAI_API_KEY` 未設定時は deterministic mock mode でサンプル文書本文から抽出します。
  - `OPENAI_API_KEY` 設定時のみ OpenAI API mode を利用します。
  - OpenAI API キーはバックエンド環境変数としてのみ扱い、フロントエンドには公開しません。
- CRE シグナル抽出プロンプトテンプレート
- 抽出シグナルの必須項目
  - `signal_type`
  - `summary`
  - `evidence_text`
  - `source_reference`
  - `confidence`
  - `recommended_sales_action`
- 既存互換の Markdown 文字列と、UI主表示用の構造化CRE営業仮説レポート生成サービス
- 追加 API
  - `GET /api/companies/{company_id}/report`
- 企業詳細 UI では Markdown 文字列を主表示せず、構造化レポートをリッチUIとして表示


### Phase 3.5: デモ品質改善

- Phase 3.5では合成デモ企業の比較性を改善していましたが、Phase 4A修正により営業デモの主対象は実在企業 `public_demo` 10社へ移行しました。
- 金額データはバックエンドでは百万円単位の整数値を維持し、フロントエンドとレポートでは億円または兆円に変換して表示します。
- 企業別 CRE 営業仮説レポートは、11章構成（エグゼクティブサマリー、優先度判定、スコア内訳、需要兆候、財務所見、経営課題接続、提案テーマ、初回アプローチ、追加ヒアリング、根拠資料、留意事項）に拡張しています。UIでは章番号順に並べ、③スコア内訳と評点理由は表形式で表示します。⑤財務・投資余力に関する所見は、売上成長率、営業利益率、設備投資額、現預金等のレンジに応じて企業別の示唆が変わるようにしています。


### Phase 4A: 日本国内の実在企業デモ化

- 日本国内の実在上場企業10社を `public_demo` として登録し、合成デモ企業20社はseed生成しない構成に変更しました。対象は製造業、小売、物流、鉄道、不動産、通信・データセンター関連、医薬、化学、インフラ・エネルギーの分散を意識して選定しています。
- 実在企業デモは、公式IRサイトで確認できる日本語の有価証券報告書、統合報告書、中期経営計画、決算説明資料、サステナビリティ関連資料等を優先し、公開情報に基づく要約を入力データにしています。長い著作物本文は保存していません。
- `documents` には資料名、資料種別、対象年度、`source_url`、取得日時、出典メモを保持します。UIとレポートから資料名とURLを確認できます。
- `data_source_type` は後方互換のため維持していますが、現行seedは `public_demo` のみを生成します。
- 実在企業のスコアリングは Phase 3.5 の100点満点ロジックをそのまま使い、公平・公正・中立的・客観的に算定します。優先度が高くなるように意図的な調整はしていません。
- 実在企業レポートは、公開情報から読み取れる事項、CRE観点の仮説、追加確認事項、提案余地の可能性、留意事項を分け、当該企業の正式なCRE方針や実際の提案機会を断定しません。

### Phase 4A UI改善（Phase 4B前）

- ダッシュボード上部をカード型ヒーローからコンパクトなツールバー型ヘッダーへ変更し、営業デモ時にランキング・企業詳細・主要指標が初期表示内に入りやすい構成にしました。
- 画面上の表示名称は「CRE営業支援BI」と「財務関連指標」に統一しています。
- 財務関連指標は、固定レンジまたは自然な丸め値の最大目盛りを使い、最小値・中間目盛り・最大値・0%基準が分かる軽量ゲージで表示します。
- 営業優先度スコアカードは、総合スコア、優先度ラベル、4指標スコア、スコアバーに絞り、推奨アクションや長文理由は分析レポート側へ集約しました。
- 根拠資料カードは企業詳細の最後に配置し、資料名、資料種別、年度、URL、言語などの事実情報を簡潔に表示します。
- ⑪留意事項は控えめな表示にし、Phase 4BのEDINET API本格接続、IR資料自動取得、継続クローリング、スケジュール実行は未実装のままです。

#### Phase 4A public_demo 対象企業と主な参照資料

| 企業 | 業種 | 主な参照資料URL | 選定理由 |
|---|---|---|---|
| トヨタ自動車株式会社 | 輸送用機器 | https://global.toyota/jp/ir/library/securities-report/index.html / https://global.toyota/jp/ir/library/annual/index.html | 国内最大級の製造業で、工場・研究開発・脱炭素投資などCRE論点が幅広い。 |
| 株式会社セブン＆アイ・ホールディングス | 小売業 | https://www.7andi.com/ir/library/secrepo.html / https://www.7andi.com/ir/library/mr/index.html | 店舗網・物流・事業ポートフォリオ見直しの観点で小売CRE仮説を示しやすい。 |
| NIPPON EXPRESSホールディングス株式会社 | 陸運業 | https://www.nipponexpress-holdings.com/ja/ir/library/securities/ / https://www.nipponexpress-holdings.com/ja/ir/library/annual/ | 物流施設、倉庫ネットワーク、サステナビリティ投資のCRE論点が明確。 |
| 東日本旅客鉄道株式会社 | 鉄道 | https://www.jreast.co.jp/company/ir/library/securitiesreport/ / https://www.jreast.co.jp/company/vision_report/report/ | 鉄道設備、駅周辺開発、老朽化・BCP対応などCRE/インフラ論点が多い。 |
| 野村不動産ホールディングス株式会社 | 不動産業 | https://www.nomura-re-hd.co.jp/ir/ir_library/ / https://www.nomura-re-hd.co.jp/ir/ir-library/integrated-report.html | 不動産開発・保有運営・物流施設など、CRE提案テーマと比較しやすい。 |
| 日本電信電話株式会社 | 情報・通信業 | https://group.ntt/jp/ir/library/yuho/ / https://group.ntt/jp/ir/library/annual/index.html | 通信局舎、データセンター、研究開発、脱炭素投資のCRE論点が多い。 |
| 三菱電機株式会社 | 電気機器 | https://www.mitsubishielectric.co.jp/ir/data/negotiable_securities/ / https://www.mitsubishielectric.co.jp/ir/data/integrated_report/ | 工場、研究開発、社会インフラ、半導体・データセンター関連設備の論点がある。 |
| 武田薬品工業株式会社 | 医薬品 | https://www.takeda.com/jp/investors/sec-filings / https://www.takeda.com/jp/investors/overview/ | 研究所・製造拠点・品質管理・サステナビリティ投資のCRE仮説を検討しやすい。 |
| 三菱ガス化学株式会社 | 化学 | https://www.mgc.co.jp/ir/library/report.html / https://www.mgc.co.jp/ir/index.html | 化学プラント、研究開発、半導体材料、脱炭素・安全対策のCRE論点がある。 |
| 東京ガス株式会社 | 電気・ガス業 | https://www.tokyo-gas.co.jp/IR/library/yuho_j.html / https://www.tokyo-gas.co.jp/IR/index.html | エネルギー供給インフラ、脱炭素、供給設備投資、不動産活用の論点がある。 |

実営業で利用する場合は、必ず最新の一次情報、個別不動産情報、顧客ヒアリングで検証してください。

## セットアップ

```bash
cp .env.example .env
```

デモ用途では `.env.example` の値のままでも起動できます。`OPENAI_API_KEY` が未設定の場合、AI モードはモックとして表示され、OpenAI API 呼び出しなしで動作します。

## ローカル起動

```bash
docker compose up --build
```

起動後、以下にアクセスします。

- フロントエンド: <http://localhost:3000>
- バックエンドヘルスチェック: <http://localhost:8000/api/health>
- 企業一覧 API: <http://localhost:8000/api/companies>
- 企業別レポート API: <http://localhost:8000/api/companies/1/report>


## スコアリングポリシー

営業優先度の `total_score` は 100 点満点です。単純にラベルを固定するのではなく、保存済み CRE シグナル、財務指標、戦略イベント、CRE 支援テーマへの適合度から算定します。API レスポンスには `component_scores` に加えて、各コンポーネントの `max_points` と短い評点理由を含む `component_details` を返します。

| コンポーネント | 満点 | 評価内容 |
|---|---:|---|
| `signal_score` | 35 | CRE 関連シグナルの件数、強さ、信頼度、テーマ多様性を評価します。対象例は遊休資産、拠点集約、建替え、BCP、脱炭素、設備投資拡大などです。 |
| `financial_score` | 25 | 売上高、設備投資額、現預金等、売上成長率、営業利益率から企業規模と投資余力を評価します。 |
| `strategic_event_score` | 25 | 中期経営計画、構造改革、資本効率、サステナビリティ、物流・R&D 拠点拡張、事業ポートフォリオ見直し等に接続しやすいイベントを評価します。 |
| `fit_score` | 15 | CRE 戦略、PM/CM、再開発、遊休資産活用、不動産ポートフォリオ最適化の支援余地を評価します。 |

優先度判定の閾値は以下です。

- 高: 85 点以上
- 中: 50 点以上 85 点未満
- 低: 50 点未満

実在企業分析は公開IR資料に基づく営業仮説です。営業優先度はスコアリングロジックの結果であり、当該企業の正式なCRE方針、実際の提案機会、経営評価を断定するものではありません。実際の営業活動前には最新公開資料と一次情報で必ず追加検証してください。

## デモシナリオ

1. `docker compose up --build` でローカル起動します。
2. ブラウザで `http://localhost:3000` を開きます。
3. ダッシュボード上部で対象企業数、高優先度企業数、最新更新時刻を確認します。
4. 業種または優先度でターゲット企業を絞り込みます。
5. 企業ランキングから企業名を選択し、企業プロフィール、財務メトリクス、CRE シグナルを確認します。
6. CRE シグナルカードの根拠テキストと出典参照を確認し、営業仮説の説明可能性を確認します。
7. スコア内訳と推奨アクションをもとに、初回アプローチ方針を検討します。
8. 企業詳細の分析レポート欄で、章立てされたリッチUIのエグゼクティブサマリー、スコア内訳、追加ヒアリング、根拠資料、留意事項を確認します。

## ローカル検証コマンド

### バックエンド

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -B -m py_compile app/__init__.py app/config.py app/database.py app/main.py app/models.py app/seed.py app/services/__init__.py app/services/scoring.py app/services/signal_extraction.py app/services/reporting.py
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
curl http://localhost:8000/api/companies/1/report
```

## 環境変数

| 変数名 | 用途 | デフォルト |
|---|---|---|
| `APP_NAME` | アプリケーション名 | `CRE営業支援BI` |
| `DATABASE_URL` | SQLite 接続 URL | `sqlite:///./cre_sales_intelligence.db` |
| `BACKEND_CORS_ORIGINS` | フロントエンド許可 Origin | `http://localhost:3000` |
| `OPENAI_API_KEY` | OpenAI API キー。未設定時はモックモード。フロントエンドには露出しません。 | 空 |
| `NEXT_PUBLIC_API_BASE_URL` | フロントエンドから参照する API ベース URL | `http://localhost:8000/api` |


### OpenAI API mode の利用方法

OpenAI API は任意です。`OPENAI_API_KEY` が未設定の場合、バックエンドはモックモードまたは保存済みseedデータで動作します。APIキーを利用する場合も、キーはバックエンド環境変数としてのみ設定し、フロントエンドや `NEXT_PUBLIC_` 系環境変数には設定しないでください。

Windows コマンドプロンプトで一時的に設定する例:

```cmd
set OPENAI_API_KEY=your_api_key_here
```

Windows で永続的に設定する例:

```cmd
setx OPENAI_API_KEY "your_api_key_here"
```

実キー（`sk-...` で始まる値など）は `.env`、README、ソースコード、スクリーンショット、GitHub PR本文へコミットしないでください。

## API 検証観点

依存関係をインストールできるローカル環境では、以下で API 契約を検証します。

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

主な確認対象は以下です。

- `GET /api/companies` が10社の実在企業デモを返し、`company_id`、`ticker`、`name`、`industry`、`market`、`total_score`、`priority_label`、`signal_count` を含むこと。
- `GET /api/companies/{company_id}` が企業プロフィール、データ種別、最新財務指標、CRE シグナル、スコア内訳、文書一覧、実在企業の場合はsource_urlを返すこと。
- `GET /api/companies/{company_id}/signals` の全シグナルに `evidence_text` と `source_reference` が含まれること。
- `GET /api/companies/{company_id}/score` が `total_score`、`priority_label`、`component_scores`、`component_details`、`explanation`、`recommended_action` を返すこと。
- `GET /api/companies/{company_id}/report` が既存互換の `preview`、`markdown_content` に加えて `structured_report` を返し、UI主表示では `structured_report` を章番号順のリッチUIとして表示すること。③スコア内訳と評点理由は、評価対象、評価観点、根拠・判断理由、点数/満点を持つ表形式データとして返すこと。

## Phase 4B 時点の制限事項

- EDINET API は書類一覧API検索と書類取得APIのアダプタを実装していますが、運用にはEDINETコードの確認・更新とAPIキー設定が必要です。
- 継続的なスケジュールクロール、企業IRサイトの大規模スクレイピングは未実装です。
- 認証、ユーザー管理、CRM 連携は未実装です。
- OpenAI API mode は任意です。依存パッケージを追加せず、バックエンドから HTTPS API を呼び出す構成にしています。
- AI 出力に `evidence_text` がない場合、そのシグナルは破棄されます。信頼度が不明な場合は `low` として扱います。
- レポートはフロントエンドで直接生成せず、保存済みデータベースレコードと抽出済みシグナルをもとにバックエンドで生成します。

Codex cloud で Python / npm パッケージ取得が 403 になる場合は、依存関係インストールを必要としない構文チェックを実行し、pytest / Next.js build はローカルで確認してください。Docker Compose コマンドも Codex cloud の必須チェックではなく、ローカル検証専用です。

## 今後の実装予定

1. EDINETコード更新フローと取得済み有報ZIPのXBRL/PDF詳細解析を強化します。
2. Markdown レポートのダウンロード導線を追加します。
3. Recharts を用いた可視化チャートを追加します。
4. データベースを PostgreSQL に置き換えやすい設定・マイグレーション構成を整備します。

## Phase 4B: 実IR資料取得・分析パイプライン

Phase 4Bでは、既存のpublic_demoデータを維持したまま、公開IR資料を取得・テキスト抽出・CRE観点で分析するためのバックエンドAPIと企業詳細画面の補助操作パネルを追加しています。実在企業に関する出力は公開情報に基づく営業仮説であり、正式方針や提案機会を断定するものではありません。

### 対象資料

- 有価証券報告書: EDINET APIの「書類一覧API」でデフォルト過去365日（`EDINET_LOOKBACK_DAYS`で変更可）を検索し、対象会社のEDINETコード・書類種別に合う最新docIDを選択して「書類取得API」で取得します。
- 中期経営計画書、統合報告書、決算説明資料、サステナビリティレポート: `documents.source_url` に手動登録されたPDF URLから取得します。HTMLページの場合は、そのページ内のPDFリンク候補のみを探索し、相対URLを絶対URLへ変換して最適候補を取得します。
- 企業IRサイト全体の大規模クロール、継続クローリング、スケジュール実行は実装していません。
- EDINETコードは企業ごとに登録・更新が必要です。未登録の場合、EDINET取得処理は安全にスキップします。

### 環境変数

| 変数 | 用途 |
| --- | --- |
| `EDINET_API_KEY` | EDINET APIで有価証券報告書を取得する場合に必要です。 |
| `OPENAI_API_KEY` | OpenAI APIによるAI分析を行う場合のみ必要です。未設定時はmock/ルールベースで動作します。 |
| `IR_FETCH_ENABLED` | `true` の場合のみ外部取得を許可します。`false` では既存public_demoデータのみでデモが動きます。 |
| `IR_FETCH_DRY_RUN` | `true` の場合、外部API・外部URLに接続せず、取得対象と実行予定を返します。 |
| `IR_ANALYSIS_MODE` | `mock` または `openai`。`openai` でも `OPENAI_API_KEY` 未設定時はmock相当で動作します。 |
| `IR_FETCH_STORAGE_DIR` | 取得ファイルと抽出テキストの保存先です。 |
| `EDINET_LOOKBACK_DAYS` | EDINET書類一覧APIで過去何日分を検索するかを指定します。未設定時は365日です。 |

> APIキーやシークレットをGitHubへコミットしないでください。`.env` はローカル専用とし、共有時は `.env.example` のみを利用してください。

### Windowsコマンドプロンプトでの一時設定例

```cmd
set EDINET_API_KEY=...
set OPENAI_API_KEY=...
set IR_FETCH_ENABLED=true
set IR_FETCH_DRY_RUN=true
set IR_ANALYSIS_MODE=mock
set EDINET_LOOKBACK_DAYS=365
```

OpenAI分析を試す場合のみ、dry-runや取得対象を確認したうえで以下のように切り替えます。

```cmd
set IR_ANALYSIS_MODE=openai
```

### 追加API

- `POST /api/companies/{company_id}/documents/fetch` — 手動登録IR URLの取得
- `POST /api/companies/{company_id}/documents/fetch-edinet` — EDINET書類一覧API検索と書類取得APIによる有報取得
- `POST /api/companies/{company_id}/analyze` — PDF抽出済みテキストを優先し、未抽出時のみ既存DB/シードテキストへフォールバックしてCRE関連箇所抽出・シグナル生成
- `GET /api/companies/{company_id}/documents` — 資料一覧と取得状態
- `GET /api/companies/{company_id}/analysis-runs` — 分析履歴
- `GET /api/companies/{company_id}/fetch-runs` — 取得履歴

### 実営業利用時の注意

本アプリは営業デモ用です。実営業で利用する前に、一次情報の原文確認、個別不動産・施設情報の確認、顧客ヒアリングによる検証が必要です。AIまたはルールベースの抽出結果は、根拠抜粋と出典URLを伴う確認候補として扱ってください。
