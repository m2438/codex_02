# Backend

CRE Sales Intelligence の FastAPI バックエンドです。

## ローカル実行

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

## ヘルスチェック

```bash
curl http://localhost:8000/api/health
```

## テスト

```bash
pytest
```

## Phase 1 API

```bash
curl http://localhost:8000/api/companies
curl http://localhost:8000/api/companies/1
curl http://localhost:8000/api/companies/1/signals
curl http://localhost:8000/api/companies/1/score
```
