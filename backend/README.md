# Backend

CRE Sales Intelligence の FastAPI バックエンドです。

## ローカル実行

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## ヘルスチェック

```bash
curl http://localhost:8000/api/health
```
