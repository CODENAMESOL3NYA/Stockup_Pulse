import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { BottomStepper } from './components/BottomStepper';
import { HomeHero } from './components/HomeHero';
import { Step1Upload } from './components/Step1Upload';
import { Step2Catalogue } from './components/Step2Catalogue';
import { Step3Plan } from './components/Step3Plan';
import { Step4Approve } from './components/Step4Approve';
import { Step5Orders } from './components/Step5Orders';
import { StepEvidence } from './components/StepEvidence';
import { WhatsAppSimulator } from './components/WhatsAppSimulator';
import { CodebaseExplorer } from './components/CodebaseExplorer';
import { SplashScreen } from './components/auth/SplashScreen';
import { LoginScreen } from './components/auth/LoginScreen';
import { SignUpScreen } from './components/auth/SignUpScreen';
import { ClientProfile } from './components/ClientProfile';
import {
  ProductItem,
  RestockingPlan,
  PurchaseOrder,
  TraceEvent,
  AuthUser,
  WapeMetrics,
  FileImportCandidate,
  FileImportReview
} from './types';
import {
  generatePlan,
  approvePlan,
  createPurchaseOrders,
  fetchTraceEvents,
  fetchWapeMetrics,
  logoutUser,
  uploadPlanningFiles
} from './services/api';
import { User, Bell, Shield, Sparkles, LogOut, MessageSquare } from 'lucide-react';

export default function App() {
  const [currentPage, setCurrentPage] = useState<'splash' | 'login' | 'signup' | 'dashboard'>('splash');
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [currentTab, setCurrentTab] = useState<string>('home');
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [maxStepReached, setMaxStepReached] = useState<number>(1);
  const [demoData, setDemoData] = useState<boolean>(true);
  const [budget, setBudget] = useState<number>(3000.00);
  const [horizonDays, setHorizonDays] = useState<number>(14);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isApproved, setIsApproved] = useState<boolean>(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState<boolean>(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // Initial catalogue items matching mockup exactly
  const [products, setProducts] = useState<ProductItem[]>([
    {
      id: 'p1',
      product: 'Coca-Cola 440ml',
      pack_size: '24 x 440ml',
      supplier_price: 289.00,
      our_price: 349.00,
      unit_price: 12.09,
      supplier: 'Makro',
      status: 'Confirmed',
      confidence: 0.98,
      recommended_qty: 96,
      at_risk: false,
      is_out_of_stock: false,
      category: 'Beverages'
    },
    {
      id: 'p2',
      product: 'Sprite 440ml',
      pack_size: '24 x 440ml',
      supplier_price: 275.50,
      our_price: 329.00,
      unit_price: 11.48,
      supplier: 'Makro',
      status: 'Confirmed',
      confidence: 0.96,
      recommended_qty: 72,
      at_risk: false,
      is_out_of_stock: false,
      category: 'Beverages'
    },
    {
      id: 'p3',
      product: 'Chicken Flavour Noodles',
      pack_size: '5 x 70g',
      supplier_price: 42.00,
      our_price: 54.00,
      unit_price: 8.40,
      supplier: 'Shoprite',
      status: 'Confirmed',
      confidence: 0.93,
      recommended_qty: 50,
      at_risk: true,
      is_out_of_stock: false,
      category: 'Instant Food'
    },
    {
      id: 'p4',
      product: 'Brown Bread',
      pack_size: '1 x 700g',
      supplier_price: 16.50,
      our_price: 24.00,
      unit_price: 16.50,
      supplier: 'Usave',
      status: 'Needs review',
      confidence: 0.67,
      recommended_qty: 20,
      at_risk: true,
      is_out_of_stock: false,
      category: 'Bakery'
    },
    {
      id: 'p5',
      product: 'Milk (long life)',
      pack_size: '6 x 1L',
      supplier_price: 84.00,
      our_price: 99.00,
      unit_price: 13.90,
      supplier: 'Usave',
      status: 'Confirmed',
      confidence: 0.92,
      recommended_qty: 24,
      at_risk: false,
      is_out_of_stock: false,
      category: 'Dairy'
    },
    {
      id: 'p6',
      product: 'Cooking Oil',
      pack_size: '6 x 1L',
      supplier_price: 210.00,
      our_price: 259.00,
      unit_price: 18.75,
      supplier: 'Makro',
      status: 'Confirmed',
      confidence: 0.89,
      recommended_qty: 20,
      at_risk: true,
      is_out_of_stock: false,
      category: 'Cooking Essentials'
    }
  ]);

  // Restocking plan state
  const [plan, setPlan] = useState<RestockingPlan | null>(null);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [wapeMetrics, setWapeMetrics] = useState<WapeMetrics | null>(null);

  // Initialize plan & trace on mount
  useEffect(() => {
    if (currentUser) recomputePlan(budget, horizonDays, products);
    fetchTraceEvents().then(res => setTraceEvents(res.events));
    if (currentUser) fetchWapeMetrics().then(setWapeMetrics);
  }, [currentUser]);

  const recomputePlan = async (currentBudget: number, horizon: number, items: ProductItem[], allowSubs = true) => {
    const newPlan = await generatePlan(currentBudget, horizon, items, allowSubs);
    setPlan(newPlan);
  };

  const handleUpdateProduct = (updated: ProductItem) => {
    const updatedList = products.map(p => p.id === updated.id ? updated : p);
    setProducts(updatedList);
    recomputePlan(budget, horizonDays, updatedList);
  };

  const handleProcessFiles = async (
    files: File[],
    supplierLeadTimes: Record<string, number>,
    planningHorizon: number,
    useDemoData: boolean
  ): Promise<FileImportReview | null> => {
    if (!files.length) {
      if (!useDemoData) throw new Error('Upload sales, stock, and leaflet files or enable demo data.');
      await recomputePlan(budget, planningHorizon, products);
      setCurrentStep(2);
      setCurrentTab('catalogue');
      setMaxStepReached(prev => Math.max(prev, 2));
      return null;
    }
    setIsProcessing(true);
    try {
      return await uploadPlanningFiles(files, supplierLeadTimes, planningHorizon);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleImportCandidates = (candidates: FileImportCandidate[]) => {
    const imported: ProductItem[] = candidates.map((candidate, index) => ({
      id: `import-${candidate.id}-${index}`,
      product: candidate.matched_product,
      pack_size: candidate.pack_size,
      supplier_price: Number(candidate.supplier_price),
      our_price: Number(candidate.our_price),
      unit_price: Number(candidate.unit_price),
      supplier: candidate.supplier,
      status: 'Confirmed',
      confidence: candidate.confidence,
      recommended_qty: Number(candidate.recommended_qty),
      at_risk: candidate.at_risk,
      is_out_of_stock: candidate.current_stock === 0,
      category: 'Imported',
      source: 'file_import',
      reviewed: true,
      lead_time_days: Number(candidate.lead_time_days),
      retail_price_verified: candidate.retail_price_verified === true,
      currency: candidate.currency || '',
      currency_verified: candidate.currency_verified === true
    }));
    setProducts(imported);
    void recomputePlan(budget, horizonDays, imported);
    setCurrentStep(2);
    setCurrentTab('catalogue');
    setMaxStepReached(prev => Math.max(prev, 2));
  };

  const handleSimulateStockoutSub = () => {
    // Toggle stockout on Coca-Cola to demonstrate deterministic brand substitution
    const toggled = products.map(p => {
      if (p.product.includes('Coca-Cola')) {
        return { ...p, is_out_of_stock: !p.is_out_of_stock };
      }
      return p;
    });
    setProducts(toggled);
    recomputePlan(budget, horizonDays, toggled);
  };

  const handleSubmitApproval = async () => {
    if (!isApproved) {
      setApprovalError("Approval checkbox must be checked.");
      return;
    }

    setIsSubmittingApproval(true);
    setApprovalError(null);

    try {
      // 1. Approve plan in backend
      await approvePlan(true, plan?.plan_id);

      // 2. Mint purchase orders
      const createdOrders = await createPurchaseOrders(true, plan?.plan_id);
      setOrders(createdOrders);

      // Refresh trace events
      const traceRes = await fetchTraceEvents();
      setTraceEvents(traceRes.events);

      setIsSubmittingApproval(false);
      setCurrentStep(5);
      setCurrentTab('orders');
      setMaxStepReached(prev => Math.max(prev, 5));
    } catch (err: any) {
      setIsSubmittingApproval(false);
      setApprovalError(err.message || "Failed to create orders");
    }
  };

  // Stepper navigation routing
  const handleSelectStep = (step: number) => {
    setCurrentStep(step);
    if (step === 1) setCurrentTab('upload');
    else if (step === 2) setCurrentTab('catalogue');
    else if (step === 3) setCurrentTab('plan');
    else if (step === 4) setCurrentTab('orders');
    else if (step === 5) setCurrentTab('evidence');
  };

  const handleSelectSidebarTab = (tab: string) => {
    setCurrentTab(tab);
    if (tab === 'upload') setCurrentStep(1);
    else if (tab === 'catalogue') setCurrentStep(2);
    else if (tab === 'plan') setCurrentStep(3);
    else if (tab === 'orders') setCurrentStep(isApproved ? 5 : 4);
    else if (tab === 'evidence') setCurrentStep(5);
  };

  const handleLogout = () => {
    void logoutUser();
    setCurrentUser(null);
    setCurrentPage('login');
  };

  // Auth routing: Splash Screen, Login Screen, and Sign-Up Screen wrapping dashboard
  if (currentPage === 'splash') {
    return <SplashScreen onComplete={() => setCurrentPage('login')} />;
  }

  if (currentPage === 'login') {
    return (
      <LoginScreen
        onSuccess={(user) => {
          setCurrentUser(user);
          setCurrentPage('dashboard');
        }}
        onGoToSignUp={() => setCurrentPage('signup')}
      />
    );
  }

  if (currentPage === 'signup') {
    return (
      <SignUpScreen
        onSuccess={(user) => {
          setCurrentUser(user);
          setCurrentPage('dashboard');
        }}
        onGoToLogin={() => setCurrentPage('login')}
      />
    );
  }

  const shopName = currentUser?.shop_name || 'Sunnyside Spaza';
  const userName = currentUser?.full_name || 'Mpho Khumalo';
  const userPhone = currentUser?.phone || '+27 82 123 4567';
  const userInitial = userName.trim().charAt(0).toUpperCase() || 'M';

  return (
    <div className="flex h-screen bg-[#0B0B0B] text-white font-sans overflow-hidden animate-fade-in">
      {/* Dark Navy / Black Persistent Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={handleSelectSidebarTab}
        demoData={demoData}
        onToggleDemoData={(val) => setDemoData(val)}
        shopName={shopName}
        userName={userName}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#0B0B0B]">
        {/* Top Navbar */}
        <header className="h-14 bg-[#0B0B0B] border-b border-[#333333] px-6 flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-[2px] bg-[#1A1A1A] border border-[#333333] text-white flex items-center gap-1.5 uppercase font-mono">
              <span className="w-2 h-2 rounded-full bg-[#00CC66]" />
              {shopName} // PRETORIA CENTRAL
            </span>
            <span className="text-[11px] text-[#888888] font-mono hidden sm:inline">
              ROCM 6.2.4 // QWEN2.5-VL-7B-INSTRUCT
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* WhatsApp Integration Status Pill */}
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-[2px] bg-[#1A1A1A] border border-[#333333] text-white text-[11px] font-mono">
              <span className="text-[#00CC66]">[WHATSAPP]</span>
              <span>{userPhone}</span>
            </div>

            {/* Clickable User Profile Element (navigates to Profile & Settings screen) */}
            <button
              onClick={() => setCurrentTab('profile')}
              className="flex items-center gap-2 p-1.5 px-3 rounded-[2px] bg-[#1A1A1A] border border-[#333333] hover:border-[#E50000] transition-all cursor-pointer group text-left"
              title="Click to view Client Profile & Operational Settings"
            >
              <div className="w-7 h-7 rounded-[2px] bg-[#0B0B0B] border border-[#333333] group-hover:border-[#E50000] flex items-center justify-center text-white font-mono font-bold text-xs">
                {userInitial}
              </div>
              <div className="text-left hidden md:block">
                <div className="text-xs font-bold text-white group-hover:text-[#E50000] leading-none uppercase">
                  {userName}
                </div>
                <div className="text-[10px] text-[#888888] mt-0.5 uppercase font-mono">{shopName}</div>
              </div>
            </button>
          </div>
        </header>

        {/* View Switcher / Page Body */}
        <main className="flex-1 overflow-y-auto">
          {currentTab === 'home' && (
            <HomeHero
              onGetStarted={() => {
                setCurrentTab('upload');
                setCurrentStep(1);
              }}
              onUseDemoData={() => {
                setDemoData(true);
                setCurrentTab('upload');
                setCurrentStep(1);
              }}
            />
          )}

          {currentTab === 'upload' && (
            <Step1Upload
              budget={budget}
              onChangeBudget={(b) => {
                setBudget(b);
                recomputePlan(b, horizonDays, products);
              }}
              horizonDays={horizonDays}
              onChangeHorizon={(h) => {
                setHorizonDays(h);
                recomputePlan(budget, h, products);
              }}
              demoData={demoData}
              onToggleDemoData={(val) => setDemoData(val)}
              onProcessFiles={handleProcessFiles}
              onImportCandidates={handleImportCandidates}
              isProcessing={isProcessing}
            />
          )}

          {currentTab === 'catalogue' && (
            <Step2Catalogue
              products={products}
              onUpdateProduct={handleUpdateProduct}
              onBack={() => {
                setCurrentTab('upload');
                setCurrentStep(1);
              }}
              onContinue={() => {
                setCurrentTab('plan');
                setCurrentStep(3);
                setMaxStepReached(prev => Math.max(prev, 3));
              }}
            />
          )}

          {currentTab === 'plan' && plan && (
            <Step3Plan
              plan={plan}
              onBack={() => {
                setCurrentTab('catalogue');
                setCurrentStep(2);
              }}
              onContinue={() => {
                setCurrentTab('orders');
                setCurrentStep(4);
                setMaxStepReached(prev => Math.max(prev, 4));
              }}
              onSimulateStockoutSub={handleSimulateStockoutSub}
            />
          )}

          {currentTab === 'orders' && plan && !isApproved && (
            <Step4Approve
              plan={plan}
              isApproved={isApproved}
              onToggleApproval={(val) => setIsApproved(val)}
              onSubmitApproval={handleSubmitApproval}
              onBack={() => {
                setCurrentTab('plan');
                setCurrentStep(3);
              }}
              isSubmitting={isSubmittingApproval}
              approvalError={approvalError}
            />
          )}

          {currentTab === 'orders' && isApproved && (
            <Step5Orders
              orders={orders}
              onBack={() => {
                setIsApproved(false);
                setCurrentStep(4);
              }}
              onGoToEvidence={() => {
                setCurrentTab('evidence');
                setCurrentStep(5);
              }}
            />
          )}

          {(currentTab === 'evidence' || currentTab === 'reports') && (
            <StepEvidence
              traceEvents={traceEvents}
              metrics={wapeMetrics}
              onBack={() => {
                if (orders.length > 0) {
                  setCurrentTab('orders');
                  setCurrentStep(5);
                } else {
                  setCurrentTab('plan');
                  setCurrentStep(3);
                }
              }}
            />
          )}

          {currentTab === 'whatsapp' && <WhatsAppSimulator />}

          {currentTab === 'codebase' && <CodebaseExplorer />}

          {currentTab === 'profile' && currentUser && (
            <ClientProfile
              user={currentUser}
              onUpdateUser={(updated) => setCurrentUser(updated)}
              onBackToDashboard={() => setCurrentTab('home')}
            />
          )}
        </main>

        {/* Step-by-Step Stepper at Bottom (1. Upload & Settings -> 5. Results & Evidence) */}
        {currentTab !== 'whatsapp' && currentTab !== 'codebase' && currentTab !== 'home' && currentTab !== 'profile' && (
          <BottomStepper
            currentStep={currentStep}
            onSelectStep={handleSelectStep}
            maxStepReached={maxStepReached}
          />
        )}
      </div>
    </div>
  );
}
