import React from 'react';

interface HomeHeroProps {
  onGetStarted: () => void;
  onUseDemoData: () => void;
}

export const HomeHero: React.FC<HomeHeroProps> = ({ onGetStarted, onUseDemoData }) => {
  return (
    <div className="p-8 md:p-12 max-w-6xl mx-auto text-white font-sans">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        {/* Left Copy */}
        <div className="lg:col-span-7 space-y-6">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-[2px] text-xs font-mono font-bold bg-[#1A1A1A] text-[#E50000] border border-[#333333] tracking-wider uppercase">
              AMD HACKATHON ACT III // REINVENT COMMERCE
            </span>
          </div>

          <div className="space-y-3">
            <div className="text-xs font-mono font-bold tracking-widest text-[#888888] uppercase">
              STOCKUP PULSE // SMARTER STOCK. STRONGER SHOPS.
            </div>
            <h1 className="text-3xl md:text-5xl font-black text-white tracking-wider uppercase leading-tight">
              BUDGET-BOUNDED RESTOCKING FOR SOUTH AFRICAN SPAZA SHOPS
            </h1>
            <div className="w-20 h-[2px] bg-[#E50000] shadow-[0_0_10px_rgba(229,0,0,0.6)]" />
            <p className="text-sm md:text-base text-[#888888] leading-relaxed">
              Review an illustrative catalogue and create a deterministic, budget-capped restocking plan. Supplier availability and price sources still need verification before ordering.
            </p>
          </div>

          {/* Value proposition badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
            <div className="px-3 py-2.5 rounded-[4px] bg-[#1A1A1A] border border-[#333333]">
              <div className="text-[10px] font-mono text-[#888888] uppercase">PROCUREMENT</div>
              <div className="text-xs font-bold text-white uppercase mt-0.5">NOT MEASURED</div>
            </div>

            <div className="px-3 py-2.5 rounded-[4px] bg-[#1A1A1A] border border-[#333333]">
              <div className="text-[10px] font-mono text-[#888888] uppercase">SHELVES</div>
              <div className="text-xs font-bold text-[#00CC66] uppercase mt-0.5">AVAILABILITY VARIES</div>
            </div>

            <div className="px-3 py-2.5 rounded-[4px] bg-[#1A1A1A] border border-[#333333]">
              <div className="text-[10px] font-mono text-[#888888] uppercase">KNAPSACK</div>
              <div className="text-xs font-bold text-white uppercase mt-0.5">BUDGET CAPPED</div>
            </div>

            <div className="px-3 py-2.5 rounded-[4px] bg-[#1A1A1A] border border-[#333333]">
              <div className="text-[10px] font-mono text-[#888888] uppercase">MARGIN</div>
              <div className="text-xs font-bold text-[#00CC66] uppercase mt-0.5">NOT MEASURED</div>
            </div>
          </div>

          {/* Call to Actions */}
          <div className="flex flex-wrap items-center gap-4 pt-4">
            <button
              onClick={onGetStarted}
              className="px-6 py-3 rounded-[4px] bg-[#E50000] hover:bg-[#CC0000] active:bg-[#4A0000] text-white font-bold text-xs uppercase tracking-wider shadow-[0_0_12px_rgba(229,0,0,0.35)] transition-all cursor-pointer"
            >
              GET STARTED
            </button>
            <button
              onClick={onUseDemoData}
              className="px-5 py-3 rounded-[4px] bg-[#1A1A1A] hover:bg-[#252525] text-white font-bold text-xs uppercase tracking-wider border border-[#333333] hover:border-[#E50000] transition-all cursor-pointer"
            >
              LOAD ILLUSTRATIVE DATA
            </button>
          </div>

          {/* South African Context Footnote */}
          <div className="pt-4 border-t border-[#333333] flex items-center gap-6 text-xs text-[#888888] font-mono">
            <div>BUILT FOR SOUTH AFRICAN SPAZA SHOPS</div>
            <div>REMOTE MODEL NOT CONFIGURED</div>
          </div>
        </div>

        {/* Right Hero Visual Card */}
        <div className="lg:col-span-5 relative">
          <div className="relative rounded-[4px] overflow-hidden border border-[#333333] bg-[#1A1A1A] group">
            <img
              src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=800&q=80"
              alt="South African retail store owner"
              className="w-full h-[460px] object-cover object-center opacity-80 group-hover:scale-102 transition-transform duration-500"
            />
            {/* Dark gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-[#0B0B0B] via-[#0B0B0B]/40 to-transparent" />

            {/* Quote badge */}
            <div className="absolute bottom-6 left-6 right-6 p-4 rounded-[4px] bg-[#1A1A1A]/95 border border-[#333333] text-white">
              <div className="text-xs font-mono font-bold tracking-wider text-[#E50000] uppercase mb-1">
                COMMERCE VERIFICATION
              </div>
              <div className="text-sm font-bold italic tracking-wide text-white">
                &ldquo;Better stock today, more sales tomorrow.&rdquo;
              </div>
              <div className="text-xs text-[#888888] mt-2 flex items-center justify-between font-mono">
                <span>Mpho Khumalo // Sunnyside Spaza</span>
                <span className="text-[10px] bg-[#0B0B0B] text-white border border-[#333333] px-2 py-0.5 rounded-[2px]">
                  MAKRO // SHOPRITE // USAVE
                </span>
              </div>
            </div>
          </div>

          {/* Floating Pill Accent */}
          <div className="absolute -top-3 -right-3 bg-[#1A1A1A] p-3 rounded-[4px] border border-[#333333] flex items-center gap-2.5 shadow-xl">
            <div className="w-8 h-8 rounded-[2px] bg-[#0B0B0B] border border-[#E50000] text-[#E50000] flex items-center justify-center font-mono font-bold text-xs">
              ZAR
            </div>
            <div>
              <div className="text-[10px] text-[#888888] font-mono uppercase">BUDGET GUARD</div>
              <div className="text-xs font-bold text-white font-mono">100% STRICT &le; R 3,000</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
