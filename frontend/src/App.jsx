import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Send, FileText, Download, MessageSquare, ChevronRight, Zap, Database, Globe, Layers, Cpu, Sparkles, BookOpen, Share2, Activity, History, Settings, User, LogOut, Shield } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import confetti from 'canvas-confetti';
import { useResearch } from './hooks/useResearch';
import ResearchMap from './components/ResearchMap';
import Auth from './components/Auth';
import Landing from './components/Landing';
import ResearchHistory from './components/ResearchHistory';

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


const SystemModal = ({ status, onOptimize, isOptimizing, onClose }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-950/80 backdrop-blur-xl"
  >
    <motion.div
      initial={{ scale: 0.9, y: 20 }}
      animate={{ scale: 1, y: 0 }}
      className="glass-card max-w-lg w-full p-8 relative overflow-hidden"
    >
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-accent" />

      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-primary/10 text-primary">
            <Cpu size={24} />
          </div>
          <h2 className="text-2xl font-black font-outfit tracking-tight">Neural Optimization</h2>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg transition-colors text-slate-500 hover:text-white">
          <ChevronRight className="rotate-90" size={20} />
        </button>
      </div>

      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Memory Capacity</div>
            <div className="text-xl font-bold">{status?.system_info?.ram_gb || 0} GB RAM</div>
          </div>
          <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Processor Cores</div>
            <div className="text-xl font-bold">{status?.system_info?.cores || 0} Logic Cores</div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-primary/5 border border-primary/20">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-primary">Current Model</div>
            <div className={`px-2 py-0.5 rounded text-[9px] font-bold ${status?.available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
              {status?.available ? 'ACTIVE' : 'OFFLINE'}
            </div>
          </div>
          <div className="text-lg font-bold font-mono text-slate-300 mb-1">{status?.model || 'None Connected'}</div>
          <div className="text-[11px] text-slate-500">Ollama API: {status?.base_url}</div>
        </div>

        <div className="p-6 rounded-2xl bg-secondary/5 border border-secondary/20 relative group">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">Yukti Recommendation</div>
          <div className="text-lg font-bold text-white mb-2">{status?.recommended}</div>
          <p className="text-[11px] text-slate-400 leading-relaxed">Based on your hardware, we recommend this model for the best balance between synthesis depth and processing speed.</p>
        </div>
      </div>

      <button
        disabled={isOptimizing}
        onClick={onOptimize}
        className="w-full mt-10 py-4 rounded-xl bg-white text-slate-900 font-bold flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
      >
        {isOptimizing ? (
          <>
            <Activity className="animate-spin" size={20} />
            <span>OPTIMIZING NEURAL PATHS...</span>
          </>
        ) : (
          <>
            <Zap size={20} className="fill-current" />
            <span>IGNITE SYSTEM OPTIMIZATION</span>
          </>
        )}
      </button>
    </motion.div>
  </motion.div>
);

const App = () => {
  const [view, setView] = useState('landing');
  const [user, setUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [sessions, setSessions] = useState({});
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const { connect, sendMessage, status, agents, report, plan, messages, sessionId } = useResearch();
  const [activeTab, setActiveTab] = useState('pipeline');
  const chatEndRef = useRef(null);
  const [onboardingName, setOnboardingName] = useState('');
  const [systemStatus, setSystemStatus] = useState(null);
  const [showSystemModal, setShowSystemModal] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const fetchSystemStatus = async () => {
    try {
      const resp = await fetch('http://localhost:8000/api/status');
      const data = await resp.json();
      setSystemStatus(data.llm);
    } catch (e) {
      console.error("System status fetch error", e);
    }
  };

  const runSystemOptimization = async () => {
    setIsOptimizing(true);
    try {
      const resp = await fetch('http://localhost:8000/api/system/setup', { method: 'POST' });
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
      const resp = await fetch('http://localhost:8000/api/sessions');
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
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
      setActiveTab('report');
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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!user) {
      setView('auth');
      return;
    }
    if (!query.trim()) return;
    connect(query);
  };

  const handleExport = (format) => {
    window.open(`http://localhost:8000/api/export/${sessionId}/${format}`, '_blank');
  };

  const loadSession = async (sid) => {
    try {
      const resp = await fetch(`http://localhost:8000/api/sessions/${sid}`);
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

            <form onSubmit={handleSubmit} className="relative w-full max-w-2xl group">
              <div className="absolute -inset-2 bg-gradient-to-r from-primary via-secondary to-accent rounded-3xl blur-2xl opacity-10 group-hover:opacity-30 transition duration-1000 group-hover:duration-200" />
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
                  <span className="font-black text-lg tracking-tight relative z-10">{user ? 'IGNITE' : 'LOGIN TO SEARCH'}</span>
                </button>
              </div>
            </form>

            <div className="mt-16">
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
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, filter: 'blur(20px)' }}
            animate={{ opacity: 1, filter: 'blur(0px)' }}
            className="h-screen flex flex-col p-4 md:p-6 lg:p-8 gap-6 overflow-hidden"
          >
            {/* Top Bar Navigation */}
            <div className="glass-card px-8 py-4 flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-3 group cursor-pointer" onClick={() => window.location.reload()}>
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center font-black text-xl shadow-lg shadow-primary/20 text-white">Y</div>
                  <GradientText
                    colors={["#6366f1", "#a855f7", "#22d3ee", "#6366f1"]}
                    animationSpeed={8}
                    showBorder={false}
                    className="font-outfit font-black text-2xl tracking-tighter"
                  >
                    YUKTI.AI
                  </GradientText>
                </div>

                <div className="h-6 w-[1.5px] bg-white/10 mx-2" />

                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${status === 'completed' ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-primary animate-ping'}`} />
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">{status}</span>
                </div>
              </div>

              <div className="flex-1 max-w-md mx-8">
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: status === 'completed' ? '100%' :
                        status === 'synthesising' ? '80%' :
                          status === 'researching' ? '50%' :
                            status === 'planning' ? '20%' : '5%'
                    }}
                    className="h-full bg-gradient-to-r from-primary to-accent"
                  />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <button
                  onClick={() => setShowSystemModal(true)}
                  className="p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-all text-slate-400 hover:text-white"
                >
                  <Cpu size={18} className={systemStatus?.available ? 'text-emerald-400' : ''} />
                </button>
                {report && (
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleExport('pdf')} className="p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 transition-colors group">
                      <Download size={18} />
                    </button>
                    <button onClick={() => handleExport('latex')} className="flex items-center gap-3 px-6 py-3 bg-white text-slate-900 rounded-xl font-bold text-sm hover:scale-105 active:scale-95 transition-all shadow-xl shadow-white/10">
                      <Share2 size={16} /> Export IEEE
                    </button>
                  </div>
                )}
                <button className="p-3 rounded-xl bg-white/5 border border-white/5 text-slate-400 hover:text-white transition-colors">
                  <History size={18} />
                </button>
              </div>
            </div>

            {/* Main Content Grid */}
            <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
              {/* Left Sidebar - History Vault */}
              <div className="col-span-3 flex flex-col gap-6 overflow-hidden">
                <div className="glass-card p-6 flex flex-col gap-6 flex-1 overflow-hidden">
                  <ResearchHistory
                    sessions={sessions}
                    onSelect={loadSession}
                    activeSessionId={sessionId}
                  />
                </div>
              </div>

              {/* Center Viewport */}
              <div className="col-span-9 flex flex-col gap-6 overflow-hidden">
                <div className="glass-card flex-1 overflow-hidden flex flex-col relative">
                  <AnimatePresence mode="wait">
                    {activeTab === 'pipeline' && (
                      <motion.div
                        key="pipeline-view"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.05 }}
                        className="flex-1 flex flex-col p-12 overflow-y-auto items-center"
                      >
                        <div className="text-center mb-16">
                          <h1 className="text-5xl font-black font-outfit mb-4">Autonomous Path</h1>
                          <p className="text-slate-400 font-light text-lg">Visualizing the logic flow of the Yukti multi-agent cluster.</p>
                        </div>

                        <div className="w-full h-[400px]">
                          <ResearchMap agents={agents} />
                        </div>

                        {plan && (
                          <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="w-full max-w-5xl mt-20 grid grid-cols-2 gap-6"
                          >
                            <div className="p-8 rounded-[2rem] bg-white/5 border border-white/10 relative overflow-hidden group">
                              <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-primary mb-6">Research Landscape</h4>
                              <p className="text-lg font-outfit font-light leading-relaxed text-slate-300 italic">"{plan.abstract_scope}"</p>
                            </div>
                            <div className="p-8 rounded-[2rem] bg-primary/5 border border-primary/20">
                              <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-primary mb-6">Key Directives</h4>
                              <div className="space-y-4">
                                {plan.sub_questions.slice(0, 3).map((q, i) => (
                                  <div key={i} className="flex gap-4">
                                    <span className="text-primary font-bold text-xs">{i + 1}</span>
                                    <span className="text-[11px] leading-tight text-slate-400">{q}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </motion.div>
                    )}

                    {activeTab === 'report' && report && (
                      <motion.div
                        key="report-view"
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -40 }}
                        className="flex-1 overflow-y-auto p-12 lg:p-20"
                      >
                        <div className="max-w-4xl mx-auto">
                          <center className="mb-24">
                            <div className="inline-block px-4 py-1 rounded-full bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest border border-primary/10 mb-8">Generated by Yukti Engine v4.0</div>
                            <h1 className="text-7xl font-black font-outfit tracking-tighter leading-[0.9] mb-12">{report.title}</h1>
                            <div className="flex items-center justify-center gap-12 text-slate-500 font-bold uppercase tracking-widest text-[10px]">
                              <div className="flex flex-col items-center gap-2"><span className="text-white text-xl">{report.word_count}</span><span>Word Count</span></div>
                              <div className="h-8 w-[1px] bg-white/10" />
                              <div className="flex flex-col items-center gap-2"><span className="text-white text-xl">{report.statistics?.total_sources || 0}</span><span>Sources</span></div>
                              <div className="h-8 w-[1px] bg-white/10" />
                              <div className="flex flex-col items-center gap-2"><span className="text-white text-xl">{report.statistics?.verified_dois || 0}</span><span>Verified DOIs</span></div>
                            </div>
                          </center>

                          <div className="prose prose-invert prose-2xl prose-slate max-w-none prose-headings:font-outfit prose-headings:font-black prose-p:leading-relaxed prose-p:font-light prose-p:text-slate-300 prose-strong:text-white prose-a:text-primary pb-32">
                            <ReactMarkdown>{report.report}</ReactMarkdown>
                          </div>
                        </div>
                      </motion.div>
                    )}

                    {activeTab === 'chat' && (
                      <motion.div
                        key="chat-view"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex-1 flex flex-col relative"
                      >
                        <div className="flex-1 overflow-y-auto px-12 py-12 flex flex-col gap-10 pb-40">
                          {messages.map((m, i) => (
                            <motion.div
                              initial={{ opacity: 0, y: 20 }}
                              animate={{ opacity: 1, y: 0 }}
                              key={i}
                              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                              <div className={`max-w-[70%] p-8 rounded-[2.5rem] shadow-3xl text-lg leading-relaxed ${m.role === 'user'
                                ? 'bg-gradient-to-br from-primary to-secondary text-white rounded-tr-none'
                                : 'glass rounded-tl-none border-white/5 bg-white/[0.03]'
                                }`}>
                                {m.content}
                              </div>
                            </motion.div>
                          ))}
                          <div ref={chatEndRef} />
                        </div>

                        <div className="absolute bottom-10 left-10 right-10 flex flex-col items-center">
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              const msg = e.target.msg.value;
                              if (!msg) return;
                              sendMessage(msg);
                              e.target.reset();
                            }}
                            className="w-full max-w-4xl relative group"
                          >
                            <div className="absolute -inset-2 bg-gradient-to-r from-primary via-secondary to-accent rounded-[2.5rem] blur opacity-10 group-focus-within:opacity-40 transition duration-700" />
                            <div className="relative">
                              <input
                                name="msg"
                                placeholder="Query the synthesis engine for specific insights..."
                                className="w-full bg-slate-900/90 backdrop-blur-3xl border border-white/10 rounded-[2.2rem] py-8 pl-10 pr-28 text-xl outline-none focus:border-primary/50 transition-all font-light"
                              />
                              <button className="absolute right-4 top-4 bottom-4 px-8 rounded-2xl bg-white text-slate-900 font-bold hover:scale-105 active:scale-95 transition-all shadow-xl">
                                <Send size={24} />
                              </button>
                            </div>
                          </form>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div className="absolute bottom-6 left-12 flex items-center gap-6">
                    {['pipeline', 'report', 'chat'].map(t => (
                      <button
                        key={t}
                        disabled={(t === 'report' && !report) || (t === 'chat' && status !== 'completed')}
                        onClick={() => setActiveTab(t)}
                        className={`text-[10px] font-black uppercase tracking-[0.2em] transition-all border-b-2 py-1 ${activeTab === t ? 'text-primary border-primary' : 'text-slate-600 border-transparent hover:text-slate-400'} ${((t === 'report' && !report) || (t === 'chat' && status !== 'completed')) ? 'opacity-20 cursor-not-allowed' : ''}`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
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
