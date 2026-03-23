import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Zap, Cpu, Sparkles, LogOut, Shield, Github, Tag, BookOpen, ChevronRight, Activity, HardDrive, Server, Database, TrendingUp } from 'lucide-react';
import confetti from 'canvas-confetti';
import { useResearch } from './hooks/useResearch';
import Auth from './components/Auth';
import Landing from './components/Landing';
import ResearchWorkspace from './components/ResearchWorkspace';
import ZoteroCitationLibrary from './components/ZoteroCitationLibrary';

import DarkVeil from './components/DarkVeil';
import PixelSnow from './components/PixelSnow';
import GradientText from './components/GradientText';
import Stepper, { Step } from './components/Stepper';

const Background = () => (
  <div className="fixed inset-0 -z-30 overflow-hidden bg-slate-950">
    {/* Cinematic Shader Background */}
    <div className="absolute inset-0 opacity-40">
      <DarkVeil hueShift={220} warpAmount={0.3} speed={0.2} />
    </div>

    {/* Atmospheric Depth Layer */}
    <div className="absolute inset-0 opacity-20 pointer-events-none">
      <PixelSnow density={0.4} speed={1.2} />
    </div>

    {/* Vignette & Gradients Mask */}
    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/20 to-background" />
    <div className="absolute inset-0 shadow-[inset_0_0_150px_rgba(0,0,0,0.8)]" />

    {/* Noise Texture */}
    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.1] mix-blend-overlay pointer-events-none" />
  </div>
);


const SystemModal = ({ status, onOptimize, isOptimizing, onClose }) => {
  const ram = status?.system_info?.ram_gb || 0;
  const availRam = status?.system_info?.available_ram_gb ?? (ram * 0.5);
  const usedRam = Math.max(0, ram - availRam);
  const ramPct = ram > 0 ? Math.min(100, Math.round((usedRam / ram) * 100)) : 0;
  const cores = status?.system_info?.cores || 0;
  const diskFree = status?.system_info?.disk_free_gb ?? null;
  const hasGpu = status?.system_info?.has_gpu ?? false;
  const availableModels = status?.models || [];

  const tier =
    ram >= 48 ? { label: 'APEX',     color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/30' } :
    ram >= 24 ? { label: 'ELITE',    color: 'text-cyan-400',   bg: 'bg-cyan-500/10',   border: 'border-cyan-500/30'   } :
    ram >= 12 ? { label: 'ADVANCED', color: 'text-emerald-400',bg: 'bg-emerald-500/10',border: 'border-emerald-500/30'} :
                { label: 'STANDARD', color: 'text-slate-400',  bg: 'bg-slate-500/10',  border: 'border-slate-500/30'  };

  const techniques = [
    { name: 'INT4 Neural Quantization',   active: ram >= 8,    desc: '4× memory compression via quantization'     },
    { name: 'Parallel Core Processing',   active: cores >= 8,  desc: `Inference spread across ${cores} CPU cores` },
    { name: 'KV-Cache Optimization',      active: ram >= 16,   desc: 'Key-value attention caching in RAM'         },
    { name: 'Hardware-Adaptive Scaling',  active: true,        desc: 'Auto-tunes context window to hardware'      },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-950/80 backdrop-blur-xl"
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        className="glass-card max-w-xl w-full relative overflow-hidden"
      >
        {/* Gradient accent bar */}
        <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-primary via-secondary to-accent" />

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
              <Cpu size={20} />
            </div>
            <div>
              <h2 className="text-xl font-black font-outfit tracking-tight leading-none">Neural Optimization</h2>
              <p className="text-[10px] text-slate-500 mt-0.5">Hardware Intelligence Engine</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border ${tier.bg} ${tier.color} ${tier.border}`}>
              {tier.label} TIER
            </span>
            <button onClick={onClose} className="p-1.5 hover:bg-white/5 rounded-lg transition-colors text-slate-500 hover:text-white">
              <ChevronRight className="rotate-90" size={18} />
            </button>
          </div>
        </div>

        {/* ── Scrollable Body ── */}
        <div className="px-6 pb-6 space-y-4 max-h-[72vh] overflow-y-auto">

          {/* Hardware metrics */}
          <div className="grid grid-cols-3 gap-3">

            {/* RAM card (spans 2 cols) */}
            <div className="col-span-2 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-500 flex items-center gap-1">
                  <HardDrive size={10} /> Memory Capacity
                </span>
                <span className="text-[9px] font-bold text-slate-500">{ramPct}% IN USE</span>
              </div>
              <div className="text-2xl font-bold leading-none">
                {ram.toFixed(0)}
                <span className="text-sm font-normal text-slate-400 ml-1">GB RAM</span>
              </div>
              {/* Animated RAM bar */}
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${ramPct}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className={`h-full rounded-full ${ramPct > 80 ? 'bg-red-500' : ramPct > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                />
              </div>
              <div className="text-[10px] text-slate-500">
                {availRam.toFixed(1)} GB free · {usedRam.toFixed(1)} GB used
              </div>
            </div>

            {/* CPU + GPU stacked */}
            <div className="flex flex-col gap-3">
              <div className="flex-1 p-3 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
                <div className="text-[9px] font-black uppercase tracking-widest text-slate-500 mb-1">Processor</div>
                <div className="text-xl font-bold leading-none">{cores}</div>
                <div className="text-[10px] text-slate-500">Logic Cores</div>
              </div>
              <div className={`flex-1 p-3 rounded-2xl border ${hasGpu ? 'bg-violet-500/5 border-violet-500/20' : 'bg-white/[0.03] border-white/[0.06]'}`}>
                <div className="text-[9px] font-black uppercase tracking-widest text-slate-500 mb-1">GPU</div>
                <div className={`text-[10px] font-bold ${hasGpu ? 'text-violet-400' : 'text-slate-500'}`}>
                  {hasGpu ? '● DETECTED' : '○ CPU MODE'}
                </div>
              </div>
            </div>
          </div>

          {/* Current Model */}
          <div className="p-4 rounded-2xl bg-primary/5 border border-primary/20 relative overflow-hidden">
            {status?.available && (
              <motion.div
                animate={{ opacity: [0.3, 0.8, 0.3] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="absolute top-3 right-3 h-2 w-2 rounded-full bg-emerald-400"
              />
            )}
            <div className="flex items-center gap-2 mb-2">
              <Server size={11} className="text-primary" />
              <div className="text-[9px] font-black uppercase tracking-widest text-primary">Current Model</div>
              <div className={`px-1.5 py-0.5 rounded text-[8px] font-black ${status?.available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                {status?.available ? 'ACTIVE' : 'OFFLINE'}
              </div>
            </div>
            <div className="text-base font-bold font-mono text-white">{status?.model || 'None Connected'}</div>
            <div className="text-[10px] text-slate-500 mt-1">Ollama API · {status?.base_url}</div>
          </div>

          {/* Installed Models chips */}
          {availableModels.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5">
                <Database size={10} className="text-slate-500" />
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">
                  Installed Models <span className="text-slate-600 normal-case tracking-normal font-normal">({availableModels.length})</span>
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {availableModels.map(m => (
                  <span
                    key={m}
                    className={`px-2 py-0.5 rounded-lg text-[10px] font-mono font-medium border transition-colors ${
                      m === status?.model
                        ? 'bg-primary/10 text-primary border-primary/30'
                        : 'bg-white/5 text-slate-400 border-white/10'
                    }`}
                  >
                    {m}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Yukti Recommendation */}
          <div className="p-4 rounded-2xl bg-secondary/5 border border-secondary/20">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <TrendingUp size={11} className="text-secondary" />
                <span className="text-[9px] font-black uppercase tracking-widest text-secondary">Yukti Recommendation</span>
              </div>
              <Sparkles size={12} className="text-secondary" />
            </div>
            <div className="text-base font-bold font-mono text-white mb-1">{status?.recommended || '—'}</div>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              Based on your hardware, we recommend this model for the best balance between synthesis depth and processing speed.
            </p>
          </div>

          {/* Optimization Techniques */}
          <div className="space-y-2">
            <div className="text-[9px] font-black uppercase tracking-widest text-slate-500">Optimization Techniques</div>
            <div className="grid grid-cols-2 gap-2">
              {techniques.map(t => (
                <div
                  key={t.name}
                  className={`p-3 rounded-xl border transition-all ${
                    t.active
                      ? 'bg-emerald-500/5 border-emerald-500/20'
                      : 'bg-white/[0.02] border-white/5'
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <div className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${t.active ? 'bg-emerald-400' : 'bg-slate-700'}`} />
                    <span className={`text-[8px] font-black uppercase tracking-wide ${t.active ? 'text-emerald-400' : 'text-slate-600'}`}>
                      {t.active ? 'ENABLED' : 'INACTIVE'}
                    </span>
                  </div>
                  <div className={`text-[10px] font-bold mb-0.5 ${t.active ? 'text-white' : 'text-slate-600'}`}>{t.name}</div>
                  <div className="text-[9px] text-slate-600 leading-tight">{t.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Disk Space */}
          {diskFree !== null && (
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <HardDrive size={11} className="text-slate-500" />
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">Free Disk Space</span>
              </div>
              <span className="text-sm font-bold text-slate-300">{Number(diskFree).toFixed(1)} GB</span>
            </div>
          )}

          {/* Action Button */}
          <button
            disabled={isOptimizing}
            onClick={onOptimize}
            className="w-full py-4 rounded-xl bg-gradient-to-r from-primary via-secondary to-accent text-white font-black text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isOptimizing ? (
              <>
                <Activity className="animate-spin" size={18} />
                <span>OPTIMIZING NEURAL PATHS...</span>
              </>
            ) : (
              <>
                <Zap size={18} className="fill-current" />
                <span>IGNITE SYSTEM OPTIMIZATION</span>
              </>
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

const App = () => {
  const [view, setView] = useState('landing');
  const [user, setUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [sessions, setSessions] = useState({});
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  // GitHub project research mode
  const [inputMode, setInputMode] = useState('topic');  // 'topic' | 'github'
  const [githubUrl, setGithubUrl] = useState('');
  const [githubTitle, setGithubTitle] = useState('');
  const [isAnalyzingGithub, setIsAnalyzingGithub] = useState(false);
  const [githubError, setGithubError] = useState(null);
  const { connect, sendMessage, status, agents, logs, report, plan, sections, setSections, messages, sessionId } = useResearch();
  const [onboardingName, setOnboardingName] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);
  const [showSystemModal, setShowSystemModal] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const fetchSystemStatus = async () => {
    try {
      const resp = await fetch('/api/status');
      const data = await resp.json();
      setSystemStatus(data.llm);
    } catch (e) {
      console.error("System status fetch error", e);
    }
  };

  const runSystemOptimization = async () => {
    setIsOptimizing(true);
    try {
      const resp = await fetch('/api/system/setup', { method: 'POST' });
      const data = await resp.json();
      setSystemStatus(data.status);
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#10b981', '#34d399', '#6ee7b7']
      });
    } catch (e) {
      console.error("Optimization error", e);
    } finally {
      setIsOptimizing(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    try {
      const resp = await fetch('/api/sessions');
      const data = await resp.json();
      setSessions(data);
    } catch (e) {
      console.error("Fetch sessions error", e);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (status !== 'idle') setIsSearching(true);
  }, [status]);

  useEffect(() => {
    if (status === 'completed') {
      confetti({
        particleCount: 200,
        spread: 90,
        origin: { y: 0.6 },
        colors: ['#6366f1', '#a855f7', '#22d3ee']
      });
      fetchSessions();
    }
  }, [status]);

  // Logout Observer
  useEffect(() => {
    if (!user && view === 'app') {
      setView('landing');
      setIsSearching(false);
    }
  }, [user, view]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user) { setView('auth'); return; }

    if (inputMode === 'github') {
      const url = githubUrl.trim();
      if (!url) return;
      setIsAnalyzingGithub(true);
      setGithubError(null);
      try {
        const res = await fetch('/api/github/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repo_url: url, existing_title: githubTitle.trim() || null }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'GitHub analysis failed');
        // Use provided title > AI-generated title > URL slug
        const researchQuery =
          githubTitle.trim() ||
          data.data?.title ||
          url.replace('https://github.com/', '').replace(/\.git\/?$/, '');
        setQuery(researchQuery);
        connect(researchQuery);
      } catch (err) {
        setGithubError(String(err));
      } finally {
        setIsAnalyzingGithub(false);
      }
    } else {
      if (!query.trim()) return;
      connect(query);
    }
  };

  const loadSession = async (sid) => {
    try {
      const resp = await fetch(`/api/sessions/${sid}`);
      const data = await resp.json();
      alert(`Loading Session: ${data.query}\nStatus: ${data.status}`);
    } catch (e) { }
  };

  const startAppFlow = () => {
    if (!user) {
      setView('auth');
    } else {
      setView('app');
    }
  };

  if (view === 'auth') return (
    <>
      <Background />
      <Auth onLogin={(u) => {
        setUser(u);
        setShowOnboarding(true);
        setView('app');
      }} onBack={() => setView('landing')} />
    </>
  );

  if (view === 'landing') return (
    <>
      <Background />
      <Landing onStart={startAppFlow} onAuth={() => setView('auth')} />
    </>
  );

  if (view === 'zotero') return (
    <div className="relative min-h-screen">
      <button
        onClick={() => setView('app')}
        className="fixed top-4 left-4 z-50 glass px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-white/10 transition-all border border-white/5"
      >
        Back to App
      </button>
      <ZoteroCitationLibrary />
    </div>
  );

  if (showOnboarding) return (
    <div className="min-h-screen flex items-center justify-center p-6 relative">
      <Background />
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-4xl"
      >
        <Stepper
          initialStep={1}
          onFinalStepCompleted={() => setShowOnboarding(false)}
          backButtonText="PREVIOUS"
          nextButtonText="CONTINUE"
        >
          <Step>
            <div className="p-8">
              <div className="w-20 h-20 rounded-3xl bg-primary/20 flex items-center justify-center text-primary mx-auto mb-8 shadow-2xl shadow-primary/20">
                <Sparkles size={40} />
              </div>
              <h2 className="text-4xl font-black mb-4 tracking-tighter">Welcome to the <br />Yukti Platform.</h2>
              <p className="text-slate-400 max-w-md mx-auto">Greetings, Scholar. Let's initialize your research interface and walks through our autonomous orchestration.</p>
            </div>
          </Step>
          <Step>
            <div className="p-8">
              <img style={{ height: '240px', width: '100%', objectFit: 'cover', borderRadius: '2rem' }} src="https://images.unsplash.com/photo-1639322537228-f710d846310a?auto=format&fit=crop&q=80&w=1000" />
              <h2 className="mt-8 text-3xl font-black tracking-tight">Conceptualize</h2>
              <p className="text-slate-400 mt-2">Enter any complex query. Our <strong>PlannerAgent</strong> will decompose it into a logical ontogical tree across multiple academic clusters.</p>
            </div>
          </Step>
          <Step>
            <div className="p-8">
              <div className="glass-card p-10 bg-emerald-500/5 border-emerald-500/20 mb-8">
                <Shield className="text-emerald-400 mx-auto mb-6" size={48} />
                <h2 className="text-emerald-400 text-3xl font-black tracking-tight">Hallucination Shield</h2>
                <p className="text-slate-400 mt-4 leading-relaxed">Unlike standard LLMs, Yukti verifies every single claim against live bibliographic databases (ArXiv, PubMed, Semantic Scholar).</p>
              </div>
            </div>
          </Step>
          <Step>
            <div className="p-8">
              <h2 className="text-4xl font-black mb-6 tracking-tighter">Final Initialization</h2>
              <p className="text-slate-400 mb-10">We are ready to ignite. What should our first research directive be?</p>
              <div className="max-w-md mx-auto">
                <input
                  type="text"
                  value={onboardingName}
                  onChange={(e) => setOnboardingName(e.target.value)}
                  placeholder="Input research domain..."
                  className="w-full bg-white/5 border border-white/10 rounded-2xl p-6 text-xl text-white outline-none focus:border-primary transition-all"
                />
              </div>
            </div>
          </Step>
        </Stepper>
      </motion.div>
    </div>
  );

  return (
    <div className="min-h-screen font-inter text-slate-100 selection:bg-primary/40 overflow-x-hidden">
      <Background />

      <AnimatePresence mode="wait">
        {!isSearching ? (
          <motion.div
            key="hero"
            initial={{ opacity: 0, scale: 1.1 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95, filter: 'blur(20px)' }}
            transition={{ duration: 0.8, ease: "circOut" }}
            className="min-h-screen flex flex-col items-center justify-center p-6 text-center z-10"
          >
            <div className="absolute top-10 right-10 flex items-center gap-4">
              {user && (
                <button
                  onClick={() => setView('zotero')}
                  className="glass px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-white/10 transition-all border border-white/5"
                >
                  Zotero Library
                </button>
              )}
              <button
                onClick={() => setShowSystemModal(true)}
                className="glass p-3 rounded-xl hover:bg-white/10 transition-all border border-white/5 relative group"
              >
                <Cpu size={18} className={systemStatus?.available ? 'text-emerald-400' : 'text-slate-500'} />
                {systemStatus?.available && (
                  <span className="absolute top-2 right-2 flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
                  </span>
                )}
              </button>
              {user ? (
                <div className="glass px-4 py-2 rounded-xl flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                    {user.user.name[0]}
                  </div>
                  <span className="text-xs font-bold">{user.user.name}</span>
                  <button onClick={() => setUser(null)} className="p-2 hover:text-red-400 transition-colors"><LogOut size={16} /></button>
                </div>
              ) : (
                <button onClick={() => setView('auth')} className="glass px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-white/10 transition-all border border-white/5">Sign In</button>
              )}
            </div>

            <GradientText
              colors={["#6366f1", "#a855f7", "#22d3ee", "#6366f1"]}
              animationSpeed={10}
              className="text-7xl md:text-9xl font-black mb-10 tracking-tighter font-outfit leading-[0.85] drop-shadow-[0_0_30px_rgba(99,102,241,0.2)]"
            >
              YUKTI.AI
            </GradientText>

            <p className="text-lg md:text-xl text-slate-400 mb-12 max-w-2xl font-light tracking-wide leading-relaxed font-outfit">
              The world's first <span className="text-white font-medium">autonomous research machine</span>. Deeply logical, perpetually verified.
            </p>

            {/* Mode toggle */}
            <div className="flex gap-1 p-1 rounded-xl bg-slate-900/60 border border-white/5 backdrop-blur mb-4">
              <button
                type="button"
                onClick={() => { setInputMode('topic'); setGithubError(null); }}
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${inputMode === 'topic' ? 'bg-primary/20 text-primary border border-primary/30' : 'text-slate-500 hover:text-slate-300'}`}
              >
                <BookOpen size={14} /> Topic Research
              </button>
              <button
                type="button"
                onClick={() => { setInputMode('github'); setGithubError(null); }}
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${inputMode === 'github' ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30' : 'text-slate-500 hover:text-slate-300'}`}
              >
                <Github size={14} /> GitHub Project
              </button>
            </div>

            <form onSubmit={handleSubmit} className="relative w-full max-w-2xl group">
              <div className="absolute -inset-2 bg-gradient-to-r from-primary via-secondary to-accent rounded-3xl blur-2xl opacity-10 group-hover:opacity-30 transition duration-1000 group-hover:duration-200" />

              {inputMode === 'topic' ? (
                <div className="relative flex items-center bg-slate-900/40 backdrop-blur-3xl border border-white/10 rounded-2xl p-2 shadow-3xl">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={user ? "Ask Yukti to illuminate any topic..." : "Login to use the AI Research Agent..."}
                    className="flex-1 bg-transparent py-4 px-6 text-xl outline-none font-light placeholder:text-slate-600"
                  />
                  <button
                    type="submit"
                    className="px-8 py-4 rounded-xl bg-gradient-to-r from-primary to-secondary text-white flex items-center gap-2 hover:scale-[1.02] active:scale-95 transition-all shadow-2xl shadow-primary/40 group/btn overflow-hidden relative"
                  >
                    <div className="absolute inset-0 bg-white/10 translate-y-full group-hover/btn:translate-y-0 transition-transform" />
                    {user ? <Search size={20} className="relative z-10" /> : <Shield size={20} className="relative z-10" />}
                    <span className="font-black text-lg tracking-tight relative z-10">{user ? 'IGNITE' : 'LOGIN'}</span>
                  </button>
                </div>
              ) : (
                <div className="relative flex flex-col gap-2 bg-slate-900/40 backdrop-blur-3xl border border-violet-500/20 rounded-2xl p-4 shadow-3xl">
                  <div className="flex items-center gap-2 px-2 py-1">
                    <Github size={16} className="text-violet-400 flex-shrink-0" />
                    <input
                      type="url"
                      value={githubUrl}
                      onChange={(e) => { setGithubUrl(e.target.value); setGithubError(null); }}
                      placeholder="https://github.com/owner/repository"
                      required
                      className="flex-1 bg-transparent py-3 text-lg outline-none font-light placeholder:text-slate-600 text-white"
                    />
                  </div>
                  <div className="h-px bg-white/5" />
                  <div className="flex items-center gap-2 px-2 py-1">
                    <Tag size={14} className="text-slate-500 flex-shrink-0" />
                    <input
                      type="text"
                      value={githubTitle}
                      onChange={(e) => setGithubTitle(e.target.value)}
                      placeholder="Paper title (optional — will be auto-generated)"
                      className="flex-1 bg-transparent py-2 text-sm outline-none font-light placeholder:text-slate-600 text-slate-300"
                    />
                  </div>
                  {githubError && (
                    <p className="text-xs text-red-400 px-2 pb-1">{githubError}</p>
                  )}
                  <button
                    type="submit"
                    disabled={isAnalyzingGithub || !githubUrl.trim() || !user}
                    className="mt-1 px-8 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-secondary text-white flex items-center justify-center gap-2 hover:scale-[1.01] active:scale-95 transition-all shadow-2xl shadow-violet-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isAnalyzingGithub ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span className="font-black tracking-tight">ANALYSING REPO…</span>
                      </>
                    ) : (
                      <>
                        {user ? <Github size={18} /> : <Shield size={18} />}
                        <span className="font-black tracking-tight">{user ? 'ANALYSE & RESEARCH' : 'LOGIN TO CONTINUE'}</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </form>

            <div className="mt-12">
              {inputMode === 'topic' ? (
                <div className="flex flex-wrap justify-center gap-3 opacity-40 hover:opacity-100 transition-opacity duration-500">
                  {['Fusion Diagnostics', 'Quantum Ethics', 'Post-Scarcity Economics', 'Bio-Neural Interfaces'].map(topic => (
                    <button
                      key={topic}
                      onClick={() => setQuery(topic)}
                      className="px-5 py-2 rounded-full border border-white/5 bg-white/[0.02] text-[10px] font-medium hover:border-primary/50 hover:bg-primary/10 hover:text-white transition-all transform hover:-translate-y-1"
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex flex-wrap justify-center gap-3 opacity-40 hover:opacity-100 transition-opacity duration-500">
                  {[
                    { label: 'huggingface/transformers', url: 'https://github.com/huggingface/transformers' },
                    { label: 'pytorch/pytorch', url: 'https://github.com/pytorch/pytorch' },
                    { label: 'openai/whisper', url: 'https://github.com/openai/whisper' },
                  ].map(ex => (
                    <button
                      key={ex.label}
                      onClick={() => setGithubUrl(ex.url)}
                      className="px-5 py-2 rounded-full border border-white/5 bg-white/[0.02] text-[10px] font-medium hover:border-violet-500/50 hover:bg-violet-500/10 hover:text-white transition-all transform hover:-translate-y-1"
                    >
                      <Github size={10} className="inline mr-1" />{ex.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="workspace"
            initial={{ opacity: 0, filter: 'blur(10px)' }}
            animate={{ opacity: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.4 }}
          >
            <ResearchWorkspace
              query={query}
              sections={sections}
              setSections={setSections}
              plan={plan}
              status={status}
              sessionId={sessionId}
              agents={agents}
              logs={logs}
              report={report}
              messages={messages}
              sendMessage={sendMessage}
              onNewResearch={() => { setIsSearching(false); setSections([]); }}
              systemStatus={systemStatus}
              onOpenSystemModal={() => setShowSystemModal(true)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showSystemModal && (
          <SystemModal
            status={systemStatus}
            isOptimizing={isOptimizing}
            onOptimize={runSystemOptimization}
            onClose={() => setShowSystemModal(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;
