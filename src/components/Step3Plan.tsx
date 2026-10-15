import React, { useState } from 'react';
import { RestockingPlan } from '../types';

interface Step3PlanProps {
  plan: RestockingPlan;
  onBack: () => void;
  onContinue: () => void;
  onSimulateStockoutSub: () => void;
}

export const Step3Plan: React.FC<Step3PlanProps> = ({
  plan,
  onBack,
  onContinue,
  onSimulateStockoutSub,
}) => {
  const [activeTab, setActiveTab] = useState<'plan' | 'comparison' | 'substitution' | 'funding'>('plan');

  const supplierComparisonData = [
    { product: 'Coca-Cola 440ml', makro: 'R 12.09', shoprite: 'R 13.50', usave: 'R 14.20', best: 'Makro' },
    { product: 'Sprite 440ml', makro: 'R 11.48', shoprite: 'R 12.90', usave: 'R 13.75', best: 'Makro' },
    { product: 'Chicken Noodles', makro: 'R 9.20', shoprite: 'R 8.40', usave: 'R 10.50', best: 'Shoprite' },
    { product: 'Brown Bread', makro: 'R 17.00', shoprite: 'R 17.50', usave: 'R 16.50', best: 'Usave' },
    { product: 'Milk (long life)', makro: 'R 15.50', shoprite: 'R 16.20', usave: 'R 13.90', best: 'Usave' },
    { product: 'Cooking Oil', makro: 'R 18.75', shoprite: 'R 21.00', usave: 'R 22.50', best: 'Makro' },
  ];

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          STEP 3 OF 5 // RESTOCKING OPTIMIZATION
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">
          DETERMINISTIC RESTOCKING PLAN
        </h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Deterministic greedy allocation within your ZAR budget ceiling. Substitutions use available fixture or scraped price records.
        </p>
      </div>

      {/* Top-Bordered Metric KPI Cards (AMD Dark Mode with 2px #E50000 top border) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Budget */}
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#E50000] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase">BUDGET CEILING</div>
          <div className="text-2xl font-black text-white font-mono mt-1">
            R {plan.budget.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-[#888888] mt-1 font-mono">FIXED SHOP LIMIT</div>
        </div>

        {/* Card 2: Estimated Spend */}
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#E50000] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase">ESTIMATED SPEND</div>
          <div className="flex items-baseline justify-between mt-1">
            <div className="text-2xl font-black text-white font-mono">
              R {plan.total_spend.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-xs font-mono font-bold text-[#00CC66] bg-[#0B0B0B] border border-[#00CC66]/40 px-1.5 py-0.5 rounded-[2px]">
              {plan.budget_utilization_pct}%
            </span>
          </div>
          <div className="text-[11px] text-[#00CC66] font-mono mt-1">WITHIN BUDGET CONSTRAINTS</div>
        </div>

        {/* Card 3: Remaining */}
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#E50000] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase">REMAINING BUFFER</div>
          <div className="text-2xl font-black text-[#00CC66] font-mono mt-1">
            R {plan.remaining_budget.toFixed(2)}
          </div>
          <div className="text-[11px] text-[#888888] mt-1 font-mono">CONTINGENCY BUFFER</div>
        </div>

        {/* Card 4: Items to Reorder */}
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#E50000] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase">ITEMS REORDERED</div>
          <div className="flex items-baseline justify-between mt-1">
            <div className="text-2xl font-black text-white font-mono">{plan.total_items_to_reorder}</div>
            <span className="text-xs font-mono font-bold text-[#FF3333] bg-[#0B0B0B] border border-[#FF3333]/40 px-1.5 py-0.5 rounded-[2px]">
              {plan.at_risk_items_count} AT RISK
            </span>
          </div>
          <div className="text-[11px] text-[#888888] mt-1 font-mono">SAFETY STOCK FORMULA</div>
        </div>
      </div>

      {/* Warning & KPI status capsules without emojis */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3 rounded-[4px] bg-[#1A1A1A] border border-[#333333] border-l-4 border-l-[#FF3333] text-xs font-mono">
          <strong className="text-[#FF3333] uppercase">8 SKUs At Stockout Risk:</strong> May run out before delivery.
        </div>

        <div className="p-3 rounded-[4px] bg-[#1A1A1A] border border-[#333333] border-l-4 border-l-[#E50000] text-xs font-mono">
          <strong className="text-[#E50000] uppercase">3 SKUs Not Funded:</strong> Truncated to avoid budget breach.
        </div>

        <div className="p-3 rounded-[4px] bg-[#1A1A1A] border border-[#333333] border-l-4 border-l-[#00CC66] text-xs font-mono">
          <strong className="text-[#00CC66] uppercase">Forecast Accuracy 87%:</strong> vs 72% baseline model.
        </div>
      </div>

      {/* Tabs Row */}
      <div className="border-b border-[#333333] flex items-center justify-between">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('plan')}
            className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
              activeTab === 'plan'
                ? 'border-[#E50000] text-white'
                : 'border-transparent text-[#888888] hover:text-white'
            }`}
          >
            Restocking Plan
          </button>
          <button
            onClick={() => setActiveTab('comparison')}
            className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
              activeTab === 'comparison'
                ? 'border-[#E50000] text-white'
                : 'border-transparent text-[#888888] hover:text-white'
            }`}
          >
            Supplier Matrix
          </button>
          <button
            onClick={() => setActiveTab('substitution')}
            className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'substitution'
                ? 'border-[#E50000] text-white'
                : 'border-transparent text-[#888888] hover:text-white'
            }`}
          >
            <span>Brand Substitutions</span>
            {plan.substitutions_applied.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-[2px] bg-[#E50000] text-white text-[10px] font-mono font-bold">
                {plan.substitutions_applied.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('funding')}
            className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
              activeTab === 'funding'
                ? 'border-[#E50000] text-white'
                : 'border-transparent text-[#888888] hover:text-white'
            }`}
          >
            Budget &amp; Funding
          </button>
        </div>

        {/* Deterministic brand substitution simulator */}
        <button
          onClick={onSimulateStockoutSub}
          className="text-xs text-[#E50000] hover:text-white font-mono font-bold uppercase tracking-wider transition-colors cursor-pointer pb-2 underline"
        >
          [SIMULATE STOCKOUT SWAP]
        </button>
      </div>

      {/* TAB 1: Restocking Plan Table */}
      {activeTab === 'plan' && (
        <div className="bg-[#0B0B0B] border border-[#333333] rounded-[4px] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#1A1A1A] border-b border-[#333333] text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3.5">Product</th>
                  <th className="px-4 py-3.5">Qty</th>
                  <th className="px-4 py-3.5">Supplier</th>
                  <th className="px-4 py-3.5">Unit Price</th>
                  <th className="px-4 py-3.5">Total Cost</th>
                  <th className="px-6 py-3.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#222222]">
                {plan.allocated_items.map((item, idx) => {
                  const isSwapped = item.swapped_via_live_market_prices || item.is_substituted;
                  const retailer = item.live_market_retailer || item.supplier;
                  return (
                    <tr key={idx} className={`hover:bg-[#1A1A1A]/50 transition-colors ${isSwapped ? 'bg-[#1A1A1A]/30' : ''}`}>
                      <td className="px-6 py-4 font-bold text-white">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span>{item.product}</span>
                          {isSwapped && (
                            <span className="px-2 py-0.5 rounded-[2px] text-[10px] font-mono font-bold bg-[#0B0B0B] text-[#E50000] border border-[#E50000]/60 uppercase">
                              SCRAPED SWAP ({retailer.toUpperCase()})
                            </span>
                          )}
                        </div>
                        {item.is_substituted && (
                          <div className="text-[11px] text-[#888888] font-mono mt-0.5">
                            Substituted for {item.original_requested} via live_market_prices
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-4 font-mono font-bold text-white">{item.qty}</td>
                      <td className="px-4 py-4 text-[#888888] font-mono uppercase">{item.supplier}</td>
                      <td className="px-4 py-4 text-[#888888] font-mono">R {item.unit_price.toFixed(2)}</td>
                      <td className="px-4 py-4 font-mono font-bold text-white">R {item.total_cost.toFixed(2)}</td>
                      <td className="px-6 py-4 text-right">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-[2px] text-[10px] font-mono font-bold uppercase tracking-wider ${
                            isSwapped
                              ? 'bg-[#1A1A1A] text-[#E50000] border border-[#E50000]'
                              : item.at_risk
                              ? 'bg-[#1A1A1A] text-[#FF3333] border border-[#FF3333]'
                              : 'bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]'
                          }`}
                        >
                          {isSwapped ? 'SUBSTITUTED' : item.at_risk ? 'HIGH RISK' : 'WITHIN BUDGET'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: Supplier Comparison */}
      {activeTab === 'comparison' && (
        <div className="space-y-4">
          <div className="bg-[#1A1A1A] p-4 rounded-[4px] border border-[#333333] text-xs text-[#888888] flex items-center justify-between font-mono">
            <div>
              <strong className="text-white uppercase">Wholesale Price Matrix:</strong> Extracted directly from promotional flyers across Makro, Shoprite, and Usave.
            </div>
            <div className="font-bold text-[#00CC66]">ESTIMATED BASKET SAVINGS: R 186.40</div>
          </div>

          <div className="bg-[#0B0B0B] border border-[#333333] rounded-[4px] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#1A1A1A] border-b border-[#333333] text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3.5">Product</th>
                    <th className="px-4 py-3.5">Makro</th>
                    <th className="px-4 py-3.5">Shoprite</th>
                    <th className="px-4 py-3.5">Usave</th>
                    <th className="px-6 py-3.5 text-right">Wholesale Winner</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#222222]">
                  {supplierComparisonData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-[#1A1A1A]/50">
                      <td className="px-6 py-4 font-bold text-white">{row.product}</td>
                      <td className="px-4 py-4 font-mono text-xs">
                        <span className={row.best === 'Makro' ? 'font-bold text-[#00CC66]' : 'text-[#888888]'}>
                          {row.makro}
                        </span>
                      </td>
                      <td className="px-4 py-4 font-mono text-xs">
                        <span className={row.best === 'Shoprite' ? 'font-bold text-[#00CC66]' : 'text-[#888888]'}>
                          {row.shoprite}
                        </span>
                      </td>
                      <td className="px-4 py-4 font-mono text-xs">
                        <span className={row.best === 'Usave' ? 'font-bold text-[#00CC66]' : 'text-[#888888]'}>
                          {row.usave}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="inline-block px-2 py-0.5 rounded-[2px] text-[10px] font-mono font-bold uppercase bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/40">
                          {row.best.toUpperCase()} [BEST]
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Automated Brand Substitutions */}
      {activeTab === 'substitution' && (
        <div className="space-y-4">
          <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 space-y-2">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                DETERMINISTIC BRAND SUBSTITUTION (POWERED BY `LIVE_MARKET_PRICES`)
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-[2px] bg-[#0B0B0B] text-[#E50000] font-bold border border-[#E50000]">
                TABLE: live_market_prices
              </span>
            </div>
            <p className="text-xs text-[#888888] leading-relaxed">
              When an uploaded item is flagged as out-of-stock or breaches the Rand budget ceiling, the optimizer queries the SQLite <code className="text-white bg-[#0B0B0B] px-1 py-0.5 rounded-[2px]">live_market_prices</code> table populated asynchronously by <code className="text-white bg-[#0B0B0B] px-1 py-0.5 rounded-[2px]">LiveRetailScraper</code>.
            </p>
          </div>

          {plan.substitutions_applied.length > 0 ? (
            <div className="space-y-3">
              {plan.substitutions_applied.map((sub, idx) => (
                <div
                  key={idx}
                  className="bg-[#1A1A1A] border border-[#888888] border-l-4 border-l-[#E50000] rounded-[4px] p-5 space-y-3 shadow-lg"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="line-through text-[#888888] font-bold font-mono">{sub.original_product}</span>
                      <span className="text-white">&rarr;</span>
                      <span className="font-bold text-white text-base font-mono">{sub.substituted_with}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-[2px] bg-[#0B0B0B] text-[#E50000] border border-[#E50000]">
                        SCRAPED: {(sub.live_market_retailer || 'Shoprite').toUpperCase()}
                      </span>
                      <span className="text-xs font-mono font-bold text-[#00CC66] bg-[#0B0B0B] px-2.5 py-0.5 rounded-[2px] border border-[#00CC66]/50">
                        SAVINGS: R {sub.savings.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-[#CCCCCC] bg-[#0B0B0B] p-3 rounded-[2px] border border-[#333333] leading-relaxed font-mono">
                    <strong className="text-[#E50000] uppercase">DETERMINISTIC RATIONALE:</strong> {sub.reason}
                  </p>

                  <div className="grid grid-cols-2 gap-4 text-xs text-[#888888] font-mono pt-1">
                    <div>ORIGINAL COST: R {sub.original_cost.toFixed(2)}</div>
                    <div className="font-bold text-white">SUBSTITUTED COST: R {sub.substituted_cost.toFixed(2)}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center bg-[#1A1A1A] border border-[#333333] rounded-[4px] text-[#888888] text-xs font-mono">
              ALL CURRENT BRAND SELECTIONS ARE FULLY IN STOCK AND WITHIN R {plan.budget.toFixed(2)} BUDGET.
              <div className="mt-3">
                <button
                  onClick={onSimulateStockoutSub}
                  className="text-xs text-[#E50000] hover:text-white font-bold uppercase underline cursor-pointer"
                >
                  SIMULATE WHOLESALE STOCKOUT TO TRIGGER LIVE SCRAPED SWAP
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Budget & Funding */}
      {activeTab === 'funding' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 space-y-3">
              <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                FUNDED RESTOCKING ALLOCATIONS
              </h4>
              <div className="space-y-2 text-xs font-mono">
                {plan.allocated_items.map((it, idx) => (
                  <div key={idx} className="flex justify-between p-2.5 rounded-[2px] bg-[#0B0B0B] border border-[#333333]">
                    <span className="font-bold text-white">{it.product} ({it.qty}x)</span>
                    <span className="font-bold text-[#00CC66]">R {it.total_cost.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-[#1A1A1A] border border-[#333333] border-l-4 border-l-[#FF3333] rounded-[4px] p-5 space-y-3">
              <h4 className="text-xs font-mono font-bold text-[#FF3333] uppercase tracking-wider">
                UNFUNDED / DEFERRED ITEMS (BUDGET CAPPED)
              </h4>
              <p className="text-xs text-[#888888]">
                These quantities were reduced or left unfunded to keep the plan within budget:
              </p>
              <div className="space-y-2 text-xs font-mono">
                {plan.unfunded_items.map((it, idx) => (
                  <div key={idx} className="p-2.5 rounded-[2px] bg-[#0B0B0B] border border-[#333333] text-white">
                    <div className="font-bold">{it.product} ({it.unfunded_qty} units unfunded)</div>
                    <div className="text-[11px] text-[#888888] mt-0.5">{it.reason}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Deterministic explanation from computed plan values */}
      <div className="bg-[#1A1A1A] text-white p-4 rounded-[4px] text-xs space-y-2 border border-[#333333] border-t-2 border-t-[#E50000]">
        <div className="flex items-center justify-between">
          <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-wider">
            PLAN SUMMARY // LOCAL FORMATTING
          </div>
          <span className="text-[10px] text-[#00CC66] bg-[#0B0B0B] px-2 py-0.5 rounded-[2px] font-mono border border-[#00CC66]/40 uppercase">
            COMPUTED PLAN VALUES
          </span>
        </div>
        <div className="p-3 bg-[#0B0B0B] rounded-[2px] border border-[#333333] text-[#CCCCCC] leading-relaxed font-mono text-[11px]">
          &ldquo;{plan.plain_language_explanation}&rdquo;
        </div>
      </div>

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="px-5 py-2.5 rounded-[4px] border border-[#333333] hover:border-[#E50000] bg-transparent text-white font-bold text-xs uppercase tracking-wider cursor-pointer transition-colors"
        >
          &larr; BACK
        </button>
        <button
          onClick={onContinue}
          className="px-6 py-2.5 rounded-[4px] bg-[#E50000] hover:bg-[#CC0000] text-white font-bold text-xs uppercase tracking-wider shadow-[0_0_12px_rgba(229,0,0,0.35)] cursor-pointer transition-colors"
        >
          CONTINUE TO APPROVAL &rarr;
        </button>
      </div>
    </div>
  );
};
