import React, { useState } from 'react';

interface CodeFile {
  path: string;
  name: string;
  description: string;
  category: string;
  content: string;
}

export const CodebaseExplorer: React.FC = () => {
  const codeFiles: CodeFile[] = [
    {
      path: 'app/ingest/live_scraper.py',
      name: 'live_scraper.py',
      category: 'Live Retail Scraper (Async)',
      description: 'Asynchronous scraper for SA retailers using httpx. Catches 401/403/429 (Cloudflare) gracefully and returns [].',
      content: `# Asynchronous South African Retail Scraper
# Handles Cloudflare anti-bot blocks gracefully (401, 403, 429)
class LiveRetailScraper:
    async def fetch_page(self, client: httpx.AsyncClient, url: str):
        response = await client.get(url, timeout=15.0)
        if response.status_code in (401, 403, 429):
            logger.warning("Access denied/rate limited (%d); returning None", response.status_code)
            return None, url
        return BeautifulSoup(response.text, "html.parser"), str(response.url)

    async def scrape_staples_and_sync(self, queries=None, retailers=None):
        # Scrapes Makro, Shoprite, Checkers, Pick n Pay and upserts into live_market_prices`
    },
    {
      path: 'app/core/db.py',
      name: 'db.py',
      category: 'SQLModel & SQLite',
      description: 'SQLModel schema for scraped market records and explicitly labeled demo fixtures.',
      content: `# SQLModel Schema for Live Scraped Market Prices
class LiveMarketPrice(SQLModel, table=True):
    __tablename__ = "live_market_prices"
    id: Optional[int] = Field(default=None, primary_key=True)
    retailer: str = Field(index=True)
    query: str = Field(index=True)
    product_name: str = Field(index=True)
    price_zar: float
    availability: str = Field(default="InStock")

def query_live_market_substitute(product_name: str, original_unit_price: float):
    # Deterministic query: lowest price_zar first, then product_name`
    },
    {
      path: 'planning/optimizer.py',
      name: 'optimizer.py',
      category: 'Planning & Brand Substitution',
      description: 'Deterministic greedy budget allocation with optional price-record substitutions.',
      content: `# Deterministic Restocking Optimizer & Brand Substitution Engine
# Non-negotiables: LLM NEVER generates numbers that drive money.
# Queries live_market_prices SQLite table for cheaper or available equivalents!

class RestockingPlanOptimizer:
    def _find_substitute(self, product_name: str, candidate: Dict[str, Any], current_spend: float, budget: float):
        live_match = query_live_market_substitute(product_name, candidate["unit_price"])
        if live_match:
            return sub_item, sub_qty, sub_cost`
    },
    {
      path: 'orders/manager.py',
      name: 'manager.py',
      category: 'Orders & Approval Gate',
      description: 'Approval guard and order formatting; the API persists owner-scoped orders and references.',
      content: `# Purchase Order Manager with Strict Approval Gate
# Non-negotiable: No purchase order exists until the owner explicitly approves.

class PurchaseOrderManager:
    def create_orders_from_plan(self, plan, approved: bool):
        if not approved or not plan.get("approved", False):
            raise PlanNotApprovedError("Explicit approval required (HTTP 409).")
        # Assigns a date-aware purchase-order reference.`
    },
    {
      path: 'adapters/amd_llm.py',
      name: 'amd_llm.py',
      category: 'Adapters & ROCm Boundary',
      description: 'Local fixture and deterministic heuristic adapter; no AMD provider call is configured.',
      content: `# Model adapter boundary
    # Remote inference is not configured.
# Business logic never imports openai or Evolus directly.

class AmdLlmAdapter:
    def extract_leaflet_text(self, image_data, prompt):
        # 30s timeout, 1 retry, fallback trace
        pass

    def adjudicate_product_match(self, internal_product, candidate_supplier_item, score):
        # Semantic equivalence adjudication (reader/writer only)
        pass`
    },
    {
      path: 'forecast/forecaster.py',
      name: 'forecaster.py',
      category: 'Forecasting & WAPE',
      description: 'Deterministic demand forecasting with WAPE metrics labeled as illustrative fixtures.',
      content: `# Deterministic Demand Forecaster & WAPE Metric
# Weighted Absolute Percentage Error: WAPE = sum(|actual - predicted|) / sum(actual)
def calculate_wape(actual, predicted): ...
class DemandForecaster:
    def forecast_item(self, sales_history, lead_time_days, planning_horizon_days, current_stock): ...
    def evaluate_wape(self): ...`
    },
    {
      path: 'api/main.py',
      name: 'main.py',
      category: 'FastAPI & WhatsApp Webhook',
      description: 'Authenticated FastAPI plans and orders; provider webhook is disabled pending signature verification.',
      content: `# FastAPI Server
@app.post("/api/orders")
def generate_purchase_orders(req: CreateOrderRequest):
    if not req.approved or not current_active_plan.get("approved"):
        raise HTTPException(status_code=409, detail="HTTP 409: Explicit approval gate required.")

@app.post("/api/whatsapp/webhook")
def whatsapp_webhook_not_configured(): ...`
    }
  ];

  const [selectedFile, setSelectedFile] = useState<CodeFile>(codeFiles[0]);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
            REFERENCE NOTES // BACKEND ARCHITECTURE
          </div>
          <h2 className="text-2xl font-black text-white tracking-wider uppercase">
            PYTHON CODEBASE ARCHITECTURE
          </h2>
          <p className="text-xs text-[#888888] mt-1 tracking-wide">
            Illustrative module notes and excerpts; provider integrations are not configured.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-[2px] bg-[#1A1A1A] text-white border border-[#333333] uppercase">
            PYTHON 3.11 // FASTAPI // LOCAL ALLOCATOR
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Files List */}
        <div className="lg:col-span-4 bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-4 shadow-xl space-y-3">
          <div className="text-xs font-mono font-bold text-[#888888] uppercase tracking-wider px-2">
            REPOSITORY MODULES ({codeFiles.length})
          </div>
          <div className="space-y-1">
            {codeFiles.map((file) => {
              const isSelected = selectedFile.path === file.path;
              return (
                <button
                  key={file.path}
                  onClick={() => setSelectedFile(file)}
                  className={`w-full text-left px-3 py-2.5 rounded-[2px] text-xs font-mono transition-all flex items-center justify-between cursor-pointer ${
                    isSelected
                      ? 'bg-[#0B0B0B] text-white font-bold border-l-4 border-[#E50000]'
                      : 'hover:bg-[#0B0B0B]/60 text-[#888888] hover:text-white border-l-4 border-transparent'
                  }`}
                >
                  <span className="truncate">{file.path}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Code Viewer */}
        <div className="lg:col-span-8 bg-[#0B0B0B] text-white rounded-[4px] shadow-2xl border border-[#333333] overflow-hidden">
          <div className="p-4 bg-[#1A1A1A] border-b border-[#333333] flex items-center justify-between">
            <div>
              <div className="text-xs font-mono font-bold text-[#E50000]">
                stockup_pulse/{selectedFile.path}
              </div>
              <div className="text-[11px] text-[#888888] mt-0.5 font-mono">
                {selectedFile.description}
              </div>
            </div>
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 rounded-[2px] bg-[#0B0B0B] hover:bg-[#252525] border border-[#333333] hover:border-[#E50000] text-white text-xs font-mono font-bold uppercase transition-colors cursor-pointer"
            >
              {copied ? 'COPIED' : 'COPY'}
            </button>
          </div>
          <div className="p-5 font-mono text-xs overflow-x-auto text-[#00CC66] bg-[#0B0B0B] leading-relaxed max-h-[500px]">
            <pre>{selectedFile.content}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};
