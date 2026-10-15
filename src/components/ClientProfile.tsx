import React, { useState } from 'react';
import { AuthUser } from '../types';

interface ClientProfileProps {
  user: AuthUser;
  onUpdateUser: (updated: AuthUser) => void;
  onBackToDashboard: () => void;
}

export const ClientProfile: React.FC<ClientProfileProps> = ({
  user,
  onUpdateUser,
  onBackToDashboard
}) => {
  const [fullName, setFullName] = useState(user.full_name);
  const [shopName, setShopName] = useState(user.shop_name);
  const [phone, setPhone] = useState(user.phone);

  const [planningHorizon, setPlanningHorizon] = useState('14 days');
  const [preferredSupplier, setPreferredSupplier] = useState('Makro');
  const [deliveryAddress, setDeliveryAddress] = useState('Shop 4, Nelson Mandela Ave, Sunnyside, Pretoria, 0002');
  const [showSavedToast, setShowSavedToast] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateUser({
      ...user,
      full_name: fullName.trim() || user.full_name,
      shop_name: shopName.trim() || user.shop_name,
      phone: phone.trim() || user.phone
    });
    setShowSavedToast(true);
    setTimeout(() => setShowSavedToast(false), 3000);
  };

  const userInitial = (fullName.trim().charAt(0) || 'M').toUpperCase();

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 animate-fade-in font-sans text-white">
      {/* Top Bar with Back Button */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onBackToDashboard}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-[4px] text-xs font-bold tracking-wider uppercase text-white bg-transparent border border-[#333333] hover:border-[#E50000] hover:bg-[#1A1A1A] transition-all cursor-pointer"
        >
          <span>&larr; BACK TO DASHBOARD</span>
        </button>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[2px] bg-[#1A1A1A] border border-[#333333] text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-[#00CC66]" />
          <span className="text-[#00CC66] font-bold">VERIFIED SPAZA OWNER</span>
        </div>
      </div>

      {/* Screen Title */}
      <div className="mb-8">
        <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
          OPERATIONAL PROFILE CONFIGURATION
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-wider uppercase">
          CLIENT PROFILE &amp; SETTINGS
        </h1>
        <p className="text-xs text-[#888888] mt-1 tracking-wide">
          Manage your Spaza store identity, WhatsApp automated ordering parameters, and supplier routing rules.
        </p>
      </div>

      {/* Gamification / Value Add Stats Cards (AMD Dark Mode #1A1A1A with #E50000 / #00CC66 2px top border) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="bg-[#1A1A1A] rounded-[4px] border border-[#333333] border-t-2 border-t-[#00CC66] p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#888888]">
              Total Rands Saved via Scraped Market Swaps
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-[2px] bg-[#0B0B0B] text-[#00CC66] border border-[#00CC66]/40 font-bold">
              SAVINGS
            </span>
          </div>
          <div className="text-3xl font-black text-white mt-2 font-mono">
            R 482.50
          </div>
          <div className="text-xs font-semibold text-[#00CC66] mt-2 font-mono">
            +14.2% margin preserved from Makro &amp; Shoprite live scrapes
          </div>
        </div>

        <div className="bg-[#1A1A1A] rounded-[4px] border border-[#333333] border-t-2 border-t-[#E50000] p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#888888]">
              Average Monthly Restock Budget
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-[2px] bg-[#0B0B0B] text-[#E50000] border border-[#E50000]/40 font-bold">
              BUDGET
            </span>
          </div>
          <div className="text-3xl font-black text-white mt-2 font-mono">
            R 12,500.00
          </div>
          <div className="text-xs font-semibold text-[#888888] mt-2 font-mono">
            Optimal knapsack tier // Bi-weekly automated bulk replenishment
          </div>
        </div>
      </div>

      {/* Main Settings Grid */}
      <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Basic Info */}
        <div className="bg-[#1A1A1A] rounded-[4px] border border-[#333333] p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 pb-4 border-b border-[#333333] mb-5">
              <div className="w-9 h-9 rounded-[2px] bg-[#0B0B0B] text-white font-mono font-bold flex items-center justify-center text-sm border border-[#333333]">
                {userInitial}
              </div>
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">Basic Information</h2>
                <p className="text-xs text-[#888888]">Account credentials and Spaza identity</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
                  placeholder="Mpho Khumalo"
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
                  className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
                  placeholder="Sunnyside Spaza"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                  WhatsApp Number
                </label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white font-mono focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all"
                  placeholder="+27 82 123 4567"
                  required
                />
                <p className="text-[11px] text-[#888888] mt-1.5">
                  Used by our WhatsApp bot to send purchase orders and dispatch confirmations.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#333333]">
            <span className="text-xs text-[#888888] font-mono">
              CREDENTIALS SECURED IN LOCAL SQLITE DATABASE
            </span>
          </div>
        </div>

        {/* Right Column: Operational Settings */}
        <div className="bg-[#1A1A1A] rounded-[4px] border border-[#333333] p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 pb-4 border-b border-[#333333] mb-5">
              <div className="w-9 h-9 rounded-[2px] bg-[#0B0B0B] text-[#E50000] font-mono font-bold flex items-center justify-center text-xs border border-[#333333]">
                OPS
              </div>
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">Operational Settings</h2>
                <p className="text-xs text-[#888888]">Restock frequency, preferred supplier, and delivery address</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                  Default Planning Horizon
                </label>
                <select
                  value={planningHorizon}
                  onChange={(e) => setPlanningHorizon(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white focus:border-[#E50000] focus:outline-none transition-all cursor-pointer"
                >
                  <option value="7 days">Next 7 days (Weekly restock)</option>
                  <option value="14 days">Next 14 days (Bi-weekly restock - Recommended)</option>
                  <option value="30 days">Next 30 days (Monthly restock)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                  Preferred Main Supplier
                </label>
                <select
                  value={preferredSupplier}
                  onChange={(e) => setPreferredSupplier(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white focus:border-[#E50000] focus:outline-none transition-all cursor-pointer"
                >
                  <option value="Makro">Makro (Wholesale Cash &amp; Carry)</option>
                  <option value="Shoprite">Shoprite (B2B Bulk)</option>
                  <option value="Usave">Usave (Value Groceries)</option>
                  <option value="Jumbo">Jumbo Cash &amp; Carry</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#888888] uppercase tracking-wider mb-1.5">
                  Delivery Address (Injected into Purchase Orders)
                </label>
                <textarea
                  rows={3}
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  className="w-full p-3 bg-[#0B0B0B] border border-[#333333] rounded-[4px] text-sm text-white focus:border-[#E50000] focus:ring-1 focus:ring-[#E50000] focus:outline-none transition-all resize-none"
                  placeholder="Enter street address, shop unit, and town..."
                  required
                />
                <p className="text-[11px] text-[#888888] mt-1">
                  Supplier drivers automatically receive this address on approved purchase order dispatches.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#333333] flex items-center justify-between">
            {showSavedToast ? (
              <span className="text-xs font-bold text-[#00CC66] uppercase tracking-wider font-mono">
                [SETTINGS SAVED TO DATABASE]
              </span>
            ) : (
              <span className="text-[11px] text-[#888888] font-mono">
                ROCm 6.2.4 CONFIGURATION
              </span>
            )}
            <button
              type="submit"
              className="px-5 py-2.5 rounded-[4px] bg-[#E50000] hover:bg-[#CC0000] active:bg-[#4A0000] text-white text-xs font-bold uppercase tracking-wider transition-all shadow-[0_0_12px_rgba(229,0,0,0.3)] cursor-pointer"
            >
              SAVE SETTINGS
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
