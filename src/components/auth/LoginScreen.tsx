import React, { useState } from 'react';
import { loginUser } from '../../services/api';
import { AuthUser } from '../../types';

interface LoginScreenProps {
  onSuccess: (user: AuthUser) => void;
  onGoToSignUp: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onSuccess, onGoToSignUp }) => {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!phone.trim()) {
      setErrorMsg('Please enter your WhatsApp number.');
      return;
    }
    if (!password) {
      setErrorMsg('Please enter your password.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await loginUser(phone, password);
      if (user) {
        onSuccess(user);
      } else {
        setErrorMsg('Invalid WhatsApp number or password.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed. Please retry.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0B0B] text-white flex flex-col justify-center items-center px-4 py-8 animate-fade-in font-sans">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-block px-3 py-1 bg-[#1A1A1A] border border-[#333333] rounded-[4px] text-[11px] font-mono font-bold text-[#E50000] tracking-widest uppercase mb-3">
            AUTHENTICATION GATEWAY
          </div>
          <h1 className="text-2xl font-black text-white tracking-wider uppercase">
            STOCKUP PULSE
          </h1>
          <p className="text-xs text-[#888888] mt-1 tracking-wide">
            Smarter stock. Stronger shops.
          </p>
        </div>

        {/* Form Container: #1A1A1A, 1px solid #333333, rounded-[4px] */}
        <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] p-6 sm:p-8 shadow-2xl">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-white uppercase tracking-wide">
              Spaza Shopkeeper Login
            </h2>
            <p className="text-xs text-[#888888] mt-1">
              Enter your WhatsApp number to manage orders and restock runs.
            </p>
          </div>

          {errorMsg && (
            <div className="mb-5 p-3 bg-[#1A1A1A] border border-[#FF3333] border-l-4 border-l-[#FF3333] rounded-[2px] text-xs text-[#FFFFFF]">
              <span className="font-bold text-[#FF3333] uppercase mr-1">ERROR:</span> {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                WhatsApp Number
              </label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+27 82 000 0000"
                className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all font-mono"
                required
              />
              <p className="text-[11px] text-[#888888] mt-1">
                Purchase orders and dispatch alerts are routed to this WhatsApp line.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
                required
              />
            </div>

            {/* Primary Action Button: #E50000, white text, sharp corners, hover #CC0000 */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-[#E50000] hover:bg-[#CC0000] active:bg-[#4A0000] text-white font-bold text-xs uppercase tracking-wider rounded-[4px] transition-all shadow-[0_0_12px_rgba(229,0,0,0.35)] cursor-pointer disabled:opacity-50 mt-2"
            >
              {isLoading ? 'AUTHENTICATING...' : 'LOG IN'}
            </button>
          </form>

          {/* Secondary Link to Sign Up */}
          <div className="mt-4 text-center">
            <p className="text-xs text-[#888888]">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={onGoToSignUp}
                className="text-[#888888] hover:text-white font-semibold transition-colors cursor-pointer"
              >
                Sign up here
              </button>
            </p>
          </div>
        </div>

        {/* Footer Hardware Tag */}
        <div className="text-center mt-6 text-[11px] font-mono text-[#888888]">
          ROCm 6.2.4 // SECURED LOCAL SQLITE DATABASE
        </div>
      </div>
    </div>
  );
};
