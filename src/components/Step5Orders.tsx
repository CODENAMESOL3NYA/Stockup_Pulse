import React, { useState } from 'react';
import { PurchaseOrder } from '../types';
import { generatePurchaseOrderPdf } from '../utils/pdfGenerator';

interface Step5OrdersProps {
  orders: PurchaseOrder[];
  onBack: () => void;
  onGoToEvidence: () => void;
}

export const Step5Orders: React.FC<Step5OrdersProps> = ({
  orders,
  onBack,
  onGoToEvidence,
}) => {
  const [activeTab, setActiveTab] = useState<'orders' | 'messages' | 'downloads'>('orders');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeJsonOrder, setActiveJsonOrder] = useState<PurchaseOrder | null>(null);

  const handleCopyMessage = (order: PurchaseOrder) => {
    navigator.clipboard.writeText(order.whatsapp_message);
    setCopiedId(order.order_number);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleDownloadPdf = (order: PurchaseOrder) => {
    generatePurchaseOrderPdf(order);
  };

  const handleDownloadJson = (order: PurchaseOrder) => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(order, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${order.order_number}_${order.supplier}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const poRefs = orders.map(o => `${o.order_number} (${o.supplier})`).join(', ');

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          STEP 5 OF 5 // PURCHASE ORDERS DISPATCH
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">
          GENERATED PURCHASE ORDERS
        </h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Purchase orders have been minted. Download official PDF invoices, JSON records, or dispatch to WhatsApp.
        </p>
      </div>

      {/* Confirmation Notification Banner */}
      <div className="p-4 rounded-[4px] bg-[#1A1A1A] border border-[#00CC66] border-l-4 border-l-[#00CC66] text-sm">
        <div className="font-bold text-[#00CC66] uppercase font-mono tracking-wider">
          ORDERS DISPATCHED &amp; RECORDED SUCCESSFULLY
        </div>
        <div className="text-xs text-white mt-1 font-mono">
          Order numbers: {poRefs}
        </div>
      </div>

      {/* Tabs Row */}
      <div className="border-b border-[#333333] flex gap-6">
        <button
          onClick={() => setActiveTab('orders')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'orders'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Orders
        </button>
        <button
          onClick={() => setActiveTab('messages')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'messages'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Supplier Messages
        </button>
        <button
          onClick={() => setActiveTab('downloads')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'downloads'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Downloads
        </button>
      </div>

      {/* TAB 1: Orders Table */}
      {activeTab === 'orders' && (
        <div className="space-y-6">
          <div className="bg-[#0B0B0B] border border-[#333333] rounded-[4px] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#1A1A1A] border-b border-[#333333] text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3.5">Supplier</th>
                    <th className="px-4 py-3.5">Order #</th>
                    <th className="px-4 py-3.5">Items</th>
                    <th className="px-4 py-3.5">Total Spend</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#222222]">
                  {orders.map((po) => (
                    <tr key={po.order_number} className="hover:bg-[#1A1A1A]/50 transition-colors">
                      <td className="px-6 py-4 font-bold text-white uppercase">{po.supplier}</td>
                      <td className="px-4 py-4 font-mono text-xs text-[#E50000] font-bold">{po.order_number}</td>
                      <td className="px-4 py-4 text-[#888888] font-mono text-xs">{po.total_items} ITEMS</td>
                      <td className="px-4 py-4 font-mono font-bold text-white">
                        R {po.total_spend.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-4">
                        <span className="inline-block px-2 py-0.5 rounded-[2px] text-[10px] font-mono font-bold bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/40 uppercase">
                          {po.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleDownloadPdf(po)}
                            className="px-2.5 py-1 text-xs font-mono font-bold rounded-[2px] bg-[#1A1A1A] hover:bg-[#252525] text-white border border-[#333333] hover:border-[#E50000] cursor-pointer transition-colors"
                          >
                            PDF
                          </button>
                          <button
                            onClick={() => handleDownloadJson(po)}
                            className="px-2.5 py-1 text-xs font-mono font-bold rounded-[2px] bg-[#1A1A1A] hover:bg-[#252525] text-[#888888] hover:text-white border border-[#333333] cursor-pointer transition-colors"
                          >
                            JSON
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Supplier Messages */}
      {activeTab === 'messages' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {orders.map((po) => (
              <div
                key={po.order_number}
                className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 shadow-lg space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="font-bold text-white uppercase text-sm font-mono">
                    {po.supplier}
                  </div>
                  <span className="text-xs text-[#888888] font-mono">{po.order_number}</span>
                </div>

                <div className="p-3 bg-[#0B0B0B] border border-[#333333] rounded-[2px] text-xs font-mono text-[#CCCCCC] whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                  {po.whatsapp_message}
                </div>

                <button
                  onClick={() => handleCopyMessage(po)}
                  className="w-full py-2 bg-[#0B0B0B] hover:bg-[#252525] border border-[#333333] hover:border-[#E50000] text-white text-xs font-bold uppercase rounded-[2px] transition-colors cursor-pointer"
                >
                  {copiedId === po.order_number ? 'COPIED TO CLIPBOARD' : 'COPY MESSAGE'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: Downloads */}
      {activeTab === 'downloads' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {orders.map((po) => (
            <div
              key={po.order_number}
              className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 shadow-lg space-y-3"
            >
              <div className="font-bold text-white uppercase font-mono text-sm">{po.supplier}</div>
              <div className="text-xs text-[#888888] font-mono">{po.order_number} // R {po.total_spend.toFixed(2)}</div>
              <div className="pt-2 flex items-center gap-2">
                <button
                  onClick={() => handleDownloadPdf(po)}
                  className="flex-1 py-2 bg-[#E50000] hover:bg-[#CC0000] text-white text-xs font-bold uppercase rounded-[2px] transition-colors"
                >
                  DOWNLOAD PDF
                </button>
                <button
                  onClick={() => handleDownloadJson(po)}
                  className="flex-1 py-2 bg-[#0B0B0B] hover:bg-[#252525] border border-[#333333] text-white text-xs font-bold uppercase rounded-[2px] transition-colors"
                >
                  EXPORT JSON
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="px-5 py-2.5 rounded-[4px] border border-[#333333] hover:border-[#E50000] bg-transparent text-white font-bold text-xs uppercase tracking-wider cursor-pointer transition-colors"
        >
          &larr; BACK
        </button>
        <button
          onClick={onGoToEvidence}
          className="px-6 py-2.5 rounded-[4px] bg-[#E50000] hover:bg-[#CC0000] text-white font-bold text-xs uppercase tracking-wider shadow-[0_0_12px_rgba(229,0,0,0.35)] cursor-pointer transition-colors"
        >
          VIEW HARDWARE EVIDENCE &rarr;
        </button>
      </div>
    </div>
  );
};
