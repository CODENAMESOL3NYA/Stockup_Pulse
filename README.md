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
| **AMD Radeon Cloud Token Factory** | Image extraction is implemented and disabled by default. It validates `AMD_ROCM_MODEL` against live `/v1/models` image capability metadata. |
| **Evolus** | Configured-workflow PDF extraction is implemented and disabled by default. Sandbox workflow result compatibility must be confirmed before enabling it. |
| **Twilio WhatsApp** | Inbound signature verification and owner-scoped approval are implemented and disabled by default. The authenticated `/api/whatsapp/simulate` endpoint remains a local simulator. Outbound supplier delivery is disabled. |
| **Retailer scraper** | Best-effort public-page scraping is available on demand. Retailers may block requests or change page markup. Seed prices remain demo fixtures. |

External credentials are optional for local development and must not be committed. See the [integration plan](stockup_pulse/INTEGRATION_PLAN.md) for the provider contracts and rollout criteria. The AMD Token Factory key is team-shared, must be redeemed by every team member, and belongs only in a local secret such as `AMD_ROCM_API_KEY`.

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

Provider integrations are off by default. To enable them, set the corresponding `*_ENABLED` flag and all required values in the local `stockup_pulse/.env` file:

| Provider | Required settings |
| --- | --- |
| AMD image extraction | `AMD_ROCM_ENABLED`, `AMD_ROCM_HOST`, `AMD_ROCM_API_KEY`, and an exact `AMD_ROCM_MODEL` from the live catalog |
| Evolus PDF extraction | `EVOLUS_ENABLED`, `EVOLUS_ENDPOINT`, `EVOLUS_API_KEY`, `EVOLUS_APPLICATION_ID`, and `EVOLUS_WORKFLOW_ID` |
| Twilio inbound webhook | `TWILIO_WEBHOOK_ENABLED`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and the externally reachable canonical `TWILIO_WEBHOOK_PUBLIC_URL` |

For Evolus, copy the application ID and workflow ID for the document-extraction workflow from your Evolus setup into `stockup_pulse/.env`; setting only `EVOLUS_ENABLED=true` and an API key is not sufficient. Restart the FastAPI process after changing this file, then confirm `evolus_pdf_extraction.enabled` is `true` from `http://127.0.0.1:8000/api/providers`.

`AMD_ROCM_MODEL` has no default: the configured preference must exist in AMD's live model catalog and explicitly support image input. The backend environment example lists the supplied model IDs, but catalog availability and capability must be checked at runtime. `OUTBOUND_SUPPLIER_DISPATCH_ENABLED` is intentionally disabled; supplier recipients and opt-ins are not configured. Never put actual API keys in source control, issue reports, or chat.

### File import formats

The authenticated upload accepts 1–5 CSV, XLSX, PDF, JPG/JPEG, or PNG files (10 MiB per file, 25 MiB total file payload). FastAPI enforces the per-file and combined file limits; the Express proxy caps streamed multipart and URL-encoded request bodies at 26 MiB to allow multipart envelope overhead. CSV/XLSX data is parsed locally; images require the AMD provider and PDFs require the configured Evolus workflow. An upload-based review needs sales rows, stock rows, and at least one leaflet or PDF. Provider extraction is all-or-nothing; no plan is saved until reviewed candidates are submitted through the normal planning flow.

CSV sales headers are exactly `date,product,quantity_sold`, with ISO `YYYY-MM-DD` dates. CSV stock headers are `product,current_stock`. Quantities must be finite and nonnegative and use sellable units. A workbook may contain `sales` and `stock` sheets with the corresponding headers. Duplicate sales rows aggregate by normalized product and date; conflicting duplicate stock rows are rejected. Missing calendar days inside the imported sales interval are zero-filled.

Example sales CSV:

```csv
date,product,quantity_sold
2025-01-01,Brown Bread,8
2025-01-02,Brown Bread,6
```

Example stock CSV:

```csv
product,current_stock
Brown Bread,4
```

Uploaded leaflet items require owner review of product mapping, pack/unit cost, verified per-unit retail price, and supplier lead time before planning. Provider status is available from `/api/providers`; it never returns credentials. After setup, run the tests and frontend checks listed above. Real AMD/Evolus/Twilio sandbox verification remains an explicit rollout prerequisite.

## Docker

The current `stockup_pulse/docker-compose.yml` references `Dockerfile.api` and `Dockerfile.streamlit`, which are not present yet. Docker Compose will not run until those Dockerfiles are added.