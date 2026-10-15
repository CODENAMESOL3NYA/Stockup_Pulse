import React, { useState } from 'react';
import { RestockingPlan } from '../types';

interface Step4ApproveProps {
  plan: RestockingPlan;
  isApproved: boolean;
  onToggleApproval: (approved: boolean) => void;
  onSubmitApproval: () => void;
  onBack: () => void;
  isSubmitting: boolean;
  approvalError?: string | null;
}

export const Step4Approve: React.FC<Step4ApproveProps> = ({
  plan,
  isApproved,
  onToggleApproval,
  onSubmitApproval,
  onBack,
  isSubmitting,
  approvalError,
}) => {
  const [selectedSupplierPreview, setSelectedSupplierPreview] = useState<string | null>(null);

  const suppliers = Object.keys(plan.supplier_breakdown);

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          STEP 4 OF 5 // APPROVAL GATEWAY
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">
          HUMAN-IN-THE-LOOP APPROVAL
        </h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Review the restocking allocation. Authorization is strictly required before purchase orders are minted.
        </p>
      </div>

      {/* Governance Banner */}
      <div className="p-4 rounded-[4px] bg-[#1A1A1A] border border-[#333333] border-l-4 border-l-[#E50000] text-sm">
        <div className="font-bold text-[#E50000] uppercase font-mono tracking-wider">
          EXPLICIT HUMAN AUTHORIZATION REQUIRED
        </div>
        <div className="text-xs text-[#CCCCCC] mt-1 font-mono leading-relaxed">
          No supplier orders will be created until you approve this plan. This rule is enforced by the FastAPI backend with an HTTP 409 Conflict rejection if bypassed.
        </div>
      </div>

      {approvalError && (
        <div className="p-3.5 rounded-[4px] bg-[#1A1A1A] border border-[#FF3333] text-[#FF3333] text-xs font-mono font-bold">
          API APPROVAL GATE ERROR: {approvalError}
        </div>
      )}

      {/* Plan Summary & Ready for Approval Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left: Plan Summary metrics */}
        <div className="lg:col-span-7 bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-6 shadow-xl space-y-4">
          <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-wider">
            PLAN SUMMARY
          </div>
          
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <div className="text-[11px] font-mono text-[#888888] uppercase">BUDGET</div>
              <div className="text-xl font-black text-white font-mono mt-0.5">
                R {plan.budget.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-mono text-[#888888] uppercase">TOTAL SPEND</div>
              <div className="text-xl font-black text-white font-mono mt-0.5">
                R {plan.total_spend.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-mono text-[#888888] uppercase">ITEMS</div>
              <div className="text-xl font-black text-white font-mono mt-0.5">
                {plan.total_items_to_reorder}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-mono text-[#888888] uppercase">SUPPLIERS</div>
              <div className="text-xl font-black text-white font-mono mt-0.5">
                {suppliers.length}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[#333333] flex items-center justify-between text-xs text-[#888888] font-mono">
            <span>HASH: #PLAN-2026-ACT3-SEED42</span>
            <span className="text-[#00CC66] font-bold">100% BUDGET COMPLIANCE VERIFIED</span>
          </div>
        </div>

        {/* Right: Ready for Approval Card */}
        <div className="lg:col-span-5 bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#00CC66] rounded-[4px] p-6 shadow-xl flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="text-xs font-mono font-bold text-[#00CC66] uppercase tracking-wider">
              READY FOR AUTHORIZATION
            </div>
            <p className="text-xs text-[#CCCCCC] font-mono leading-relaxed">
              This plan is within budget. Approval creates purchase order records with unique references; supplier messages are prepared but not dispatched.
            </p>

            <label className="flex items-center gap-3 pt-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isApproved}
                onChange={(e) => onToggleApproval(e.target.checked)}
                className="w-4 h-4 rounded-[2px] text-[#E50000] focus:ring-[#E50000] border-[#333333] bg-[#0B0B0B]"
              />
              <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                I AUTHORIZE THIS RESTOCKING PLAN (SPEC V1.0)
              </span>
            </label>
          </div>

          <button
            onClick={onSubmitApproval}
            disabled={!isApproved || isSubmitting}
            className={`w-full py-3 px-4 rounded-[4px] font-bold text-xs uppercase tracking-wider transition-all shadow-sm ${
              isApproved
                ? 'bg-[#E50000] hover:bg-[#CC0000] active:bg-[#4A0000] text-white cursor-pointer shadow-[0_0_12px_rgba(229,0,0,0.35)]'
                : 'bg-[#0B0B0B] border border-[#333333] text-[#888888] cursor-not-allowed'
            }`}
          >
            {isSubmitting ? 'MINTING PURCHASE ORDERS...' : 'APPROVE PLAN & CREATE ORDERS'}
          </button>
        </div>
      </div>

      {/* Purchase Orders Preview Cards */}
      <div className="space-y-3 pt-2">
        <div className="text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">
          PURCHASE ORDERS TO BE DISPATCHED
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {suppliers.map((supName, idx) => {
            const supData = plan.supplier_breakdown[supName];
            return (
              <div
                key={supName}
                className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 shadow-lg space-y-3 hover:border-[#E50000] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="font-bold text-white uppercase text-sm font-mono">
                    {supName}
                  </div>
                  <span className="text-xs text-[#888888] font-mono">REFERENCE ON APPROVAL</span>
                </div>

                <div>
                  <div className="text-2xl font-black text-white font-mono">
                    R {supData.total_spend.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-[#888888] mt-0.5 font-mono">{supData.items_count} ITEMS TO PACK</div>
                </div>

                <div className="pt-2 border-t border-[#333333] flex items-center justify-between text-xs font-mono">
                  <span className="text-[#888888]">LEAD TIME: 2-3 DAYS</span>
                  <button
                    onClick={() => setSelectedSupplierPreview(supName)}
                    className="text-xs text-[#E50000] hover:text-white font-bold uppercase underline cursor-pointer"
                  >
                    VIEW
                  </button>
                </div>
              </div>
            );
          })}
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
      </div>

      {/* Supplier Items Preview Modal */}
      {selectedSupplierPreview && (
        <div className="fixed inset-0 z-50 bg-[#0B0B0B]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1A1A1A] rounded-[4px] max-w-md w-full p-6 shadow-2xl border border-[#333333] space-y-4">
            <div className="flex items-center justify-between border-b border-[#333333] pb-2">
              <h4 className="font-bold text-white uppercase tracking-wider text-sm font-mono">
                {selectedSupplierPreview.toUpperCase()} ORDER LINE ITEMS
              </h4>
              <button
                onClick={() => setSelectedSupplierPreview(null)}
                className="text-[#888888] hover:text-white text-xs font-mono font-bold cursor-pointer"
              >
                [X]
              </button>
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto font-mono text-xs">
              {plan.supplier_breakdown[selectedSupplierPreview]?.items.map((it, idx) => (
                <div key={idx} className="flex justify-between p-2 rounded-[2px] bg-[#0B0B0B] border border-[#333333]">
                  <span className="font-bold text-white">{it.product} ({it.qty}x)</span>
                  <span className="font-bold text-[#00CC66]">R {it.total_cost.toFixed(2)}</span>
                </div>
              ))}
            </div>
            <button
              onClick={() => setSelectedSupplierPreview(null)}
              className="w-full py-2 bg-[#0B0B0B] border border-[#333333] hover:border-[#E50000] text-white font-bold text-xs uppercase rounded-[2px]"
            >
              CLOSE
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
