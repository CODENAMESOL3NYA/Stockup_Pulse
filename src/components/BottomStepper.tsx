import React from 'react';

interface BottomStepperProps {
  currentStep: number;
  onSelectStep: (step: number) => void;
  maxStepReached: number;
}

export const BottomStepper: React.FC<BottomStepperProps> = ({
  currentStep,
  onSelectStep,
  maxStepReached,
}) => {
  const steps = [
    { number: 1, label: 'UPLOAD & SETTINGS' },
    { number: 2, label: 'REVIEW CATALOGUE' },
    { number: 3, label: 'RESTOCKING PLAN' },
    { number: 4, label: 'APPROVE & CREATE ORDERS' },
    { number: 5, label: 'RESULTS & EVIDENCE' },
  ];

  return (
    <div className="bg-[#0B0B0B] border-t border-[#333333] px-6 py-3 shrink-0 font-sans">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        {steps.map((step, index) => {
          const isActive = currentStep === step.number;
          const isCompleted = step.number < currentStep || step.number <= maxStepReached;
          const isClickable = step.number <= maxStepReached + 1;

          return (
            <React.Fragment key={step.number}>
              {/* Step indicator */}
              <button
                disabled={!isClickable}
                onClick={() => onSelectStep(step.number)}
                className={`flex items-center gap-2 group transition-all text-left ${
                  isClickable ? 'cursor-pointer' : 'cursor-not-allowed opacity-40'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-[2px] flex items-center justify-center text-[11px] font-mono font-bold transition-all ${
                    isActive
                      ? 'bg-[#E50000] text-white shadow-[0_0_8px_rgba(229,0,0,0.6)]'
                      : isCompleted
                      ? 'bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/50'
                      : 'bg-[#1A1A1A] text-[#888888] border border-[#333333]'
                  }`}
                >
                  {step.number}
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] font-mono text-[#888888]">
                    STEP {step.number} OF 5
                  </span>
                  <span
                    className={`text-[11px] tracking-wider uppercase font-bold ${
                      isActive
                        ? 'text-white border-b border-[#E50000] pb-0.5'
                        : isCompleted
                        ? 'text-[#CCCCCC]'
                        : 'text-[#888888]'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              </button>

              {/* Connecting line */}
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-[1px] mx-3 transition-colors ${
                    step.number < currentStep ? 'bg-[#00CC66]/40' : 'bg-[#333333]'
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
