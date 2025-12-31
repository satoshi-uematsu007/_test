# Study Tracker API

FastAPI で学習時間を管理する REST API です。Render.com へのデプロイを前提とした構成になっています。

## 要求仕様
- Python 3.11
- FastAPI + SQLAlchemy 2.x + Alembic
- PostgreSQL（`DATABASE_URL` で接続）
- OpenAPI ドキュメント: `/docs`
- CORS: デフォルトで `*` 許可

## セットアップ

### 1. 依存関係のインストール
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数
`.env` またはシェル環境に `DATABASE_URL` を設定してください。
例:
```
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
```

### 3. データベース初期化 & マイグレーション
最初に DB に接続可能なことを確認した上で Alembic を実行します。
```bash
alembic upgrade head
```

## ローカル起動
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- ヘルスチェック: `GET http://localhost:8000/api/health`
- OpenAPI: `http://localhost:8000/docs`

## Render へのデプロイ手順（例）
1. Render で **New Web Service** を作成
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT`
4. Environment Variables に `DATABASE_URL` を登録（Render の PostgreSQL を接続）
5. 必要なら `PYTHON_VERSION=3.11` を追加
6. デプロイ後、`/api/health` で稼働確認
7. マイグレーションはデプロイフック、またはシェルで `alembic upgrade head` を実行

## API クイックリファレンス
Base URL: `/api`

### ユーザー
- `POST /api/users` — `{ "email": "a@example.com" }`
- `GET /api/users/{user_id}`

### セッション
- `POST /api/users/{user_id}/sessions/start`
  - body 例: `{ "started_at": "2025-12-31T10:00:00+09:00", "memo": "数学" }`
- `POST /api/users/{user_id}/sessions/{session_id}/stop`
  - body 例: `{ "ended_at": "2025-12-31T11:30:00+09:00" }`
- `GET /api/users/{user_id}/sessions?status=active|closed|all&from=...&to=...`
- `DELETE /api/users/{user_id}/sessions/{session_id}`

### 統計
- `GET /api/users/{user_id}/stats/daily?date=YYYY-MM-DD`
- `GET /api/users/{user_id}/stats/weekly?week_start=YYYY-MM-DD`

## 動作確認例 (curl)
```bash
# ユーザー作成
USER_ID=$(curl -s -X POST http://localhost:8000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}' | jq -r '.id')

# セッション開始
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/users/$USER_ID/sessions/start \
  -H 'Content-Type: application/json' \
  -d '{"memo":"math"}' | jq -r '.id')

# セッション終了
curl -s -X POST http://localhost:8000/api/users/$USER_ID/sessions/$SESSION_ID/stop -H 'Content-Type: application/json'

# 日次統計
curl -s "http://localhost:8000/api/users/$USER_ID/stats/daily?date=$(date +%F)"

# 週次統計
curl -s "http://localhost:8000/api/users/$USER_ID/stats/weekly"
```

## テスト
簡易的な例として `pytest` でヘルスチェックが通るか確認できます。
```bash
pytest
```

