import React, { useState } from 'react';

interface Step1UploadProps {
  budget: number;
  onChangeBudget: (b: number) => void;
  horizonDays: number;
  onChangeHorizon: (h: number) => void;
  demoData: boolean;
  onToggleDemoData: (val: boolean) => void;
  onProcessFiles: () => void;
  isProcessing: boolean;
}

export const Step1Upload: React.FC<Step1UploadProps> = ({
  budget,
  onChangeBudget,
  horizonDays,
  onChangeHorizon,
  demoData,
  onToggleDemoData,
  onProcessFiles,
  isProcessing,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState([
    { name: 'sales_data.csv', type: 'Sales data (CSV)', size: '2.4 KB', status: 'ready' },
    { name: 'stock_data.csv', type: 'Stock data (CSV)', size: '3.1 KB', status: 'ready' },
    { name: 'supplier_price_list.pdf', type: 'Supplier price list (PDF)', size: '1.2 MB', status: 'ready' },
  ]);

  const [suppliers, setSuppliers] = useState([
    { name: 'Makro', leadTime: 2 },
    { name: 'Shoprite', leadTime: 3 },
    { name: 'Usave', leadTime: 2 },
  ]);

  const [newSupplierName, setNewSupplierName] = useState('');
  const [showAddSupplier, setShowAddSupplier] = useState(false);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const newFile = {
        name: file.name,
        type: file.name.endsWith('.csv') ? 'Custom CSV' : 'Flyer Document / Leaflet',
        size: `${(file.size / 1024).toFixed(1)} KB`,
        status: 'ready'
      };
      setUploadedFiles(prev => [...prev, newFile]);
    }
  };

  const handleAddSupplier = () => {
    if (newSupplierName.trim()) {
      setSuppliers(prev => [...prev, { name: newSupplierName.trim(), leadTime: 2 }]);
      setNewSupplierName('');
      setShowAddSupplier(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      {/* Step Header */}
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          STEP 1 OF 5 // DATA INGESTION
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">
          UPLOAD STORE DATA
        </h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Upload sales logs, stock counts, and supplier promotional flyers for AMD vision processing.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Drag & Drop Area */}
        <div className="lg:col-span-7 space-y-4">
          <label className="block border border-dashed border-[#333333] hover:border-[#E50000] bg-[#1A1A1A] hover:bg-[#1A1A1A]/80 rounded-[4px] p-8 text-center cursor-pointer transition-all">
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileUpload}
              accept=".csv,.xlsx,.pdf,.jpg,.jpeg,.png"
            />
            <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-widest mb-2">
              [FILE INGESTION PORTAL]
            </div>
            <div className="text-sm font-bold text-white uppercase">
              DRAG &amp; DROP INPUT FILES HERE, OR <span className="text-[#E50000] underline">BROWSE</span>
            </div>
            <div className="text-xs text-[#888888] mt-1 font-mono">
              CSV, XLSX, PDF, JPG, PNG (MAX 10MB PER FILE)
            </div>
          </label>

          {/* Files List */}
          <div className="space-y-2">
            <div className="text-[11px] font-bold text-[#888888] uppercase tracking-wider px-1 font-mono">
              LOADED INPUTS ({uploadedFiles.length})
            </div>
            {uploadedFiles.map((f, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3.5 rounded-[4px] bg-[#1A1A1A] border border-[#333333] hover:border-[#4A0000] transition-colors"
              >
                <div>
                  <div className="text-sm font-bold text-white font-mono">{f.name}</div>
                  <div className="text-xs text-[#888888]">{f.type}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[#888888] font-mono">{f.size}</span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-[2px] bg-[#0B0B0B] text-[#00CC66] border border-[#00CC66]/40 uppercase">
                    CONFIRMED
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Planning Settings Card */}
        <div className="lg:col-span-5 bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-6 shadow-xl space-y-5">
          <div className="border-b border-[#333333] pb-3">
            <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-wider mb-1">
              CONSTRAINTS
            </div>
            <h3 className="text-base font-bold text-white uppercase tracking-wider">Planning Settings</h3>
            <p className="text-xs text-[#888888]">Configure shop budget constraints and parameters</p>
          </div>

          {/* Budget Input in ZAR */}
          <div>
            <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Budget Ceiling (ZAR)
            </label>
            <div className="relative rounded-[4px]">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#888888] font-mono font-bold text-sm">
                R
              </div>
              <input
                type="number"
                min="100"
                step="50"
                value={budget}
                onChange={(e) => onChangeBudget(parseFloat(e.target.value) || 0)}
                className="w-full pl-8 pr-4 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm font-bold text-white font-mono focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none"
                placeholder="3000.00"
              />
            </div>
            <div className="text-[11px] text-[#888888] mt-1 font-mono">
              Deterministic optimizer strictly caps expenditure &le; R {budget.toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
            </div>
          </div>

          {/* Planning Horizon */}
          <div>
            <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
              Planning Horizon
            </label>
            <select
              value={horizonDays}
              onChange={(e) => onChangeHorizon(parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white focus:border-[#E50000] focus:outline-none cursor-pointer"
            >
              <option value={7}>Next 7 days (Weekly restock)</option>
              <option value={14}>Next 14 days (Bi-weekly - Recommended)</option>
              <option value={21}>Next 21 days</option>
              <option value={30}>Next 30 days (Monthly restock)</option>
            </select>
          </div>

          {/* Supplier Lead Times */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-[#888888] uppercase tracking-wider">
                Supplier Lead Times
              </label>
              <button
                type="button"
                onClick={() => setShowAddSupplier(!showAddSupplier)}
                className="text-xs text-[#E50000] hover:text-white font-bold uppercase transition-colors cursor-pointer"
              >
                + ADD SUPPLIER
              </button>
            </div>

            <div className="space-y-2">
              {suppliers.map((s, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 bg-[#0B0B0B] rounded-[2px] border border-[#333333] text-sm font-mono">
                  <span className="font-bold text-white uppercase">{s.name}</span>
                  <span className="text-xs text-[#888888] bg-[#1A1A1A] px-2 py-0.5 rounded-[2px] border border-[#333333]">
                    {s.leadTime} DAYS
                  </span>
                </div>
              ))}
            </div>

            {showAddSupplier && (
              <div className="mt-2.5 flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Supplier name (e.g. Jumbo)"
                  value={newSupplierName}
                  onChange={(e) => setNewSupplierName(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-xs bg-[#0B0B0B] border border-[#333333] text-white rounded-[2px] focus:border-[#E50000] focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleAddSupplier}
                  className="px-3 py-1.5 bg-[#E50000] text-white text-xs font-bold uppercase rounded-[2px] hover:bg-[#CC0000]"
                >
                  SAVE
                </button>
              </div>
            )}
          </div>

          {/* Demo Data Toggle */}
          <div className="pt-3 border-t border-[#333333] flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-white uppercase">Use Demo Data</div>
              <div className="text-[11px] text-[#888888]">Pre-loaded with synthetic South African retail staples.</div>
            </div>
            <button
              type="button"
              onClick={() => onToggleDemoData(!demoData)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-xs border border-[#333333] transition-colors duration-200 ease-in-out ${
                demoData ? 'bg-[#E50000]' : 'bg-[#0B0B0B]'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-xs bg-white shadow-xs transition duration-200 ease-in-out ${
                  demoData ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Process Files CTA */}
          <button
            onClick={onProcessFiles}
            disabled={isProcessing}
            className="w-full py-3 px-4 bg-[#E50000] hover:bg-[#CC0000] active:bg-[#4A0000] disabled:bg-[#333333] text-white font-bold text-xs uppercase tracking-wider rounded-[4px] shadow-[0_0_12px_rgba(229,0,0,0.35)] flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            {isProcessing ? 'PREPARING RESTOCKING PLAN...' : 'PROCESS FILES'}
          </button>
        </div>
      </div>
    </div>
  );
};
