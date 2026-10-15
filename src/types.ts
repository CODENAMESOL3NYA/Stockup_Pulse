export interface ProductItem {
  id: string;
  product: string;
  pack_size: string;
  supplier_price: number;
  our_price: number;
  unit_price: number;
  supplier: string;
  status: 'Confirmed' | 'Needs review' | 'Unmatched';
  confidence: number;
  recommended_qty: number;
  at_risk: boolean;
  is_out_of_stock: boolean;
  category: string;
  source?: 'file_import';
  reviewed?: boolean;
  lead_time_days?: number;
  retail_price_verified?: boolean;
  currency?: string;
  currency_verified?: boolean;
}

export interface AllocatedItem {
  product: string;
  original_requested?: string;
  qty: number;
  supplier: string;
  unit_price: number;
  total_cost: number;
  status: string;
  is_substituted: boolean;
  swapped_via_live_market_prices?: boolean;
  live_market_retailer?: string;
  at_risk: boolean;
}

export interface BrandSubstitution {
  original_product: string;
  substituted_with: string;
  original_cost: number;
  substituted_cost: number;
  savings: number;
  reason: string;
  swapped_via_live_market_prices?: boolean;
  live_market_retailer?: string;
}

export interface UnfundedItem {
  product: string;
  unfunded_qty: number;
  reason: string;
}

export interface RestockingPlan {
  plan_id?: string;
  plan_version: string;
  seed: number;
  approved: boolean;
  budget: number;
  total_spend: number;
  remaining_budget: number;
  budget_utilization_pct: number;
  total_items_to_reorder: number;
  at_risk_items_count: number;
  unfunded_items_count: number;
  allocated_items: AllocatedItem[];
  substitutions_applied: BrandSubstitution[];
  unfunded_items: UnfundedItem[];
  supplier_breakdown: Record<string, {
    supplier: string;
    total_spend: number;
    items_count: number;
    items: AllocatedItem[];
  }>;
  plain_language_explanation?: string;
}

export interface PurchaseOrder {
  order_number: string;
  supplier: string;
  store_name: string;
  total_items: number;
  total_spend: number;
  status: string;
  delivery_status?: 'queued' | 'sent' | 'failed' | 'not_sent';
  items: AllocatedItem[];
  whatsapp_message: string;
}

export interface TraceEvent {
  id: string;
  timestamp: string;
  event_type: string;
  device: string;
  rocm_version: string;
  model: string;
  endpoint_host: string;
  evolus_block?: string;
  latency_ms: number;
  tokens_prompt: number;
  tokens_completion: number;
  tokens_total: number;
  status: string;
  details: Record<string, any>;
}

export interface WapeMetrics {
  model_wape: number;
  baseline_wape: number;
  forecast_accuracy: number;
  baseline_accuracy: number;
  dataset_type?: string;
  sample_count?: number;
}

export interface AuthUser {
  phone: string;
  full_name: string;
  shop_name: string;
}

export interface ImportForecast {
  daily_demand_forecast: number;
  safety_stock: number;
  horizon_demand: number;
  recommended_qty: number;
  runout_days: number;
  at_risk_before_delivery: boolean;
  lead_time_days: number;
}

export interface ImportAvailableProduct {
  normalized_key: string;
  name: string;
  ambiguous: boolean;
  sales_history: number[];
  current_stock: number | null;
}

export interface FileImportCandidate {
  id: string;
  product: string;
  pack_size: string;
  pack_count: number | null;
  supplier_price: number | null;
  unit_price: number | null;
  our_price: number | null;
  supplier: string;
  variant?: string | null;
  currency?: string | null;
  availability?: string | null;
  evidence?: string | null;
  currency_verified?: boolean;
  confidence: number;
  source: string;
  source_filename: string;
  warnings?: string[];
  matched_product: string;
  lead_time_days: number | null;
  current_stock: number | null;
  sales_history: number[] | null;
  forecast: ImportForecast | null;
  recommended_qty: number | null;
  at_risk: boolean;
  issues: string[];
  status: 'Needs review';
  retail_price_verified?: boolean;
  include?: boolean;
}

export interface FileImportReview {
  status: string;
  sales_interval: { start: string; end: string };
  candidates: FileImportCandidate[];
  available_products: ImportAvailableProduct[];
  source_files: Array<{ filename: string; kind: string }>;
  providers: Record<string, { enabled: boolean }>;
}

export interface FileImportJobStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  result?: FileImportReview;
  error?: string;
}

export interface ProviderCapabilities {
  amd_image_extraction: { enabled: boolean };
  evolus_pdf_extraction: { enabled: boolean };
  twilio_inbound_webhook: { enabled: boolean };
  supplier_dispatch: { enabled: boolean };
}
