# 三維貨櫃裝箱系統

*[English](README.md)*

> 具堆高機通道約束的三維裝箱最佳化，即時視覺化，全端 Docker 部署。

**線上展示 → [wutesta0101-hue.github.io/container-packing](https://wutesta0101-hue.github.io/container-packing)**

![X 光模式下的裝箱結果](docs/hero.png)

---

## 這個系統做什麼

輸入貨物資料（手動輸入或 CSV 匯入），系統計算出貨櫃的最佳三維裝載方案，並強制檢查決定方案能否在現場實際執行的物理約束：

- **堆高機通道淨空** — 每一件貨物都必須能被從櫃門進入的堆高機取到。這是幾何上強制檢查的，不是啟發式的近似。
- **堆疊規則** — 只能堆在可堆疊的貨物上，且上層貨物密度不得超過支撐物的 105%。
- **支撐覆蓋率** — 貨物底面至少 90% 需有支撐，以精確的面積聯集計算，而非四角取樣。
- **VIP 優先** — 指定的高價值貨物優先裝入最內側位置。
- **由內到外裝載** — 裝箱自櫃底向櫃門推進，符合實際堆高機作業流程。

結果以互動式三維呈現，含 X 光模式、逐件播放，以及空間利用率與重心儀表板。

| 實體模式 | X 光模式 |
|---|---|
| ![實體模式](docs/solid-view.png) | ![X 光模式](docs/hero.png) |

播放列會逐件重播裝載順序，讓現場人員看到的是**該怎麼裝**，而不只是裝完長什麼樣。

---

## 系統架構

![系統架構圖](docs/architecture(zh).png)

前端是共用單一 Zustand store 的三面板 React 應用。所有裝箱邏輯集中在 `algorithm/packing.py`，是不依賴任何框架的純函式，可獨立單元測試。四項實體約束在每個候選位置上依序評估。

---

## 部署拓樸

![部署拓樸圖](docs/deployment(zh).png)

四個容器，對外只發布單一連接埠。Nginx 提供建置後的前端靜態檔，並將 `/api/*` 反向代理至後端 —— 對瀏覽器而言只有一個來源，因此正式環境不需要任何 CORS 設定。

對外只開放 `:80` 與 `:8080`。API（`:9000`）與資料庫（`:5432`）的直接存取僅存在於開發專用的 `docker-compose.override.yml`，客戶端部署兩者皆無。

應用資料存放於 `postgres_data` named volume，位於所有容器之外。這就是為什麼 `docker compose down` 會保留資料，而 `down -v` 會將其清除。

---

## 核心演算法

裝箱引擎實作三維 **Bottom-Left-Back（BLB）錨點法**。每件貨物放置在第一個通過四項實體約束的可行錨點。

### 座標系統

原點 $(0,0,0)$ 為貨櫃的後-左-底角，櫃門位於 $x = L_{container}$。

```
z（高）
│
│    y（寬）
│   ╱
│  ╱
│ ╱
└──────── x（深，朝櫃門方向）
```

### 1. 排序策略

裝箱前先以三層鍵值排序：

$$\text{key}(i) = \big(\lnot\,\mathrm{VIP}_i,\; -V_i,\; -m_i\big), \qquad V_i = L_i W_i H_i$$

VIP 貨物永遠落在最深處，對應實際的由內到外裝載順序。

### 2. 錨點生成

貨物 $k$ 放置於 $(x_k, y_k, z_k)$ 後，產生三個新的候選錨點：

$$A_{k+1} = \{(x_k + L_k,\, y_k,\, z_k),\ (x_k,\, y_k + W_k,\, z_k),\ (x_k,\, y_k,\, z_k + H_k)\}$$

錨點以字典序 $(x, z, y)$ 嘗試——**先深、再低、後左**——這會產生密實且貼地的排列。

### 3. 約束堆疊

每個候選位置必須依序通過四項檢查：

**① 邊界**

$$x + L_i \le L_c \ \land\ y + W_i \le W_c \ \land\ z + H_i \le H_c$$

**② 碰撞（AABB）**

對每一件已放置的貨物 $p$，軸對齊包圍盒不得重疊：

$$x + L_i \le p.x \ \lor\ p.x + p.L \le x \ \lor\ y + W_i \le p.y \ \lor\ \cdots$$

**③ 堆疊支撐**

若 $z > 0$，貨物必須座落在可堆疊的支撐物上，且同時滿足密度規則與覆蓋率規則：

$$\rho_{upper} \le \rho_{support} \times 1.05$$

$$\frac{\text{Area}\!\left(\bigcup_s \text{proj}(s) \cap \text{base}(i)\right)}{L_i \times W_i} \ \ge\ 0.9$$

聯集面積以 sweep-line 演算法在 $O(N^2)$ 內**精確**計算——若改用四角取樣的近似法，會接受實務上會塌陷的懸空堆疊。

**④ 堆高機通道淨空**

候選位置與櫃門之間的走道，必須在堆高機作業包絡線內保持淨空。貨叉伸入容差 $r = 0.9 \times l_{fork}$ 允許貨叉部分滑入下一件貨物底部：

$$\forall\, p \in \text{placed}: \quad p.x \ge x + L_i + r \implies \lnot\big(Y_{overlap}(p) \land p.z < H_{forklift}\big)$$

其中 $Y_{overlap}$ 檢查 $p$ 是否落在以貨物 $y$ 中點為中心、寬度為 $\max(W_i, W_{forklift})$ 的通道範圍內。

---

## 技術組成

| 層 | 技術 |
|---|---|
| 前端 | React 18 + Vite、Three.js、Zustand、Axios |
| 三維渲染 | Three.js r128（自刻 OrbitControls） |
| 後端 | Python 3.11、FastAPI、Pydantic v2 |
| 資料庫 | PostgreSQL 16、SQLAlchemy ORM |
| 容器化 | Docker + Docker Compose |
| 前端服務 | Nginx（production build） |

---

## 快速開始

**前置需求** — Docker Desktop（或 Docker Engine + Compose plugin）、Git。

```bash
git clone https://github.com/wutesta0101-hue/container-packing.git
cd container-packing

cp .env.docker.example .env
# 預設值可直接使用，僅在需要更改資料庫帳密時編輯

docker compose up -d
```

> 目標檔名必須是 `.env`。Docker Compose 只會自動讀取 `.env`，其他檔名需要加上 `--env-file`；而忘記加參數時，Compose 不會報錯，只會靜靜套用內建預設值。

會啟動四個服務：

| 服務 | 網址 | 用途 |
|---|---|---|
| 前端 | `http://localhost` | React 應用（Nginx） |
| 後端 | 內部 | FastAPI（port 9000） |
| PostgreSQL | 內部 | 資料庫 |
| pgAdmin | `http://localhost:8080` | 資料庫管理介面 |

在 pgAdmin 建立伺服器連線時，**Host 欄位要填 `postgres`**，不是 `localhost` —— pgAdmin 跑在容器內，對它而言 `localhost` 指向自己，而 Docker 內建 DNS 會把服務名稱解析為主機名稱。

驗證：

```bash
docker compose ps            # 所有服務應顯示 "running"
docker compose logs backend  # 應出現 "Uvicorn running"
```

開啟 `http://localhost` 即載入裝箱介面。點「載入範例資料」可直接試跑，不需手動輸入貨物。

停止：

```bash
docker compose down          # 停止，資料保留
docker compose down -v       # 停止並清除資料庫
```

---

## API 說明

### `POST /api/v1/pack`

送出貨物資料並執行裝箱演算法。

```json
{
  "container_type": "40",
  "forklift_type": "E35SH",
  "cargo": [
    {
      "id": "A001",
      "type": "heavy",
      "L": 1200,
      "W": 1000,
      "H": 800,
      "weight": 800,
      "quantity": 4,
      "stackable": true,
      "rotatable": true
    }
  ]
}
```

```json
{
  "task_id": "task_a3f9c2e81b04",
  "packed": [
    {
      "id": "A001-1",
      "base_id": "A001",
      "type": "heavy",
      "L": 1200, "W": 1000, "H": 800,
      "weight": 800.0,
      "stackable": true,
      "x": 0, "y": 0, "z": 0,
      "is_packed": true,
      "rotated": false
    }
  ],
  "unpacked": [],
  "utilization": 8.51
}
```

`utilization` 為 0–100 的百分比。`unpacked` 內的項目帶有 `is_packed: false` 與 `null` 座標。`quantity: 4` 的批次會展開為四個獨立單件 —— `A001-1` 至 `A001-4` —— `base_id` 保留原始批次識別碼。

驗證錯誤回傳 **422**，`detail` 陣列會標明出錯欄位。空的貨物清單、未知的貨櫃或堆高機代碼、非正數尺寸、ID 含空白，都會在處理函式執行前被擋下。

### `GET /api/v1/results/{task_id}`

取回先前計算的結果。回傳相同結構並額外包含 `created_at`、`container_type` 與 `forklift_type`。查無此 ID 回傳 404。

---

## 參考資料

### 貨櫃規格

| 代碼 | 尺寸 長 × 寬 × 高（mm） | 最大載重（kg） |
|---|---|---|
| `20` | 5,898 × 2,352 × 2,393 | 28,000 |
| `40` | 12,032 × 2,352 × 2,393 | 26,000 |
| `40HQ` | 12,032 × 2,352 × 2,698 | 26,000 |

### 堆高機規格

依 Linde E 系列技術規格。選定的機型決定所需的通道寬度，因此會直接改變計算結果。

| 代碼 | 型號 | 車身寬（mm） | 車身高（mm） | 額定載重（kg） |
|---|---|---|---|---|
| `E25` | Linde E25 | 1,175 | 2,200 | 2,500 |
| `E25S` | Linde E25 S | 1,175 | 2,200 | 2,500 |
| `E25SH` | Linde E25 SH | 1,228 | 2,200 | 2,500 |
| `E30S` | Linde E30 S | 1,228 | 2,200 | 3,000 |
| `E30SH` | Linde E30 SH | 1,228 | 2,200 | 3,000 |
| `E35SH` | Linde E35 SH | 1,325 | 2,200 | 3,500 |

所有型號的貨叉長度均為 1,150 mm，淨空判定時套用 0.9 的伸入係數。

### 貨物類型

| 代碼 | 標示 | 行為 |
|---|---|---|
| `normal` | 一般 | 預設 |
| `heavy` | 重物 | 顏色區隔；密度規則與其他貨物相同 |
| `fragile` | 易碎品 | 通常宣告為 `stackable: false` |
| `vip` | VIP | 優先排序，放置於最內側 |

### CSV 匯入格式

請存成 UTF-8 —— Excel 預設的 CSV 匯出可能使用地區編碼，導致中文亂碼。

```csv
id,type,length,width,height,weight,quantity,stackable,rotatable
A001,heavy,1200,1000,800,800,4,true,true
B001,fragile,1000,800,600,150,5,false,true
V001,vip,1400,1100,1000,600,2,true,true
```

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | string | 批次識別碼，不可含空白 |
| `type` | enum | `normal` / `heavy` / `fragile` / `vip` |
| `length`、`width`、`height` | integer（mm） | 尺寸 |
| `weight` | float（kg） | 單件重量，用於堆疊密度檢查 |
| `quantity` | integer | 此批次的相同件數 |
| `stackable` | boolean | 是否允許其他貨物堆疊其上 |
| `rotatable` | boolean | 是否允許繞垂直軸旋轉 90° |

`stackable` 與 `rotatable` 未填時預設為 `true`，只有明確寫 `false` 才會停用。

---

## 專案結構

```
container-packing/
├── backend/
│   ├── algorithm/
│   │   └── packing.py           ← 三維裝箱核心，純函式、可單元測試
│   ├── db/
│   │   └── repository.py        ← SQLAlchemy ORM，Tasks + PackedItems
│   ├── routes/
│   │   └── pack.py              ← FastAPI 路由處理
│   ├── schemas/                 ← Pydantic 請求 / 回應模型
│   ├── services/
│   │   └── packing_service.py   ← 業務邏輯、流程編排
│   ├── core/
│   │   └── config.py            ← .env、CORS 設定
│   ├── tests/                   ← 演算法單元測試
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LeftPanel/       ← 輸入表單、CSV 上傳、貨物清單
│   │   │   ├── CenterCanvas/    ← Three.js 三維場景
│   │   │   └── RightPanel/      ← 儀表板卡片
│   │   ├── store/
│   │   │   └── useCargoStore.js ← Zustand 全域狀態
│   │   └── api/
│   │       └── apiClient.js     ← Axios，所有後端呼叫
│   ├── Dockerfile
│   └── nginx.conf
├── docs/
├── docker-compose.yml
├── docker-compose.override.yml  ← 開發覆寫：對外連接埠、熱重載
└── .env.docker.example
```

---

## 相關專案

**[貨櫃追蹤器](https://github.com/wutesta0101-hue/container-arrival-tracker)** — 零基礎設施的貨櫃到貨**追蹤工具**，串接倉庫、報關與採購三個部門。

**[電動移動貨架 揀貨序列最佳化](https://github.com/wutesta0101-hue/emr-scheduling)** — 密集式移動貨架的揀貨**3D可視化**。

---

**授權** — © 2026 Testa Wu。保留所有權利。僅供作品展示用途。
