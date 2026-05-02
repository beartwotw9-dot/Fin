# 個人金融網站

這個 repo 是自用的個人金融網站，整合台股 / 美股報價、深色終端風格儀表板、K 線圖與策略回測篩選系統。

## 技術棧

- 前端：Next.js 14 + TypeScript + Tailwind CSS
- 後端：FastAPI + Python 3.11+
- 資料來源：FinMind（台股）+ yfinance（美股 / ETF）
- 圖表：TradingView Lightweight Charts + Recharts
- 回測：backtesting.py + pandas + numpy
- 部署：Vercel（前端）+ Render（後端）

## 專案結構

```text
.
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── chart/[id]/page.tsx
│   │   └── backtest/page.tsx
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── vercel.json
├── backend/
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── data/watchlist.json
│   ├── requirements.txt
│   ├── render.yaml
│   └── .env.example
└── README.md
```

## 本地啟動

### 後端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 環境變數

### `backend/.env`

```env
FINMIND_TOKEN=
FRONTEND_URL=http://localhost:3000
```

- `FINMIND_TOKEN`：到 [finmindtrade.com](https://finmindtrade.com/) 免費註冊後取得。
- `FRONTEND_URL`：部署後前端網址，供 FastAPI CORS 使用。

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## FinMind 免費方案

- 有 token 且完成信箱驗證：600 次 / 小時
- 無 token 匿名：300 次 / 小時

沒有 token 也能跑，但台股資料額度會比較低。

## 回測篩選邏輯

### 五大必過門檻

全部通過才算 `PASSED`：

1. Sharpe Ratio `>= 0.75`
2. Max Drawdown `>= -30%`
3. Win Rate `>= 40%`
4. Total Trades `>= 10`
5. Profit Factor `>= 1.2`

### 進階觀察指標

- Calmar Ratio
- Sortino Ratio
- Recovery Factor

### Walk-Forward 驗證

資料切分：

- In-Sample：前 60%
- Validation：中 20%
- Out-of-Sample：後 20%

流程：

1. 用 In-Sample 找最佳參數
2. 用 Validation 幫助選參數
3. 固定參數跑 OOS
4. 計算 `WF Efficiency = OOS Return / IS Return`

判讀：

- `> 0.7`：`ROBUST`
- `0.5 ~ 0.7`：`MARGINAL`
- `< 0.5`：`OVERFIT`

### 參數穩健性測試

最佳參數會再做 `±10%` 測試，若 Sharpe 標準差 `< 0.3`，代表策略較穩健。

## 台股費率提醒

- 股票手續費常見：`0.1425%`
- 股票交易稅：`0.3%`
- ETF 交易稅：`0.1%`

常見估法：

- 股票：`0.001425 + 0.003 = 0.004425`
- ETF（0050 / 006208）：`0.001425 + 0.001 = 0.002425`

## 部署

### Render 後端

1. 將 repo 推到 GitHub
2. 在 Render 建立 Web Service
3. Root Directory 指到 `backend`
4. Build Command：`pip install -r requirements.txt`
5. Start Command：`uvicorn main:app --host 0.0.0.0 --port $PORT`
6. 設定環境變數：
   - `FINMIND_TOKEN`
   - `FRONTEND_URL`

### Vercel 前端

1. 匯入同一個 repo
2. Root Directory 指到 `frontend`
3. 設定：

```env
NEXT_PUBLIC_API_URL=https://your-render-url.onrender.com
```

4. 部署完成後，把前端正式網址填回後端 `FRONTEND_URL`
