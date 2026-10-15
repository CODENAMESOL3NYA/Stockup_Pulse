# StockUp Pulse - AMD Hackathon ACT III (Reinvent Commerce)

> **Smarter stock. Stronger shops.**  
> An AI restocking agent for small retailers (Spaza shops in South Africa) with no point-of-sale system.

---

## 🎯 Problem & Product
Small retailers and township spaza shops in South Africa operate on thin margins with no expensive point-of-sale systems. Restocking is done manually from chaotic, promotional wholesale flyers (Makro, Jumbo, Shoprite, Usave). Overbuying locks up critical cash; underbuying leads to empty shelves.

**StockUp Pulse** provides:
1. **Budget-Capped Allocation:** A deterministic greedy allocator caps spending at the owner's Rand budget; it is not a globally optimal integer knapsack solver.
2. **Brand Substitution:** Substitutions use live scrape records when available, otherwise configured rules or illustrative seed prices. Seed prices are not verified offers.
3. **Interfaces:** The React dashboard and Streamlit prototype use the Python domain code. Leaflet extraction is available when AMD or Evolus is fully configured; WhatsApp inbound approval is optional and outbound supplier delivery remains disabled.

---

## 🛡️ Non-Negotiable Principles

1. **Money Calculations Are Deterministic:**  
   Only deterministic Python code computes allocation quantities and totals. External model adapters are optional and disabled by default; local fixture extraction and heuristic matching are labeled as such.

2. **Strict Approval Gate (HTTP 409):**  
   Authenticated API orders require an owner-approved, owner-scoped plan. An unapproved plan returns HTTP 409.

3. **Traceability (Evidence over Logos):**  
   Trace summaries count actual external calls; local heuristics and fixtures do not claim provider calls or fabricated tokens.

4. **Boundary Adapters:**
   - `adapters/amd_llm.py`: AMD image-extraction adapter; requires an enabled provider and an image-capable configured model.
   - `adapters/evolus.py`: Evolus workflow adapter; requires the endpoint, API key, application ID, and workflow ID.
   *Business logic never imports openai or Evolus SDKs directly.*

5. **Resilience:**
   The scraper uses bounded HTTP timeouts and handles common blocks. Provider requests have bounded timeouts and retry transient failures; failures are surfaced rather than treated as successful extraction.

6. **Determinism:**
   The allocator serializes its result with sorted keys and a fixed seed. Database plan IDs and creation timestamps are intentionally outside that deterministic result.

7. **Brand Substitution (No Pooling):**  
   Deterministic brand substitution replaces out-of-stock items with comparable extracted items while respecting the Rand budget.

8. **Honesty:**
   The included benchmark and seed prices are illustrative fixtures, not verified retail or historical sales data. The metrics endpoint labels its fixture and sample count; no production accuracy claim is made.

---

## 📂 Repository Layout
```
stockup_pulse/
├── .env.example
├── requirements.txt
├── app/
│   └── ui/
│       └── streamlit_app.py        # Streamlit prototype
├── api/
│   └── main.py                     # FastAPI backend and authenticated simulator
├── core/
│   └── config.py                   # Pydantic settings & timeouts
├── ingest/
│   └── extract/
│       └── leaflet_extractor.py    # Promotional flyer vision extractor
├── catalogue/
│   └── matcher.py                  # RapidFuzz string distance & LLM adjudication
├── forecast/
│   └── forecaster.py               # Deterministic forecaster & WAPE benchmark
├── planning/
│   └── optimizer.py                # Budget-constrained optimizer & brand substitution
├── agent/
│   └── orchestrator.py             # Restocking agent coordinator
├── adapters/
│   ├── amd_llm.py                  # Model adapter boundary; currently fixture-backed
│   └── evolus.py                   # Optional configured-workflow provider adapter
├── orders/
│   └── manager.py                  # Purchase orders & HTTP 409 approval gate
├── trace/
│   └── tracker.py                  # Hardware audit & trace recorder
└── tests/
    ├── test_optimizer.py           # Determinism & budget tests
    ├── test_approval_gate.py       # HTTP 409 gate tests
    ├── test_hypothesis.py          # Property-based testing
   ├── test_forecast_wape.py       # Fixture metric validation
   ├── test_adapters.py            # Adapter status and trace tests
   ├── test_api_security.py        # Authentication and owner-isolation tests
   └── test_scraper.py             # Retail price parsing tests
```

---

## 🚀 Running the System

Run the following commands from the workspace root (the directory containing `stockup_pulse/`).

### 0. Install Python Dependencies
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r stockup_pulse/requirements.txt
Copy-Item stockup_pulse/.env.example stockup_pulse/.env
Copy-Item .env.example .env.local
```

The React development server proxies `/api` to FastAPI at `http://127.0.0.1:8000`; set `PYTHON_API_URL` if it runs elsewhere. For direct browser-to-API access, set `VITE_API_BASE_URL` in `.env.local` to the API URL and add the frontend origin to `CORS_ORIGINS`. Configure provider credentials only when those providers are available. Registration is required; the old demo account is intentionally disabled.

### 1. Run Tests
```bash
python -m pytest -v stockup_pulse/tests/
```

### 2. Run API
```bash
python -m uvicorn stockup_pulse.api.main:app --host 127.0.0.1 --port 8000
```

### 3. Run React Dashboard
```bash
npm install
npm run dev
```

### 4. Run Streamlit Prototype
```bash
streamlit run stockup_pulse/app/ui/streamlit_app.py --server.port 8501
```

### 5. Docker
Docker deployment is not supported yet: the repository does not include backend or Streamlit Dockerfiles. Run the API and dashboard using the commands above.
