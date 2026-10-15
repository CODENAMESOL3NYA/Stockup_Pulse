import React, { useState } from 'react';
import { TraceEvent, WapeMetrics } from '../types';

interface StepEvidenceProps {
  traceEvents: TraceEvent[];
  metrics: WapeMetrics | null;
  onBack: () => void;
}

export const StepEvidence: React.FC<StepEvidenceProps> = ({ traceEvents, metrics, onBack }) => {
  const [activeTab, setActiveTab] = useState<'hardware' | 'performance' | 'trace' | 'provenance'>('hardware');

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6 text-white font-sans">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          TECHNICAL STATUS // PYTHON SERVICE EVIDENCE
        </div>
        <h2 className="text-2xl font-black text-white tracking-wider uppercase">
          5. RESULTS &amp; TECHNICAL EVIDENCE
        </h2>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Runtime events and illustrative forecast metrics reported by the backend.
        </p>
      </div>

      {/* Top Metric Cards (AMD Dark Mode #1A1A1A with 2px #E50000 / #00CC66 top border) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#00CC66] rounded-[4px] p-5 shadow-lg">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">MODEL WAPE</div>
          <div className="text-3xl font-black text-white font-mono mt-1">{metrics ? `${(metrics.model_wape * 100).toFixed(1)}%` : 'NOT AVAILABLE'}</div>
          <div className="text-xs font-mono font-bold text-[#888888] mt-1">{metrics?.dataset_type === 'illustrative_fixture' ? 'ILLUSTRATIVE FIXTURE' : metrics ? 'VALIDATION DATASET' : 'NO METRICS'}</div>
          <div className="text-[11px] text-[#888888] mt-0.5 font-mono">{metrics?.sample_count ?? 0} samples</div>
        </div>

        {/* Metric 2: Forecast Accuracy */}
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#00CC66] rounded-[4px] p-5 shadow-lg">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">FORECAST ACCURACY</div>
          <div className="text-3xl font-black text-[#00CC66] font-mono mt-1">{metrics ? `${(metrics.forecast_accuracy * 100).toFixed(1)}%` : 'NOT AVAILABLE'}</div>
          <div className="text-xs font-mono font-bold text-[#888888] mt-1">BASELINE {metrics ? `${(metrics.baseline_accuracy * 100).toFixed(1)}%` : 'NOT AVAILABLE'}</div>
          <div className="text-[11px] text-[#888888] mt-0.5 font-mono">
            Accuracy derived from the reported fixture only
          </div>
        </div>

        {/* Metric 3: Plan Generation Time */}
        <div className="bg-[#1A1A1A] border border-[#333333] border-t-2 border-t-[#E50000] rounded-[4px] p-5 shadow-lg">
          <div className="text-[11px] font-mono font-bold text-[#888888] uppercase tracking-wider">PLAN GENERATION TIME</div>
          <div className="text-3xl font-black text-white font-mono mt-1">NOT MEASURED</div>
          <div className="text-xs text-[#888888] font-mono mt-1">NO REMOTE MODEL CALL IS CONFIGURED</div>
          <div className="text-[11px] text-[#888888] mt-0.5 font-mono">PLAN CALCULATION RUNS LOCALLY</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#333333] flex gap-6">
        <button
          onClick={() => setActiveTab('hardware')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'hardware'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Backend Configuration
        </button>
        <button
          onClick={() => setActiveTab('performance')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'performance'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Performance &amp; WAPE
        </button>
        <button
          onClick={() => setActiveTab('trace')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'trace'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Trace Timeline
        </button>
        <button
          onClick={() => setActiveTab('provenance')}
          className={`pb-3 text-xs font-mono font-bold uppercase tracking-wider border-b-2 transition-colors cursor-pointer ${
            activeTab === 'provenance'
              ? 'border-[#E50000] text-white'
              : 'border-transparent text-[#888888] hover:text-white'
          }`}
        >
          Data Provenance
        </button>
      </div>

      {/* TAB 1: Hardware & AMD Evidence */}
      {activeTab === 'hardware' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Technical Evidence Table */}
            <div className="lg:col-span-7 bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 shadow-xl space-y-4">
              <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-wider">
                CONFIGURATION STATUS
              </div>

              <div className="divide-y divide-[#333333] text-xs font-mono">
                <div className="py-2.5 flex justify-between">
                  <span className="text-[#888888]">GPU ACCELERATOR</span>
                  <span className="font-bold text-white">NOT CONFIGURED</span>
                </div>
                <div className="py-2.5 flex justify-between">
                  <span className="text-[#888888]">ROCM / HIP RUNTIME</span>
                  <span className="font-bold text-[#E50000]">NOT CONFIGURED</span>
                </div>
                <div className="py-2.5 flex justify-between">
                  <span className="text-[#888888]">VISION-LANGUAGE MODEL</span>
                  <span className="text-white">NOT INVOKED</span>
                </div>
                <div className="py-2.5 flex justify-between">
                  <span className="text-[#888888]">INFERENCE ENGINE</span>
                  <span className="text-white">NOT CONFIGURED</span>
                </div>
                <div className="py-2.5 flex justify-between">
                  <span className="text-[#888888]">EXTRACTION LATENCY (AVG)</span>
                  <span className="font-bold text-[#888888]">NOT MEASURED</span>
                </div>
              </div>
            </div>

            {/* Evolus Usage Block */}
            <div className="lg:col-span-5 bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-5 shadow-xl space-y-4">
              <div className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                EXECUTION TELEMETRY COUNTERS
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded-[2px] bg-[#0B0B0B] border border-[#333333]">
                  <div className="text-[#888888]">AGENT CALLS</div>
                  <div className="text-xl font-black text-white mt-1">{traceEvents.filter(event => event.evolus_block === 'agent').length}</div>
                </div>
                <div className="p-3 rounded-[2px] bg-[#0B0B0B] border border-[#333333]">
                  <div className="text-[#888888]">WORKFLOW EXECS</div>
                  <div className="text-xl font-black text-white mt-1">{traceEvents.filter(event => event.evolus_block === 'workflow').length}</div>
                </div>
                <div className="p-3 rounded-[2px] bg-[#0B0B0B] border border-[#333333]">
                  <div className="text-[#888888]">DOCUMENT EXTRACTIONS</div>
                  <div className="text-xl font-black text-white mt-1">{traceEvents.filter(event => event.evolus_block === 'document_extraction').length}</div>
                </div>
                <div className="p-3 rounded-[2px] bg-[#0B0B0B] border border-[#333333]">
                  <div className="text-[#888888]">TOOL CALLS</div>
                  <div className="text-xl font-black text-white mt-1">{traceEvents.filter(event => event.event_type === 'tool_call').length}</div>
                </div>
              </div>
              <div className="text-[11px] text-[#888888] font-mono">
                Counts reflect recorded events; zero means no provider call was recorded.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Performance & WAPE */}
      {activeTab === 'performance' && (
        <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
            ILLUSTRATIVE WAPE FIXTURE
          </h3>
          <p className="text-xs text-[#888888] leading-relaxed font-mono">
            These values are computed from a small synthetic fixture, not historical store sales or a holdout validation set.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-4 rounded-[4px] bg-[#0B0B0B] border border-[#333333] space-y-2">
              <div className="font-bold text-[#FF3333] text-sm uppercase">BASELINE FORECASTER (7-DAY ROLLING)</div>
              <p className="text-[#888888]">
                Simple moving average over unadjusted POS sales history.
              </p>
              <div className="font-bold text-base text-[#FF3333]">WAPE: {metrics ? `${(metrics.baseline_wape * 100).toFixed(2)}%` : 'NOT AVAILABLE'}</div>
            </div>

            <div className="p-4 rounded-[4px] bg-[#0B0B0B] border border-[#00CC66] space-y-2">
              <div className="font-bold text-[#00CC66] text-sm uppercase">STOCKUP PULSE STATISTICAL FORECASTER</div>
              <p className="text-[#888888]">
                Day-of-week weighted exponential smoothing with safety stock buffering.
              </p>
              <div className="font-bold text-base text-[#00CC66]">WAPE: {metrics ? `${(metrics.model_wape * 100).toFixed(2)}%` : 'NOT AVAILABLE'}</div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Trace Events Timeline */}
      {activeTab === 'trace' && (
        <div className="bg-[#0B0B0B] border border-[#333333] rounded-[4px] overflow-hidden">
          <div className="p-4 border-b border-[#333333] flex items-center justify-between">
            <div className="text-xs font-mono font-bold text-[#E50000] uppercase tracking-wider">
              TRACE EVENTS TIMELINE (LATEST AUDIT TRAIL)
            </div>
            <span className="text-xs text-[#888888] font-mono">
              TOTAL RECORDED: {traceEvents.length}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#1A1A1A] border-b border-[#333333] text-[#888888] uppercase font-bold">
                <tr>
                  <th className="px-6 py-3">Event Type</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Device / Endpoint</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#222222]">
                {traceEvents.map((ev, i) => (
                  <tr key={ev.id || i} className="hover:bg-[#1A1A1A]/50">
                    <td className="px-6 py-3 font-bold text-white flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#E50000]" />
                      {ev.event_type.toUpperCase()}
                    </td>
                    <td className="px-4 py-3 text-[#888888]">{ev.timestamp.slice(11, 19) || ev.timestamp}</td>
                    <td className="px-4 py-3 text-white">{ev.endpoint_host}</td>
                    <td className="px-4 py-3 text-[#888888]">{ev.latency_ms ? `${ev.latency_ms.toFixed(1)}ms` : '-'}</td>
                    <td className="px-4 py-3">
                      <span className="inline-block px-2 py-0.5 rounded-[2px] text-[10px] font-bold bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/40 uppercase">
                        {ev.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: Data Provenance */}
      {activeTab === 'provenance' && (
        <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-6 shadow-xl space-y-4 text-xs text-[#CCCCCC] font-mono">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">DATA SOURCES &amp; VALIDATION</h3>
          <ul className="space-y-2 list-disc pl-4 leading-relaxed">
            <li><strong>Price inputs:</strong> Supplied by the dashboard fixture or current request; source verification is not automated.</li>
            <li><strong>Retail price records:</strong> Scraper output or illustrative seed records, identified by source type.</li>
            <li><strong>Sales history:</strong> No store sales dataset is connected to this demo.</li>
            <li><strong>Plan calculation:</strong> Deterministic greedy allocation with a strict budget ceiling; it is not a MILP solver.</li>
          </ul>
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
        <span className="inline-block px-3 py-1 rounded-[2px] text-xs font-mono font-bold bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/30 uppercase">
          FIXTURE DATA IS LABELED
        </span>
      </div>
    </div>
  );
};
