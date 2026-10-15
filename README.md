# StockUp Pulse

StockUp Pulse is a restocking-planning prototype for small retailers and spaza shops in South Africa. It helps an owner review a product catalogue, set a Rand budget, create a budget-capped restocking plan, approve it, and generate supplier order drafts.

The Python allocator is deterministic and currently uses a greedy allocation strategy; it is not a globally optimal integer knapsack solver. It keeps spending within the supplied budget and can use matching scraped prices or explicitly labeled demo fixture prices for substitutions. Verify supplier prices and availability before placing an order.

## Features

- React dashboard with catalogue review, budget controls, plan approval, order drafts, and a WhatsApp simulator.
- FastAPI backend with account registration/login, bearer sessions, owner-scoped plans and orders, and an explicit approval gate. Unapproved order creation returns HTTP 409.
- Streamlit prototype for the planning domain and local SQLite data.
- Deterministic demand-forecasting utilities and an illustrative WAPE fixture. The fixture is not historical sales data or a production accuracy benchmark.
- Best-effort retailer page scraping and local seed prices. Seed records are labeled `demo_fixture`, not verified offers.

## Tech Stack

- **Dashboard:** React 19, TypeScript, Vite, Tailwind CSS, and Lucide icons.
- **Web server/proxy:** Node.js, Express, and Vite middleware. The Express server proxies `/api` requests to FastAPI.
- **Python API:** Python 3.11, FastAPI, Pydantic, SQLModel, SQLite, and Uvicorn.
- **Planning and data:** deterministic Python allocation, NumPy/Pandas forecasting utilities, RapidFuzz matching, HTTPX, and Beautiful Soup scraper.
- **Tests:** pytest and Hypothesis for Python; TypeScript checking and Vite production build for the frontend.

## Integrations

| Integration | Current status |
| --- | --- |
| **AMD Radeon Cloud Token Factory** | Planned, not active. The adapter still uses local fixture extraction and deterministic matching; it does not currently call AMD. The intended OpenAI-compatible base URL is `https://developer.amd.com.cn/radeon/api/v1`. Model IDs should be discovered from `/v1/models` because the catalog changes. |
| **Evolus** | Not configured. Adapter methods return a `not_configured` status; provider document extraction is not connected. |
| **Twilio WhatsApp** | Not configured. `/api/whatsapp/webhook` returns HTTP 501 until signature verification is implemented. The authenticated `/api/whatsapp/simulate` endpoint is a local simulator, not a live WhatsApp channel. |
| **Retailer scraper** | Best-effort public-page scraping is available on demand. Retailers may block requests or change page markup. Seed prices remain demo fixtures. |

External credentials are optional for local development and must not be committed. See the [integration plan](stockup_pulse/INTEGRATION_PLAN.md) for the proposed provider work. The AMD Token Factory key is team-shared, must be redeemed by every team member, and belongs only in a local secret such as `AMD_ROCM_API_KEY`.

## Requirements

- Python 3.11
- Node.js and npm compatible with the installed Vite 8 toolchain
- PowerShell for the commands below; use your shell's equivalent environment activation command on other platforms.

## Setup

Run these commands from the workspace root, the directory containing this README and `stockup_pulse/`.

Create and activate a Python virtual environment, then install the backend requirements:

```powershell
py -3.11 -m venv .venv
& ./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -r stockup_pulse/requirements.txt
Copy-Item stockup_pulse/.env.example stockup_pulse/.env
```

Install the dashboard dependencies:

```powershell
npm install
```

The React app defaults to `/api`; the Express development server forwards those requests to `http://127.0.0.1:8000`. To run FastAPI elsewhere, set `PYTHON_API_URL` in the root `.env` file. For direct browser-to-API requests, set `VITE_API_BASE_URL` in root `.env.local` and include the frontend origin in backend `CORS_ORIGINS`.

## Run the Application

Start the Python API in one terminal:

```powershell
& ./.venv/Scripts/Activate.ps1
python -m uvicorn stockup_pulse.api.main:app --host 127.0.0.1 --port 8000
```

Start the React dashboard and proxy in a second terminal:

```powershell
npm run dev
```

Open `http://localhost:3000`. The FastAPI service is at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

Account registration is required. The old hard-coded demo account and demo login fallback are disabled.

To run the Streamlit prototype instead or alongside the API:

```powershell
& ./.venv/Scripts/Activate.ps1
streamlit run stockup_pulse/app/ui/streamlit_app.py --server.port 8501
```

## Tests and Checks

From the workspace root, with the Python environment activated:

```powershell
python -m pytest -v stockup_pulse/tests/
npx tsc --noEmit
npm run build
```

## Configuration

Backend settings are loaded from `stockup_pulse/.env`; see [the backend environment example](stockup_pulse/.env.example). The frontend's optional `VITE_API_BASE_URL` belongs in root `.env.local`; the Express proxy's optional `PYTHON_API_URL` belongs in root `.env`.

Relevant provider settings include `AMD_ROCM_HOST`, `AMD_ROCM_API_KEY`, `AMD_ROCM_MODEL`, `EVOLUS_ENDPOINT`, `EVOLUS_API_KEY`, `TWILIO_ACCOUNT_SID`, and `TWILIO_AUTH_TOKEN`. Provider integrations remain disabled or incomplete by default. Never put actual API keys in source control, issue reports, or chat.

## Docker

The current `stockup_pulse/docker-compose.yml` references `Dockerfile.api` and `Dockerfile.streamlit`, which are not present yet. Docker Compose will not run until those Dockerfiles are added.