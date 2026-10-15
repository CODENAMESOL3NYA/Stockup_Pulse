import React, { useState } from 'react';
import { ProductItem } from '../types';

interface Step2CatalogueProps {
  products: ProductItem[];
  onUpdateProduct: (product: ProductItem) => void;
  onBack: () => void;
  onContinue: () => void;
}

export const Step2Catalogue: React.FC<Step2CatalogueProps> = ({
  products,
  onUpdateProduct,
  onBack,
  onContinue,
}) => {
  const [search, setSearch] = useState('');
  const [selectedSupplier, setSelectedSupplier] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [activeModalItem, setActiveModalItem] = useState<ProductItem | null>(null);

  const filteredProducts = products.filter((p) => {
    const matchesSearch = p.product.toLowerCase().includes(search.toLowerCase());
    const matchesSupplier = selectedSupplier === 'All' || p.supplier === selectedSupplier;
    const matchesStatus = selectedStatus === 'All' || p.status === selectedStatus;
    return matchesSearch && matchesSupplier && matchesStatus;
  });

  const confirmedCount = products.filter(p => p.status === 'Confirmed').length;
  const needsReviewCount = products.filter(p => p.status === 'Needs review').length;
  const unmatchedCount = products.filter(p => p.status === 'Unmatched').length;

  const handleConfirmItem = (item: ProductItem) => {
    onUpdateProduct({ ...item, status: 'Confirmed', confidence: 0.95 });
    setActiveModalItem(null);
  };

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          STEP 2 OF 5 // CATALOGUE EXTRACTION &amp; ADJUDICATION
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">
          REVIEW &amp; CONFIRM PRODUCT CATALOGUE
        </h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Catalogue matching uses local fuzzy rules. Review product and price matches before planning.
        </p>
      </div>

      {/* KPI Cards Row (Dark mode with AMD accents) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#E50000] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase">TOTAL PRODUCTS</div>
          <div className="text-2xl font-black text-white font-mono mt-1">{products.length}</div>
        </div>

        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#00CC66] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#00CC66] uppercase">CONFIRMED MATCHES</div>
          <div className="text-2xl font-black text-[#00CC66] font-mono mt-1">{confirmedCount}</div>
        </div>

        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#FF3333] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#FF3333] uppercase">NEEDS REVIEW</div>
          <div className="text-2xl font-black text-[#FF3333] font-mono mt-1">{needsReviewCount}</div>
        </div>

        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#888888] rounded-[4px] p-4">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase">UNMATCHED SKUS</div>
          <div className="text-2xl font-black text-white font-mono mt-1">{unmatchedCount}</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="SEARCH PRODUCTS..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3.5 py-2 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-xs text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none uppercase font-mono"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={selectedSupplier}
            onChange={(e) => setSelectedSupplier(e.target.value)}
            className="px-3 py-2 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-xs text-white focus:border-[#E50000] focus:outline-none cursor-pointer uppercase font-mono"
          >
            <option value="All">ALL SUPPLIERS</option>
            <option value="Makro">MAKRO</option>
            <option value="Shoprite">SHOPRITE</option>
            <option value="Usave">USAVE</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-2 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-xs text-white focus:border-[#E50000] focus:outline-none cursor-pointer uppercase font-mono"
          >
            <option value="All">ALL STATUS</option>
            <option value="Confirmed">CONFIRMED</option>
            <option value="Needs review">NEEDS REVIEW</option>
            <option value="Unmatched">UNMATCHED</option>
          </select>
        </div>
      </div>

      {/* Product Table: Header #1A1A1A, Rows #0B0B0B, status capsules */}
      <div className="bg-[#0B0B0B] border border-[#333333] rounded-[4px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#1A1A1A] border-b border-[#333333] text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5">Product</th>
                <th className="px-4 py-3.5">Pack Size</th>
                <th className="px-4 py-3.5">Supplier Price</th>
                <th className="px-4 py-3.5">Our Price</th>
                <th className="px-4 py-3.5">Status</th>
                <th className="px-4 py-3.5">Confidence</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#222222]">
              {filteredProducts.map((item) => (
                <tr key={item.id} className="hover:bg-[#1A1A1A]/50 transition-colors">
                  <td className="px-6 py-4 font-bold text-white">
                    {item.product}
                    <div className="text-[10px] text-[#888888] font-mono font-normal uppercase">{item.supplier}</div>
                  </td>
                  <td className="px-4 py-4 text-[#888888] font-mono text-xs">{item.pack_size}</td>
                  <td className="px-4 py-4 font-bold text-white font-mono">R {item.supplier_price.toFixed(2)}</td>
                  <td className="px-4 py-4 text-[#888888] font-mono">R {item.our_price.toFixed(2)}</td>
                  <td className="px-4 py-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-[2px] text-[10px] font-mono font-bold uppercase tracking-wider ${
                        item.status === 'Confirmed'
                          ? 'bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/50'
                          : item.status === 'Needs review'
                          ? 'bg-[#1A1A1A] text-[#FF3333] border border-[#FF3333]/50'
                          : 'bg-[#1A1A1A] text-[#888888] border border-[#333333]'
                      }`}
                    >
                      {item.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-4 font-mono font-bold text-xs">
                    <span className={item.confidence >= 0.85 ? 'text-[#00CC66]' : 'text-[#FF3333]'}>
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setActiveModalItem(item)}
                      className="text-xs text-[#E50000] hover:text-white font-bold uppercase tracking-wider cursor-pointer underline"
                    >
                      VIEW AUDIT
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Navigation Footer */}
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
          CONTINUE TO PLAN &rarr;
        </button>
      </div>

      {/* Adjudication Modal */}
      {activeModalItem && (
        <div className="fixed inset-0 z-50 bg-[#0B0B0B]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1A1A1A] rounded-[4px] max-w-lg w-full p-6 shadow-2xl border border-[#333333] space-y-5 animate-fade-in">
            <div className="flex items-center justify-between border-b border-[#333333] pb-3">
              <div>
                <div className="text-[10px] font-mono text-[#E50000] font-bold uppercase">LOCAL MATCH REVIEW</div>
                <h3 className="text-base font-black text-white uppercase tracking-wider">SKU MATCH ADJUDICATION</h3>
              </div>
              <button
                onClick={() => setActiveModalItem(null)}
                className="text-[#888888] hover:text-white text-sm font-mono font-bold p-1 cursor-pointer"
              >
                [X]
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <span className="text-[10px] font-mono font-bold text-[#888888] uppercase">Internal Spaza Product</span>
                <div className="text-base font-bold text-white font-mono">{activeModalItem.product}</div>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-[#0B0B0B] p-3 rounded-[2px] border border-[#333333]">
                <div>
                  <div className="text-[10px] font-mono text-[#888888] uppercase">Wholesale Flyer Source</div>
                  <div className="font-bold text-white uppercase text-xs">{activeModalItem.supplier} Leaflet</div>
                </div>
                <div>
                  <div className="text-[10px] font-mono text-[#888888] uppercase">Confidence Score</div>
                  <div className="font-mono font-bold text-[#00CC66] text-xs">{Math.round(activeModalItem.confidence * 100)}%</div>
                </div>
              </div>

              <div className="bg-[#0B0B0B] p-3 rounded-[2px] border border-[#333333] text-xs text-[#888888] space-y-1">
                <div className="font-bold text-[#E50000] font-mono uppercase">
                  QWEN2.5-VL ADJUDICATION RATIONALE
                </div>
                <p className="leading-relaxed">
                  Match adjudicated between internal store inventory &apos;{activeModalItem.product}&apos; and extracted wholesale leaflet item. Pack volume format matches standard Gauteng Spaza retail units. Deterministic integer arithmetic enforces exact prices.
                </p>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-[#888888] pt-1">
                <span>EXTERNAL MODEL NOT CONFIGURED</span>
                <span>VLLM BACKEND</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#333333]">
              <button
                onClick={() => setActiveModalItem(null)}
                className="px-4 py-2 rounded-[2px] border border-[#333333] text-[#888888] hover:text-white text-xs font-bold uppercase"
              >
                CLOSE
              </button>
              <button
                onClick={() => handleConfirmItem(activeModalItem)}
                className="px-5 py-2 rounded-[2px] bg-[#E50000] hover:bg-[#CC0000] text-white text-xs font-bold uppercase tracking-wider shadow-sm"
              >
                CONFIRM MATCH
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
