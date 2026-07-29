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

![系統架構圖](docs/architecture.png)

前端是共用單一 Zustand store 的三面板 React 應用。所有裝箱邏輯集中在 `algorithm/packing.py`，是不依賴任何框架的純函式，可獨立單元測試。四項實體約束在每個候選位置上依序評估。

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

cp .env.docker.example .env.docker
# 預設值可直接使用，僅在需要更改資料庫帳密時編輯

docker compose up -d
```

會啟動四個服務：

| 服務 | 網址 | 用途 |
|---|---|---|
| 前端 | `http://localhost` | React 應用（Nginx） |
| 後端 | 內部 | FastAPI（port 9000） |
| PostgreSQL | 內部 | 資料庫 |
| pgAdmin | `http://localhost:8080` | 資料庫管理介面 |

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
  "container": "20ft",
  "forklift": "linde_e25",
  "cargo": [
    {
      "id": "A001",
      "type": "standard",
      "L": 1200,
      "W": 800,
      "H": 1000,
      "weight": 500,
      "quantity": 3,
      "stackable": true
    }
  ]
}
```

```json
{
  "task_id": "abc123",
  "packed": [
    { "id": "A001-1", "x": 0, "y": 0, "z": 0, "L": 1200, "W": 800, "H": 1000 }
  ],
  "unpacked": [],
  "utilization": 0.87,
  "cog": { "x": 4200, "y": 1150, "z": 620 }
}
```

### `GET /api/v1/results/{task_id}`

取回先前計算的結果。

---

## 參考資料

### 貨櫃規格

| 代碼 | 尺寸 長 × 寬 × 高（mm） |
|---|---|
| `20ft` | 5,900 × 2,350 × 2,390 |
| `40ft` | 12,030 × 2,350 × 2,390 |
| `40ft_hc` | 12,030 × 2,350 × 2,695 |

### 堆高機規格

依 Linde E 系列技術規格。選定的機型決定所需的通道寬度。

| 代碼 | 通道寬（mm） | 車身高（mm） |
|---|---|---|
| `linde_e25` | 1,100 | 2,150 |
| `linde_e30` | 1,150 | 2,150 |
| `linde_e35` | 1,200 | 2,200 |

### CSV 匯入格式

```csv
id,type,L,W,H,weight,quantity,stackable
A001,standard,1200,800,1000,500,3,true
B001,vip,800,600,800,200,1,false
```

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | string | 貨物唯一識別碼 |
| `type` | `standard` / `vip` | VIP 優先裝入最內側 |
| `L`, `W`, `H` | integer（mm） | 尺寸 |
| `weight` | float（kg） | 用於堆疊密度檢查 |
| `quantity` | integer | 相同貨物件數 |
| `stackable` | boolean | 是否允許其他貨物堆疊其上 |

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
