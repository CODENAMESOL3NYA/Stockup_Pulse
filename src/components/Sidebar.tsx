import React from 'react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  demoData: boolean;
  onToggleDemoData: (val: boolean) => void;
  shopName?: string;
  userName?: string;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  demoData,
  onToggleDemoData,
  shopName = 'Sunnyside Spaza',
  userName = 'Mpho Khumalo',
  onLogout,
}) => {
  const menuItems = [
    { id: 'home', label: 'HOME' },
    { id: 'upload', label: '1. DATA & UPLOADS' },
    { id: 'catalogue', label: '2. REVIEW CATALOGUE' },
    { id: 'plan', label: '3. RESTOCKING PLAN' },
    { id: 'orders', label: '4. APPROVE & ORDERS' },
    { id: 'reports', label: 'ANALYTICS & REPORTS' },
    { id: 'evidence', label: 'TECHNICAL EVIDENCE' },
    { id: 'whatsapp', label: 'WHATSAPP CHANNEL', badge: 'BOT' },
    { id: 'codebase', label: 'PYTHON BACKEND', badge: 'ROCM' },
  ];

  return (
    <aside className="w-64 bg-[#0B0B0B] text-white flex flex-col justify-between shrink-0 min-h-screen select-none border-r border-[#333333] font-sans">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-[#333333]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-base font-black tracking-wider text-white uppercase">
              STOCKUP PULSE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-[2px] bg-[#1A1A1A] text-[#E50000] border border-[#333333] font-bold">
              AMD
            </span>
          </div>
          <div className="h-[2px] w-12 bg-[#E50000] mb-2 shadow-[0_0_8px_rgba(229,0,0,0.6)]" />
          <div className="text-[11px] text-[#888888] font-medium leading-none tracking-wide">
            Smarter stock. Stronger shops.
          </div>
        </div>

        {/* Navigation list */}
        <nav className="p-2 space-y-1">
          {menuItems.map((item) => {
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-[2px] text-xs font-bold tracking-wider uppercase transition-all duration-150 cursor-pointer text-left ${
                  isActive
                    ? 'bg-[#1A1A1A] text-white border-l-4 border-[#E50000]'
                    : 'text-[#888888] hover:text-white hover:bg-[#1A1A1A]/60 border-l-4 border-transparent'
                }`}
              >
                <span>{item.label}</span>
                {item.badge && (
                  <span
                    className={`text-[9px] font-mono px-1 py-0.5 rounded-[2px] font-bold ${
                      isActive
                        ? 'bg-[#E50000] text-white'
                        : 'bg-[#1A1A1A] text-[#888888] border border-[#333333]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Shop Info & Demo Data Switch */}
      <div className="p-4 border-t border-[#333333] bg-[#0B0B0B] space-y-3">
        {/* Clickable Client Info block in sidebar */}
        <div
          onClick={() => onSelectTab('profile')}
          className="p-2.5 rounded-[2px] bg-[#1A1A1A] border border-[#333333] hover:border-[#E50000] transition-colors cursor-pointer group"
          title="Open Client Profile & Operational Settings"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-white group-hover:text-[#E50000] transition-colors uppercase truncate">
              {shopName}
            </div>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-[2px] bg-[#0B0B0B] text-[#00CC66] border border-[#00CC66]/30">
              ACTIVE
            </span>
          </div>
          <div className="text-[10px] text-[#888888] mt-1 font-mono">
            {userName} // PRETORIA
          </div>
        </div>

        {/* Demo Data Toggle */}
        <div className="pt-2 border-t border-[#333333] flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-white uppercase tracking-wider">Demo Data</div>
            <div className="text-[10px] text-[#888888] font-mono">HACKATHON MODE</div>
          </div>
          <button
            type="button"
            onClick={() => onToggleDemoData(!demoData)}
            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-xs border border-[#333333] transition-colors duration-200 ease-in-out ${
              demoData ? 'bg-[#E50000]' : 'bg-[#1A1A1A]'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-xs bg-white shadow-xs transition duration-200 ease-in-out ${
                demoData ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Dedicated Sidebar Logout Button */}
        {onLogout && (
          <div className="pt-2 border-t border-[#333333]">
            <button
              onClick={onLogout}
              className="w-full py-2 px-3 rounded-[2px] text-xs font-bold uppercase tracking-wider text-[#888888] hover:text-white bg-[#1A1A1A] border border-[#333333] hover:border-[#E50000] hover:bg-[#4A0000]/40 transition-colors cursor-pointer text-center"
            >
              LOG OUT
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
