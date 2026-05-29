# 3D 貨櫃裝箱系統 — 環境建置指南

## 專案結構

```
container-packing/
├── backend/
│   ├── requirements.txt    ← Python 套件清單
│   └── .env.example        ← 環境變數範本
├── frontend/               ← 之後用 Vite 建立
├── docker-compose.yml      ← PostgreSQL + pgAdmin
└── .gitignore
```

---

## 一、啟動 PostgreSQL（用 Docker）

在專案根目錄（`container-packing/`）下打開終端機：

```bash
docker compose up -d
```

這會在背景啟動兩個服務：

| 服務 | 用途 | 連線位置 |
|---|---|---|
| `cp_postgres` | PostgreSQL 16 資料庫 | `localhost:5432` |
| `cp_pgadmin` | 資料庫圖形管理介面 | http://localhost:5050 |

**資料庫連線資訊：**
- 帳號：`cpuser`
- 密碼：`cppassword`
- 資料庫名稱：`container_packing`

**pgAdmin 登入：**
- Email：`admin@example.com`
- 密碼：`admin`

驗證是否啟動成功：
```bash
docker compose ps
```
看到兩個服務都是 `running` 就成功了。

**常用指令：**
```bash
docker compose up -d      # 啟動
docker compose stop       # 停止（保留資料）
docker compose down       # 停止並移除容器（保留資料 volume）
docker compose down -v    # 連資料一起清除（重置用）
docker compose logs -f    # 看即時 log
```

---

## 二、設定後端（FastAPI）

### 1. 在 PyCharm 開啟專案

`File → Open` 選擇 `container-packing/` 資料夾。

### 2. 建立 Python 虛擬環境

`Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter`：
- 選 **Virtualenv Environment**
- Location：`container-packing/backend/.venv`
- Base interpreter：你的 Python 3.11+

### 3. 安裝套件

打開 PyCharm 內建 Terminal（確認左下角顯示 `(.venv)`）：

```bash
cd backend
pip install -r requirements.txt
```

如果看到綠色字 `Successfully installed ...` 就成功了。

### 4. 設定環境變數

```bash
# Mac / Linux
cp .env.example .env

# Windows (PowerShell)
copy .env.example .env
```

`.env` 是給本地用的，已經被 `.gitignore` 排除，**永遠不要 commit**。

### 5. 驗證後端可跑

先建立一個最小的 `main.py` 測試（之後我們會擴充）：

```python
# backend/main.py
from fastapi import FastAPI

app = FastAPI(title="Container Packing API")

@app.get("/")
def root():
    return {"status": "ok"}
```

跑起來：
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 9000
```

請先執行方案一：
uvicorn main:app --reload --host 127.0.0.1 --port 9000

如果成功啟動，您會看到：
INFO: Uvicorn running on http://127.0.0.1:9000

這時請打開瀏覽器造訪：
http://127.0.0.1:9000/docs

只要看到 FastAPI 的藍色畫面（Swagger UI），我們就過關了

---

## 三、建立前端（Vite + React）

### 1. 確認 Node.js 版本

```bash
node -v   # 要 v20.x 或更新
npm -v    # 要 v10.x 或更新
```

### 2. 在專案根目錄執行

```bash
# 從 container-packing/ 開始
npm create vite@latest frontend -- --template react

cd frontend
npm install
```

選項提示時：
- Framework：**React**
- Variant：**JavaScript**（如果你會 TypeScript 也可以選 TypeScript）

### 3. 安裝必要套件

```bash
# UI 與表單
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material

# CSV 解析
npm install papaparse

# API 呼叫
npm install axios

# 3D 渲染（給模組 6 用）
npm install three @react-three/fiber @react-three/drei
```

### 4. 啟動前端

```bash
npm run dev
```

打開瀏覽器看 http://localhost:5173 應該看到 Vite 預設的 React 歡迎頁。

---

## 四、PyCharm Run Configuration 設定（強烈推薦）

省去每次都要打指令的麻煩。

### 後端：`Run → Edit Configurations → + → Python`
- Name：`Backend (FastAPI)`
- Module name：`uvicorn`（注意是 Module，不是 Script）
- Parameters：`main:app --reload`
- Working directory：`container-packing/backend`
- Python interpreter：選你剛建的 .venv

### 前端：`Run → Edit Configurations → + → npm`
- Name：`Frontend (Vite)`
- package.json：選 `container-packing/frontend/package.json`
- Command：`run`
- Scripts：`dev`

設好之後右上角會有兩個綠色三角形按鈕，一鍵啟動。

---

## 五、檢查清單（環境是否齊全）

跑完上面步驟，下面這 4 個都要能成功：

- [ ] `docker compose ps` 顯示 postgres 與 pgadmin 都 running
- [ ] 瀏覽器打開 http://localhost:5050 能看到 pgAdmin 登入頁
- [ ] 瀏覽器打開 http://127.0.0.1:9000/docs 能看到 FastAPI Swagger
- [ ] 瀏覽器打開 http://localhost:5173 能看到 Vite React 頁面

**全部打勾 → 環境完成，可以進入開發階段。**

---

## 六、接下來的開發順序建議

1. **模組 2 + 模組 4**（後端骨架）— Pydantic schema、API route、資料庫 model
2. **模組 3**（核心演算法）— 純函數的 3DBPP，先用單元測試驗證
3. **模組 5**（資料持久化）— SQLAlchemy 接上 PostgreSQL
4. **模組 1**（前端輸入）— React 表單與 CSV 上傳
5. **模組 6**（3D 可視化）— Three.js 串接後端結果

這個順序的好處是：演算法是核心難點，先把它寫對且測試通過，後面接 UI 才不會白工。
