# 3D Container Packing System

> — 3D Bin-Packing with forklift aisle constraints, real-time visualization, and full-stack Docker deployment.

**Live Demo → [wutesta0101-hu.github.io/container-packing](https://wutesta0101-hue.github.io/container-packing)**

![System Architecture](https://github.com/user-attachments/assets/6ba09142-ebe9-4dba-a0c6-2232e10eb9a9)

---

## What It Does

Upload cargo data (manual input or CSV), and the system calculates an optimal 3D loading plan for a shipping container — respecting physical constraints most bin-packing demos ignore:

- **Forklift aisle clearance**: every item must be reachable by a forklift entering from the door; the algorithm enforces this geometrically, not just as a heuristic
- **Stacking rules**: items can only be stacked on stackable cargo, and only if the upper item's density ≤ 105% of the supporting item's density
- **VIP priority**: designated high-value cargo is packed into the innermost positions first
- **Inside-out loading order**: packing proceeds from the rear of the container toward the door, matching real forklift workflow

Results are rendered in interactive 3D (Three.js) with X-ray mode, step-by-step playback, and a utilization / center-of-gravity dashboard.

---

## System Architecture

```
┌─────────────────────────────────────────┐
│           Frontend (React + Vite)        │
│                                         │
│  LeftPanel      CenterCanvas  RightPanel │
│  ├ ContainerSelector  ├ ContainerScene  ├ UtilizationCard │
│  ├ CargoForm          ├ CargoBoxes      ├ WeightCard      │
│  ├ CsvDropzone        ├ ViewControls   ├ DirectionCard   │
│  ├ CargoList          └ PlaybackBar    └ LegendCard      │
│  └ SummaryPanel                                          │
│                                                          │
│  State: Zustand (useCargoStore)                          │
│  API:   apiClient.js → HTTP/JSON                         │
└─────────────────┬───────────────────────┘
                  │ POST /api/v1/pack
                  │ GET  /api/v1/results/{id}
┌─────────────────▼───────────────────────┐
│           Backend (FastAPI)              │
│                                         │
│  routes/pack.py      schemas/           │
│  ├ POST /api/v1/pack  └ Pydantic        │
│  └ GET  /results/{id}   Request/Response│
│                                         │
│  services/packing_service.py            │
│  ├ Expand quantity                      │
│  ├ VIP sort + density sort              │
│  └ Orchestrate algorithm + DB write     │
│                                         │
│  algorithm/packing.py  ←── Core         │
│  ├ 3DBPP (BLB anchor-point method)      │
│  ├ Collision detection                  │
│  ├ Stacking constraint                  │
│  └ Forklift aisle constraint            │
│                                         │
│  db/repository.py (SQLAlchemy ORM)      │
│  └ Tasks + PackedItems tables           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       PostgreSQL 16 (Docker)             │
└─────────────────────────────────────────┘
```

---

## Core Algorithm

The packing engine (`algorithm/packing.py`) implements a **3D Bottom-Left-Back (BLB)** anchor-point algorithm. Each item is placed at the first feasible anchor point that passes four sequential physical constraints.

### Coordinate System

Origin `(0, 0, 0)` = rear-left-bottom corner of the container. The door is at `x = L_container`.

```
z (height)
│
│    y (width)
│   ╱
│  ╱
│ ╱
└──────── x (depth, toward door)
```

### 1. Sorting Strategy

Items are sorted by a three-key priority before packing begins:

$$\text{sort key} = \bigl(\neg\,\text{is\_vip},\ -V_i,\ -m_i\bigr)$$

where $V_i = L_i \times W_i \times H_i$ is item volume and $m_i$ is weight. VIP items always land deepest (innermost), matching real inside-out loading order.

### 2. Anchor-Point Placement

After placing item $k$ at position $(x_k, y_k, z_k)$, three new candidate anchors are generated:

$$A_{k+1} = \bigl\{(x_k + L_k,\ y_k,\ z_k),\ (x_k,\ y_k + W_k,\ z_k),\ (x_k,\ y_k,\ z_k + H_k)\bigr\}$$

Anchors are tried in lexicographic order $(x, z, y)$ — deepest first, then lowest, then leftmost — which produces dense, floor-hugging arrangements.

### 3. Constraint Stack

Every candidate position $(x, y, z)$ must pass four checks in order:

**① Boundary**

$$x + L_i \leq L_c \quad \land \quad y + W_i \leq W_c \quad \land \quad z + H_i \leq H_c$$

**② Collision (AABB)**

For every placed item $p$, no axis-aligned bounding box overlap:

$$x + L_i \leq p.x \;\lor\; p.x + p.L \leq x \;\lor\; y + W_i \leq p.y \;\lor\; \cdots$$

**③ Stacking Support**

If $z > 0$, the item must rest on at least one stackable support. Three sub-conditions must all hold:

- All supports have `stackable = True`
- Density constraint (heavy-below rule with 5% tolerance):

$$\rho_{\text{upper}} \leq \rho_{\text{support}} \times 1.05$$

- Support coverage ≥ 90% of the item's base area (prevents excessive overhang):

$$\frac{\text{Area}\!\left(\bigcup_s \text{proj}(s) \cap \text{base}(i)\right)}{L_i \times W_i} \geq 0.9$$

The union area is computed exactly via a sweep-line algorithm in $O(N^2)$.

**④ Forklift Aisle Clearance**

The corridor between the candidate item and the container door must be free of obstructions within the forklift's operating envelope. Fork-reach tolerance $r = 0.9 \times l_{\text{fork}}$ allows the forks to partially slide under the next item:

$$\forall\, p \in \text{placed} : \quad p.x \geq x + L_i + r \implies \neg\bigl(Y_{\text{overlap}}(p) \land p.z < H_{\text{forklift}}\bigr)$$

where $Y_{\text{overlap}}$ checks if $p$ falls within the aisle width $\max(W_i, W_{\text{forklift}})$ centered on the item's Y midpoint.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite, Three.js, Zustand, Axios |
| 3D Rendering | Three.js r128 (custom OrbitControls) |
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy ORM |
| Containerization | Docker + Docker Compose |
| Frontend Serving | Nginx (production build) |

---

## Quick Start

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin)
- Git

### 1. Clone

```bash
git clone https://github.com/wutesta0101-hue/container-packing.git
cd container-packing
```

### 2. Configure Environment

```bash
cp .env.docker.example .env.docker
# Edit .env.docker if you want to change DB credentials (defaults work out of the box)
```

### 3. Build and Start

```bash
docker compose up -d
```

This starts four services:

| Service | URL | Purpose |
|---|---|---|
| Frontend | http://localhost | React app (Nginx) |
| Backend | internal only | FastAPI (port 9000) |
| PostgreSQL | internal only | Database |
| pgAdmin | http://localhost:8080 | DB management UI |

### 4. Verify

```bash
docker compose ps          # All services should show "running"
docker compose logs backend  # Should show "Uvicorn running"
```

Open http://localhost — the packing interface should load.

### Stop

```bash
docker compose down          # Stop (data preserved)
docker compose down -v       # Stop + wipe database
```

---

## API Reference

### POST `/api/v1/pack`

Submit cargo data and trigger the packing algorithm.

```json
// Request
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

// Response
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

### GET `/api/v1/results/{task_id}`

Retrieve a previously computed result.

---

## Project Structure

```
container-packing/
├── backend/
│   ├── algorithm/
│   │   └── packing.py          ← 3DBPP core (pure functions, unit-testable)
│   ├── db/
│   │   └── repository.py       ← SQLAlchemy ORM, Tasks + PackedItems
│   ├── routes/
│   │   └── pack.py             ← FastAPI route handlers
│   ├── schemas/                ← Pydantic request/response models
│   ├── services/
│   │   └── packing_service.py  ← Business logic, orchestration
│   ├── core/
│   │   └── config.py           ← .env, CORS settings
│   ├── tests/                  ← Unit tests for algorithm
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LeftPanel/      ← Input forms, CSV upload, cargo list
│   │   │   ├── CenterCanvas/   ← Three.js 3D scene
│   │   │   └── RightPanel/     ← Dashboard cards
│   │   ├── store/
│   │   │   └── useCargoStore.js ← Zustand global state
│   │   └── api/
│   │       └── apiClient.js    ← Axios, all backend calls
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── docker-compose.override.yml ← Dev overrides (expose ports, hot reload)
└── .env.docker.example
```

---

## Supported Containers

| Code | Dimensions (L × W × H mm) |
|---|---|
| `20ft` | 5,900 × 2,350 × 2,390 |
| `40ft` | 12,030 × 2,350 × 2,390 |
| `40ft_hc` | 12,030 × 2,350 × 2,695 |

## Supported Forklifts

Based on Linde E-series technical specifications:

| Code | Width (mm) | Body Height (mm) |
|---|---|---|
| `linde_e25` | 1,100 | 2,150 |
| `linde_e30` | 1,150 | 2,150 |
| `linde_e35` | 1,200 | 2,200 |

---

## CSV Import Format

Upload a `.csv` file with the following columns:

```csv
id,type,L,W,H,weight,quantity,stackable
A001,standard,1200,800,1000,500,3,true
B001,vip,800,600,800,200,1,false
```

| Column | Type | Description |
|---|---|---|
| `id` | string | Unique cargo identifier |
| `type` | `standard` / `vip` | VIP items are packed first (innermost) |
| `L`, `W`, `H` | integer (mm) | Dimensions |
| `weight` | float (kg) | Used for stacking density check |
| `quantity` | integer | Number of identical units |
| `stackable` | boolean | Whether other items can be placed on top |


