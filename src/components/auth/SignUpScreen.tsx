import React, { useState } from 'react';
import { registerUser } from '../../services/api';
import { AuthUser } from '../../types';

interface SignUpScreenProps {
  onSuccess: (user: AuthUser) => void;
  onGoToLogin: () => void;
}

export const SignUpScreen: React.FC<SignUpScreenProps> = ({ onSuccess, onGoToLogin }) => {
  const [fullName, setFullName] = useState('');
  const [shopName, setShopName] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!fullName.trim()) {
      setErrorMsg('Please enter your full name.');
      return;
    }
    if (!whatsapp.trim()) {
      setErrorMsg('Please enter your WhatsApp number.');
      return;
    }
    if (!password) {
      setErrorMsg('Please enter a password.');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Use a password with at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match. Please verify.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await registerUser(
        fullName.trim(),
        shopName.trim() || 'Spaza Store',
        whatsapp.trim(),
        password
      );

      if (user) {
        onSuccess(user);
      } else {
        setErrorMsg('Registration failed. Please retry.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Registration error occurred.');
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
            ACCOUNT PROVISIONING
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
              Create Your Account
            </h2>
            <p className="text-xs text-[#888888] mt-1">
              Join South African spaza shops maximizing margin and eliminating stockouts.
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
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g., Mpho Khumalo"
                className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                Shop Name
              </label>
              <input
                type="text"
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
                placeholder="e.g., Sunnyside Spaza"
                className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                WhatsApp Number
              </label>
              <input
                type="text"
                value={whatsapp}
                onChange={(e) => setWhatsapp(e.target.value)}
                placeholder="+27 82 000 0000"
                className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all font-mono"
                required
              />
              <p className="text-[11px] text-[#888888] mt-1">
                This will be used to send your purchase orders via our WhatsApp bot.
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
                placeholder="Create password"
                className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white placeholder-[#888888] focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
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
              {isLoading ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT'}
            </button>
          </form>

          {/* Secondary Link to Log In */}
          <div className="mt-4 pt-4 border-t border-[#333333] text-center">
            <p className="text-xs text-[#888888]">
              Already have an account?{' '}
              <button
                type="button"
                onClick={onGoToLogin}
                className="text-[#888888] hover:text-white font-semibold transition-colors cursor-pointer"
              >
                Log in
              </button>
            </p>
          </div>
        </div>

        {/* Footer Hardware Tag */}
        <div className="text-center mt-6 text-[11px] font-mono text-[#888888]">
          ROCm 6.2.4 // AMD ACCELERATED RESTOCKING
        </div>
      </div>
    </div>
  );
};
