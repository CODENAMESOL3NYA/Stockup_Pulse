import React, { useEffect, useState } from 'react';

interface SplashScreenProps {
  onComplete: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onComplete }) => {
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // 2.5 seconds timer with progress bar
    const interval = 25; // 25ms steps
    const totalDuration = 2500;
    const stepIncrement = (interval / totalDuration) * 100;

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          return 100;
        }
        return prev + stepIncrement;
      });
    }, interval);

    const fadeOutTimeout = setTimeout(() => {
      setIsFadingOut(true);
    }, 2200);

    const completeTimeout = setTimeout(() => {
      onComplete();
    }, totalDuration);

    return () => {
      clearInterval(timer);
      clearTimeout(fadeOutTimeout);
      clearTimeout(completeTimeout);
    };
  }, [onComplete]);

  const handleSkip = () => {
    setIsFadingOut(true);
    setTimeout(() => {
      onComplete();
    }, 200);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0B0B0B] text-white transition-opacity duration-300 ${
        isFadingOut ? 'opacity-0 scale-98 pointer-events-none' : 'opacity-100 scale-100'
      }`}
    >
      <div className="animate-fade-in flex flex-col items-center text-center max-w-lg px-6">
        {/* Hardware Status Tag */}
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-4">
          AMD DEVELOPER HACKATHON ACT III // REINVENT COMMERCE
        </div>

        {/* Brand Name */}
        <h1 className="text-4xl sm:text-5xl font-black text-white tracking-wider uppercase mb-2">
          STOCKUP PULSE
        </h1>

        {/* Accent: Single, sharp #E50000 (AMD Red) 2px horizontal line */}
        <div className="w-24 h-[2px] bg-[#E50000] shadow-[0_0_12px_rgba(229,0,0,0.6)] mb-4" />

        {/* Tagline */}
        <p className="text-base font-medium text-[#888888] tracking-wide mb-6">
          Smarter stock. Stronger shops.
        </p>

        {/* Technical Subtitle */}
        <p className="text-xs text-[#888888] max-w-sm mb-8 leading-relaxed font-mono">
          PYTHON BACKEND // DETERMINISTIC BUDGET ALLOCATION // PROVIDERS UNCONFIGURED
        </p>

        {/* 2.5s Auto-transition indicator */}
        <div className="w-56 bg-[#1A1A1A] border border-[#333333] rounded-xs h-1 overflow-hidden mb-6">
          <div
            className="bg-[#E50000] h-full transition-all duration-75 ease-linear shadow-[0_0_8px_#E50000]"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>

        {/* Skip Button: Transparent background, #FFFFFF text, #E50000 border on hover */}
        <button
          onClick={handleSkip}
          className="text-xs font-semibold text-white tracking-wider uppercase py-2 px-5 bg-transparent border border-[#333333] hover:border-[#E50000] hover:bg-[#1A1A1A] rounded-xs transition-all duration-200 cursor-pointer"
        >
          CONTINUE TO LOGIN
        </button>
      </div>
    </div>
  );
};
