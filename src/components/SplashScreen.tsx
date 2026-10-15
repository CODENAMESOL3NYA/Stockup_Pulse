import React, { useEffect } from 'react';
import { ShoppingCart, ArrowRight, Sparkles } from 'lucide-react';

interface SplashScreenProps {
  onFinish: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onFinish }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onFinish();
    }, 2500);
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <div className="fixed inset-0 bg-[#101828] text-white flex flex-col items-center justify-center p-6 z-50 select-none animate-in fade-in duration-500">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Animated Brand Logo */}
        <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-tr from-blue-700 to-blue-500 flex items-center justify-center shadow-2xl shadow-blue-500/40 ring-4 ring-blue-500/20 animate-bounce duration-1000">
          <ShoppingCart className="w-10 h-10 text-white" />
        </div>

        {/* Title and Tagline */}
        <div className="space-y-2">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white">
            StockUp Pulse
          </h1>
          <p className="text-lg md:text-xl text-blue-200/80 font-medium">
            Smarter stock. Stronger shops.
          </p>
        </div>

        {/* Track Badge */}
        <div>
          <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/50">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            AMD Hackathon ACT III &bull; Reinvent Commerce
          </span>
        </div>

        <p className="text-xs text-slate-400">
          AI-Powered Restocking Agent for South African Spaza Shops
        </p>

        {/* Quick Skip Button */}
        <div className="pt-8">
          <button
            onClick={onFinish}
            className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            Skip to Login
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
