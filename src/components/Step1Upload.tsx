import React, { useState } from 'react';
import { forecastImportedCandidate } from '../services/api';
import { FileImportCandidate, FileImportReview } from '../types';

interface Step1UploadProps {
  budget: number;
  onChangeBudget: (budget: number) => void;
  horizonDays: number;
  onChangeHorizon: (days: number) => void;
  demoData: boolean;
  onToggleDemoData: (enabled: boolean) => void;
  onProcessFiles: (
    files: File[],
    supplierLeadTimes: Record<string, number>,
    horizonDays: number,
    demoData: boolean
  ) => Promise<FileImportReview | null>;
  onImportCandidates: (candidates: FileImportCandidate[]) => Promise<void> | void;
  isProcessing: boolean;
}

interface SupplierLeadTime {
  id: number;
  name: string;
  days: string;
}

const parseOptionalNumber = (value: string): number | null => {
  if (!value.trim()) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export const Step1Upload: React.FC<Step1UploadProps> = ({
  budget,
  onChangeBudget,
  horizonDays,
  onChangeHorizon,
  demoData,
  onToggleDemoData,
  onProcessFiles,
  onImportCandidates,
  isProcessing,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [suppliers, setSuppliers] = useState<SupplierLeadTime[]>([]);
  const [candidates, setCandidates] = useState<FileImportCandidate[]>([]);
  const [availableProducts, setAvailableProducts] = useState<FileImportReview['available_products']>([]);
  const [newSupplierName, setNewSupplierName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [hasNoExtractedOffers, setHasNoExtractedOffers] = useState(false);

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const added = Array.from(incoming);
    const next = [...uploadedFiles, ...added];
    if (next.length > 5) {
      setError('Upload no more than 5 files at a time.');
      return;
    }
    if (next.some(file => file.size > 10 * 1024 * 1024) ||
        next.reduce((sum, file) => sum + file.size, 0) > 25 * 1024 * 1024) {
      setError('Each file must be at most 10 MB and combined uploads at most 25 MB.');
      return;
    }
    setError(null);
    setUploadedFiles(next);
    setCandidates([]);
    setHasNoExtractedOffers(false);
  };

  const refreshForecast = async (candidate: FileImportCandidate) => {
    if (!candidate.sales_history?.length || candidate.current_stock === null ||
        candidate.lead_time_days === null || candidate.lead_time_days < 1) {
      return;
    }
    try {
      const forecast = await forecastImportedCandidate(
        candidate.sales_history,
        candidate.current_stock,
        candidate.lead_time_days,
        horizonDays
      );
      setCandidates(previous => previous.map(item =>
        item.id === candidate.id
          ? { ...item, forecast, recommended_qty: forecast.recommended_qty, at_risk: forecast.at_risk_before_delivery }
          : item
      ));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Forecast recalculation failed.');
    }
  };

  const updateCandidate = (id: string, changes: Partial<FileImportCandidate>, recalculate = false) => {
    const existing = candidates.find(candidate => candidate.id === id);
    if (!existing) return;
    const updated = { ...existing, ...changes };
    updated.issues = [
      ...(!updated.matched_product ? ['Select an exact store product match.'] : []),
      ...(!updated.sales_history?.length ? ['Sales history is required or this candidate must be excluded.'] : []),
      ...(updated.current_stock === null ? ['Current stock is required or this candidate must be excluded.'] : []),
      ...(!updated.lead_time_days || updated.lead_time_days < 1 ? ['Enter a verified supplier lead time.'] : []),
      ...(!updated.pack_count && !updated.unit_price ? ['Verify pack count or manually enter the per-unit supplier cost.'] : []),
      ...(!updated.supplier.trim() ? ['Enter and verify the supplier.'] : []),
      ...(updated.supplier_price === null || updated.supplier_price <= 0 ? ['Enter the observed supplier pack price.'] : []),
      ...(!updated.unit_price || updated.unit_price <= 0 ? ['Enter supplier cost per sellable unit.'] : []),
      ...(updated.currency?.toUpperCase() !== 'ZAR' || updated.currency_verified !== true
        ? ['Confirm the supplier prices are denominated in ZAR; other currencies need conversion before import.']
        : []),
      ...(!updated.our_price || updated.our_price <= 0 ? ['Enter the verified store retail price.'] : []),
      ...(updated.retail_price_verified !== true ? ['Confirm the store retail price is verified.'] : []),
    ];
    setCandidates(previous => previous.map(candidate => candidate.id === id ? updated : candidate));
    if (recalculate) void refreshForecast(updated);
  };

  const handleMatchChange = (candidate: FileImportCandidate, normalizedKey: string) => {
    const product = availableProducts.find(item => item.normalized_key === normalizedKey);
    const mapped = {
      ...candidate,
      matched_product: product?.name || '',
      sales_history: product && !product.ambiguous ? product.sales_history : null,
      current_stock: product && !product.ambiguous ? product.current_stock : null,
      forecast: null,
      recommended_qty: null,
    };
    updateCandidate(candidate.id, mapped, true);
  };

  const handleProcessFiles = async () => {
    setError(null);
    setCandidates([]);
    setHasNoExtractedOffers(false);
    setIsReviewing(true);
    try {
      const leadTimes = Object.fromEntries(
        suppliers
          .filter(item =>
            item.name.trim() &&
            Number.isInteger(Number(item.days)) &&
            Number(item.days) > 0 &&
            Number(item.days) <= 365
          )
          .map(item => [item.name.trim(), Number(item.days)])
      );
      const review = await onProcessFiles(uploadedFiles, leadTimes, horizonDays, demoData);
      if (review) {
        setCandidates(review.candidates.map(candidate => ({ ...candidate, include: true })));
        setAvailableProducts(review.available_products);
        setHasNoExtractedOffers(review.candidates.length === 0);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'File processing failed.');
    } finally {
      setIsReviewing(false);
    }
  };

  const includedCandidates = candidates.filter(candidate => candidate.include !== false);
  const canImport = includedCandidates.length > 0 && includedCandidates.every(candidate =>
    Boolean(candidate.matched_product) &&
    Boolean(candidate.sales_history?.length) &&
    candidate.current_stock !== null &&
    Boolean(candidate.lead_time_days && Number.isInteger(candidate.lead_time_days) && candidate.lead_time_days <= 365) &&
    Boolean(candidate.unit_price && candidate.unit_price > 0) &&
    Boolean(candidate.supplier_price && candidate.supplier_price > 0) &&
    Boolean(candidate.supplier.trim()) &&
    candidate.currency?.toUpperCase() === 'ZAR' &&
    candidate.currency_verified === true &&
    Boolean(candidate.our_price && candidate.our_price > 0) &&
    candidate.retail_price_verified === true &&
    Boolean(candidate.recommended_qty && Number.isInteger(candidate.recommended_qty) && candidate.recommended_qty > 0) &&
    candidate.forecast !== null
  );

  const addSupplier = () => {
    if (!newSupplierName.trim()) return;
    setSuppliers(previous => [
      ...previous,
      { id: Date.now(), name: newSupplierName.trim(), days: '' },
    ]);
    setNewSupplierName('');
  };

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          STEP 1 OF 5 // DATA INGESTION
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">UPLOAD STORE DATA</h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          CSV/XLSX data is parsed locally. Leaflet images use AMD and PDFs use Evolus when each provider is configured.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <div className="lg:col-span-7 space-y-4">
          <label className="block border border-dashed border-[#333333] hover:border-[#E50000] bg-[#1A1A1A] rounded-[4px] p-8 text-center cursor-pointer">
            <input
              type="file"
              multiple
              className="hidden"
              onChange={event => addFiles(event.target.files)}
              accept=".csv,.xlsx,.pdf,.jpg,.jpeg,.png"
            />
            <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-widest mb-2">
              [FILE INGESTION PORTAL]
            </div>
            <div className="text-sm font-bold text-white uppercase">
              DRAG &amp; DROP INPUT FILES HERE, OR <span className="text-[#E50000] underline">BROWSE</span>
            </div>
            <div className="text-xs text-[#888888] mt-1 font-mono">
              CSV, XLSX, PDF, JPG, PNG (MAX 10MB EACH / 25MB TOTAL / 5 FILES)
            </div>
          </label>

          {uploadedFiles.map((file, index) => (
            <div key={`${file.name}-${index}`} className="flex items-center justify-between p-3 bg-[#1A1A1A] border border-[#333333] rounded-[4px]">
              <div>
                <div className="text-sm font-bold font-mono">{file.name}</div>
                <div className="text-xs text-[#888888]">{(file.size / 1024).toFixed(1)} KB</div>
              </div>
              <button
                type="button"
                className="text-xs text-[#FF7777] font-bold uppercase"
                onClick={() => setUploadedFiles(previous => previous.filter((_, fileIndex) => fileIndex !== index))}
              >
                REMOVE
              </button>
            </div>
          ))}

          {error && <div role="alert" className="p-3 border border-[#FF3333] text-[#FF7777] text-sm">{error}</div>}
          {hasNoExtractedOffers && (
            <div role="status" className="p-3 border border-[#555555] text-[#CCCCCC] text-sm">
              No leaflet offers were extracted. Check the selected files or use another supplier document.
            </div>
          )}

          {candidates.length > 0 && (
            <section className="space-y-3 border border-[#333333] bg-[#111111] p-4 rounded-[4px]">
              <div>
                <h3 className="text-sm font-bold uppercase">Review extracted leaflet items</h3>
                <p className="text-xs text-[#999999] mt-1">
                  Confirm product mapping, supplier costs, retail prices and supplier lead times before continuing.
                </p>
              </div>
              {candidates.map(candidate => (
                <div key={candidate.id} className="space-y-3 p-3 border border-[#333333] rounded-[4px]">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-bold text-sm">{candidate.product}</div>
                      <div className="text-[11px] text-[#888888]">
                        {candidate.source_filename} · {candidate.supplier || 'supplier not identified'}
                        {candidate.currency ? ` · ${candidate.currency}` : ' · currency unverified'}
                        {candidate.availability ? ` · ${candidate.availability}` : ''}
                      </div>
                      {candidate.evidence && (
                        <div className="text-[11px] text-[#999999] mt-1">Evidence: {candidate.evidence}</div>
                      )}
                      {candidate.warnings?.map((warning, index) => (
                        <div key={`${candidate.id}-warning-${index}`} className="text-[11px] text-[#D8AD70] mt-1">
                          {warning}
                        </div>
                      ))}
                    </div>
                    <label className="text-xs flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={candidate.include !== false}
                        onChange={event => updateCandidate(candidate.id, { include: event.target.checked })}
                      />
                      INCLUDE
                    </label>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <label className="text-[11px] text-[#999999] uppercase">
                      Matched store product
                      <select
                        value={availableProducts.find(item => item.name === candidate.matched_product)?.normalized_key || ''}
                        onChange={event => handleMatchChange(candidate, event.target.value)}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      >
                        <option value="">Select exact sales/stock product</option>
                        {availableProducts.map(item => (
                          <option key={item.normalized_key} value={item.normalized_key} disabled={item.ambiguous}>
                            {item.name}{item.ambiguous ? ' — ambiguous; fix source rows' : ''}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Pack size
                      <input
                        value={candidate.pack_size}
                        onChange={event => updateCandidate(candidate.id, { pack_size: event.target.value, unit_price: null })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Supplier
                      <input
                        value={candidate.supplier}
                        onChange={event => updateCandidate(candidate.id, { supplier: event.target.value })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Supplier pack price (R)
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={candidate.supplier_price ?? ''}
                        onChange={event => updateCandidate(candidate.id, { supplier_price: parseOptionalNumber(event.target.value), unit_price: null })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Price currency
                      <input
                        value={candidate.currency || ''}
                        maxLength={3}
                        placeholder="ZAR"
                        onChange={event => updateCandidate(candidate.id, {
                          currency: event.target.value.toUpperCase(),
                          currency_verified: false,
                        })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                      <span className="mt-2 flex items-center gap-2 normal-case">
                        <input
                          type="checkbox"
                          checked={candidate.currency_verified === true}
                          disabled={candidate.currency?.toUpperCase() !== 'ZAR'}
                          onChange={event => updateCandidate(candidate.id, { currency_verified: event.target.checked })}
                        />
                        I verified these prices are in ZAR
                      </span>
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Supplier cost per sellable unit (R)
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={candidate.unit_price ?? ''}
                        onChange={event => updateCandidate(candidate.id, { unit_price: parseOptionalNumber(event.target.value) })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Verified store retail price per unit (R)
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={candidate.our_price ?? ''}
                        onChange={event => updateCandidate(candidate.id, { our_price: parseOptionalNumber(event.target.value), retail_price_verified: false })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                      <span className="mt-2 flex items-center gap-2 normal-case">
                        <input
                          type="checkbox"
                          checked={candidate.retail_price_verified === true}
                          disabled={!candidate.our_price}
                          onChange={event => updateCandidate(candidate.id, { retail_price_verified: event.target.checked })}
                        />
                        I verified this retail price
                      </span>
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Supplier lead time (days)
                      <input
                        type="number"
                        min="1"
                        max="365"
                        step="1"
                        value={candidate.lead_time_days ?? ''}
                        onChange={event => {
                          const value = event.target.value.trim();
                          const parsed = value ? Number(value) : null;
                          updateCandidate(candidate.id, {
                            lead_time_days: parsed !== null && Number.isInteger(parsed) && parsed <= 365 ? parsed : null,
                            forecast: null,
                          }, true);
                        }}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                    </label>
                    <label className="text-[11px] text-[#999999] uppercase">
                      Planned quantity (sellable units)
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={candidate.recommended_qty ?? ''}
                        onChange={event => updateCandidate(candidate.id, { recommended_qty: parseOptionalNumber(event.target.value) })}
                        className="mt-1 w-full p-2 bg-[#0B0B0B] border border-[#333333] text-white normal-case"
                      />
                    </label>
                  </div>
                  <div className="text-xs text-[#999999]">
                    {candidate.forecast
                      ? `Deterministic forecast: ${candidate.forecast.recommended_qty} units; current stock ${candidate.current_stock}.`
                      : 'A forecast will be calculated after product mapping and lead time are supplied.'}
                  </div>
                  {candidate.issues.length > 0 && (
                    <ul className="list-disc pl-5 text-xs text-[#D8AD70]">
                      {candidate.issues.map(issue => <li key={issue}>{issue}</li>)}
                    </ul>
                  )}
                </div>
              ))}
              <button
                type="button"
                disabled={!canImport || isProcessing}
                onClick={() => onImportCandidates(includedCandidates)}
                className="w-full py-3 bg-[#E50000] disabled:bg-[#444444] text-white text-xs font-bold uppercase rounded-[4px]"
              >
                Use reviewed items for catalogue
              </button>
              {!canImport && <p className="text-xs text-[#999999]">Resolve required fields or exclude candidates before continuing.</p>}
            </section>
          )}
        </div>

        <div className="lg:col-span-5 bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-6 space-y-5">
          <div className="border-b border-[#333333] pb-3">
            <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-wider mb-1">CONSTRAINTS</div>
            <h3 className="text-base font-bold uppercase">Planning Settings</h3>
          </div>

          <label className="block text-xs font-bold text-[#888888] uppercase">
            Budget ceiling (ZAR)
            <input
              type="number"
              min="0.01"
              step="50"
              value={budget}
              onChange={event => onChangeBudget(parseFloat(event.target.value) || 0)}
              className="mt-2 w-full p-2.5 bg-[#0B0B0B] border border-[#333333] text-sm text-white"
            />
          </label>

          <label className="block text-xs font-bold text-[#888888] uppercase">
            Planning horizon
            <select
              value={horizonDays}
              onChange={event => onChangeHorizon(parseInt(event.target.value, 10))}
              className="mt-2 w-full p-2.5 bg-[#0B0B0B] border border-[#333333] text-sm text-white"
            >
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={21}>21 days</option>
              <option value={30}>30 days</option>
            </select>
          </label>

          <div>
            <div className="text-xs font-bold text-[#888888] uppercase mb-2">Supplier lead-time defaults</div>
            <p className="text-[11px] text-[#999999] mb-2">No lead time is assumed. Missing suppliers can be completed per extracted item.</p>
            {suppliers.map(item => (
              <div key={item.id} className="flex gap-2 mb-2">
                <span className="flex-1 text-sm py-2">{item.name}</span>
                <input
                  type="number"
                  min="1"
                  max="365"
                  placeholder="Days"
                  value={item.days}
                  onChange={event => setSuppliers(previous => previous.map(row =>
                    row.id === item.id ? { ...row, days: event.target.value } : row
                  ))}
                  className="w-24 p-2 bg-[#0B0B0B] border border-[#333333] text-white text-sm"
                />
              </div>
            ))}
            <div className="flex gap-2">
              <input
                type="text"
                value={newSupplierName}
                onChange={event => setNewSupplierName(event.target.value)}
                placeholder="Supplier name"
                className="flex-1 p-2 bg-[#0B0B0B] border border-[#333333] text-white text-sm"
              />
              <button type="button" onClick={addSupplier} className="px-3 bg-[#333333] text-xs font-bold">ADD</button>
            </div>
          </div>

          <div className="pt-3 border-t border-[#333333] flex items-center justify-between">
            <div>
              <div className="text-xs font-bold uppercase">Use demo data</div>
              <div className="text-[11px] text-[#888888]">Continue with the locally supplied demonstration catalogue.</div>
            </div>
            <input type="checkbox" checked={demoData} onChange={event => onToggleDemoData(event.target.checked)} />
          </div>

          <button
            onClick={handleProcessFiles}
            disabled={isProcessing || isReviewing}
            className="w-full py-3 px-4 bg-[#E50000] disabled:bg-[#333333] text-white font-bold text-xs uppercase rounded-[4px]"
          >
            {isProcessing || isReviewing ? 'PROCESSING FILES...' : uploadedFiles.length ? 'UPLOAD & EXTRACT' : 'CONTINUE'}
          </button>
          {(isProcessing || isReviewing) && (
            <p role="status" className="text-[11px] text-[#999999]">
              Provider extraction can take several minutes. Keep this page open while the import status is checked.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
