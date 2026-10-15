import React, { useState } from 'react';
import { ShoppingCart, Lock, Phone, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (user: { name: string; shop_name: string; phone: string }) => void;
  onGoToSignUp: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess, onGoToSignUp }) => {
  const [phone, setPhone] = useState('+27 82 123 4567');
  const [password, setPassword] = useState('spaza123');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) {
      setError('Please enter your WhatsApp number.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    // Authenticate
    setError(null);
    onLoginSuccess({
      name: 'Mpho Khumalo',
      shop_name: 'Sunnyside Spaza',
      phone: phone.trim()
    });
  };

  const handleUseDemo = () => {
    setPhone('+27 82 123 4567');
    setPassword('spaza123');
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col justify-center items-center p-6 animate-in fade-in duration-300">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8 space-y-2">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-xl shadow-blue-500/20 mb-3">
            <ShoppingCart className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Log in to StockUp Pulse
          </h1>
          <p className="text-xs text-slate-500">
            Enter your WhatsApp number to access your spaza restocking agent
          </p>
        </div>

        {/* Auth Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-7 shadow-xl shadow-slate-200/50 space-y-5">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                WhatsApp Number
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Phone className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+27 82 000 0000"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Used to dispatch purchase orders and communicate via WhatsApp webhook.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Log In</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Demo account helper */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-400">Sunnyside Spaza demo?</span>
            <button
              type="button"
              onClick={handleUseDemo}
              className="text-blue-600 font-semibold hover:underline cursor-pointer flex items-center gap-1"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Fill Demo Login
            </button>
          </div>
        </div>

        {/* Footer Link to Sign Up */}
        <div className="text-center mt-6 text-xs text-slate-500">
          Don&apos;t have an account?{' '}
          <button
            onClick={onGoToSignUp}
            className="text-blue-600 font-bold hover:underline cursor-pointer"
          >
            Sign up here
          </button>
        </div>
      </div>
    </div>
  );
};
