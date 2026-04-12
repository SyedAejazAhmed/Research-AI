import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowRight,
  BookOpen,
  FolderOpen,
  Github,
  Leaf,
  LogOut,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useResearch } from './hooks/useResearch';
import ResearchWorkspace from './components/ResearchWorkspace';

const guideSteps = [
  {
    step: '2',
    title: 'Conceptualize',
    body: 'Enter any complex query. Our PlannerAgent will decompose it into a logical ontogical tree across multiple academic clusters.',
  },
  {
    step: '3',
    title: 'Hallucination Shield',
    body: 'Unlike standard LLMs, Yukti verifies every single claim against live bibliographic databases (ArXiv, PubMed, Semantic Scholar).',
  },
  {
    step: '4',
    title: 'Final Initialization',
    body: 'We are ready to ignite. What should our first research directive be?',
  },
];

const pageShell =
  'min-h-screen bg-[radial-gradient(circle_at_16%_14%,rgba(16,185,129,0.18),transparent_34%),radial-gradient(circle_at_82%_8%,rgba(52,211,153,0.14),transparent_30%),linear-gradient(180deg,#05120e_0%,#02110a_48%,#010a06_100%)] text-slate-100';

function BrandMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="rounded-2xl bg-emerald-400/20 p-3 text-emerald-300">
        <Leaf size={18} />
      </div>
      <div>
        <p className="font-outfit text-xl font-black tracking-tight">Yukti.AI</p>
        <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-300/70">Research Intelligence</p>
      </div>
    </div>
  );
}

function LandingScreen({ onLogin, onSignup }) {
  return (
    <div className={`${pageShell} relative overflow-hidden p-6 md:p-10`}>
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(16,185,129,0.04)_0%,transparent_40%,rgba(52,211,153,0.06)_100%)]" />

      <div className="relative mx-auto flex w-full max-w-6xl flex-col gap-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <BrandMark />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onLogin}
              className="rounded-xl border border-emerald-300/30 bg-emerald-500/10 px-4 py-2 text-xs font-black uppercase tracking-wider text-emerald-200 transition hover:bg-emerald-500/20"
            >
              Login
            </button>
            <button
              type="button"
              onClick={onSignup}
              className="rounded-xl bg-emerald-400 px-4 py-2 text-xs font-black uppercase tracking-wider text-slate-950 transition hover:bg-emerald-300"
            >
              Signup
            </button>
          </div>
        </header>

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-8 rounded-3xl border border-emerald-300/15 bg-slate-900/60 p-7 shadow-2xl backdrop-blur md:grid-cols-2 md:p-10"
        >
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-300">Autonomous Academic Engine</p>
            <h1 className="mt-4 font-outfit text-4xl font-black leading-tight tracking-tight md:text-5xl">
              Analyze repositories first, then orchestrate verified research.
            </h1>
            <p className="mt-4 text-sm leading-relaxed text-slate-300">
              Yukti starts with repository structure intelligence, extracts implementation context, and then launches
              evidence-grounded paper generation with references.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3 text-xs text-emerald-200">
              <span className="rounded-full border border-emerald-300/30 bg-emerald-500/10 px-3 py-1">Green platform mode</span>
              <span className="rounded-full border border-emerald-300/30 bg-emerald-500/10 px-3 py-1">GitHub + Folder ingestion</span>
              <span className="rounded-full border border-emerald-300/30 bg-emerald-500/10 px-3 py-1">Live citation pipeline</span>
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-300/15 bg-slate-950/55 p-5">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-300">Startup Sequence</p>
            <ol className="mt-4 space-y-3 text-sm text-slate-300">
              <li>1. Authenticate with Login or Signup.</li>
              <li>2. Provide title plus GitHub URL or folder upload.</li>
              <li>3. Repo analyzer maps structure and summarizes implementation.</li>
              <li>4. Research orchestration starts with source-grounded context.</li>
            </ol>
            <button
              type="button"
              onClick={onLogin}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-xs font-black uppercase tracking-wider text-slate-950 transition hover:bg-emerald-300"
            >
              Enter Platform
              <ArrowRight size={15} />
            </button>
          </div>
        </motion.section>
      </div>
    </div>
  );
}

function AuthScreen({ mode, setMode, form, setForm, onSubmit, loading, onBack }) {
  return (
    <div className={`${pageShell} flex items-center justify-center p-6`}>
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md rounded-3xl border border-white/10 bg-slate-900/70 p-8 shadow-2xl backdrop-blur"
      >
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-2xl bg-emerald-400/20 p-3 text-emerald-300">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="font-outfit text-2xl font-black tracking-tight">Yukti Platform</h1>
            <p className="text-xs uppercase tracking-widest text-slate-400">Research Control Access</p>
          </div>
        </div>

        <div className="mb-6 flex gap-2 rounded-xl bg-slate-800/70 p-1 text-xs font-bold uppercase tracking-wider">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`flex-1 rounded-lg py-2 transition ${mode === 'login' ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-400 hover:text-white'}`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => setMode('signup')}
            className={`flex-1 rounded-lg py-2 transition ${mode === 'signup' ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-400 hover:text-white'}`}
          >
            Signup
          </button>
        </div>

        <button
          type="button"
          onClick={onBack}
          className="mb-4 text-xs font-bold uppercase tracking-wider text-slate-400 transition hover:text-emerald-300"
        >
          Back to landing
        </button>

        <form onSubmit={onSubmit} className="space-y-4">
          {mode === 'signup' && (
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="Full name"
              className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm outline-none focus:border-emerald-400/60"
            />
          )}
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
            placeholder="Academic email"
            className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm outline-none focus:border-emerald-400/60"
          />
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
            placeholder="Password"
            className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm outline-none focus:border-emerald-400/60"
          />
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-black uppercase tracking-wider text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <ShieldCheck size={16} />
            {loading ? 'Initializing...' : mode === 'signup' ? 'Create Account' : 'Enter Platform'}
          </button>
        </form>
      </motion.div>
    </div>
  );
}

function IntakeScreen({
  user,
  title,
  setTitle,
  mode,
  setMode,
  githubUrl,
  setGithubUrl,
  folderLabel,
  onFolderChange,
  onStart,
  isStarting,
  error,
  systemStatus,
  onLogout,
}) {
  return (
    <div className={`${pageShell} min-h-screen p-6 md:p-10`}>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-emerald-300">Welcome to the Yukti Platform.</p>
            <h1 className="mt-2 font-outfit text-3xl font-black tracking-tight md:text-4xl">Research Interface Initialization</h1>
            <p className="mt-2 text-sm text-slate-400">
              Greetings, Scholar. Let's initialize your research interface and walks through our autonomous orchestration.
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-xs">
            <span className="font-bold text-slate-300">{user?.user?.name}</span>
            <button
              onClick={onLogout}
              className="rounded-lg bg-slate-800 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-300 hover:bg-slate-700"
            >
              <LogOut size={12} className="mr-1 inline" /> Logout
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-5">
          <div className="space-y-4 lg:col-span-2">
            {guideSteps.map((item) => (
              <div key={item.step} className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                <p className="text-xs font-black uppercase tracking-[0.22em] text-emerald-300">{item.step}</p>
                <h2 className="mt-2 text-lg font-bold text-white">{item.title}</h2>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{item.body}</p>
              </div>
            ))}
          </div>

          <form onSubmit={onStart} className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-xl lg:col-span-3">
            <div className="mb-6">
              <h2 className="font-outfit text-2xl font-black tracking-tight">Input research domain...</h2>
              <p className="mt-1 text-sm text-slate-400">Provide a paper title and one mandatory source type: GitHub link or local folder.</p>
            </div>

            <div className="space-y-5">
              <div>
                <label className="mb-2 block text-xs font-black uppercase tracking-[0.18em] text-slate-400">Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Example: Trustworthy LLMs for Clinical Reasoning"
                  className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm outline-none focus:border-emerald-400/60"
                />
              </div>

              <div>
                <label className="mb-2 block text-xs font-black uppercase tracking-[0.18em] text-slate-400">Source (Mandatory)</label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => setMode('github')}
                    className={`rounded-xl border px-4 py-3 text-left transition ${mode === 'github' ? 'border-emerald-400/60 bg-emerald-500/10 text-emerald-200' : 'border-white/10 bg-slate-950/40 text-slate-300 hover:border-white/20'}`}
                  >
                    <Github size={16} className="mb-2" />
                    <p className="text-sm font-bold">GitHub Link</p>
                    <p className="text-xs text-slate-400">Analyze public repository</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setMode('folder')}
                    className={`rounded-xl border px-4 py-3 text-left transition ${mode === 'folder' ? 'border-emerald-400/60 bg-emerald-500/10 text-emerald-200' : 'border-white/10 bg-slate-950/40 text-slate-300 hover:border-white/20'}`}
                  >
                    <FolderOpen size={16} className="mb-2" />
                    <p className="text-sm font-bold">Select Folder</p>
                    <p className="text-xs text-slate-400">Folder only, not zip</p>
                  </button>
                </div>
              </div>

              {mode === 'github' ? (
                <div>
                  <label className="mb-2 block text-xs font-black uppercase tracking-[0.18em] text-slate-400">GitHub URL</label>
                  <input
                    type="url"
                    required
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm outline-none focus:border-emerald-400/60"
                  />
                </div>
              ) : (
                <div>
                  <label className="mb-2 block text-xs font-black uppercase tracking-[0.18em] text-slate-400">Project Folder</label>
                  <input
                    type="file"
                    webkitdirectory=""
                    directory=""
                    multiple
                    onChange={onFolderChange}
                    className="block w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-400 file:px-3 file:py-1.5 file:text-xs file:font-bold file:text-slate-950"
                  />
                  <p className="mt-2 text-xs text-slate-400">{folderLabel || 'No folder selected yet.'}</p>
                </div>
              )}

              {error && (
                <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</p>
              )}

              <div className="flex items-center justify-between gap-3 pt-2">
                <div className="text-xs text-slate-500">
                  <BookOpen size={14} className="mr-1 inline" />
                  System status: {systemStatus?.available ? 'ready' : 'offline'}
                </div>
                <button
                  type="submit"
                  disabled={isStarting}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-5 py-3 text-sm font-black uppercase tracking-wider text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isStarting ? 'Launching...' : 'Start Research'}
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

const App = () => {
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState('login');
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' });
  const [authLoading, setAuthLoading] = useState(false);
  const [entryView, setEntryView] = useState('landing'); // landing | auth

  const [query, setQuery] = useState('');
  const [title, setTitle] = useState('');
  const [inputMode, setInputMode] = useState('github'); // github | folder
  const [githubUrl, setGithubUrl] = useState('');
  const [folderFiles, setFolderFiles] = useState([]);
  const [launchError, setLaunchError] = useState('');
  const [isLaunching, setIsLaunching] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);

  const { connect, sendMessage, status, agents, logs, report, plan, sections, setSections, messages, sessionId } = useResearch();

  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        setSystemStatus(data.llm);
      } catch {
        setSystemStatus(null);
      }
    };
    fetchSystemStatus();
  }, []);

  useEffect(() => {
    if (status !== 'idle') {
      setIsSearching(true);
    }
  }, [status]);

  const folderLabel = useMemo(() => {
    if (!folderFiles.length) return '';
    const relPath = folderFiles[0]?.webkitRelativePath || '';
    const root = relPath.split('/')[0] || 'Selected folder';
    return `${root} (${folderFiles.length} files selected)`;
  }, [folderFiles]);

  const handleAuthSubmit = (e) => {
    e.preventDefault();
    setAuthLoading(true);
    window.setTimeout(() => {
      const displayName = authForm.name.trim() || authForm.email.split('@')[0] || 'Scholar';
      setUser({
        status: 'success',
        user: {
          name: displayName,
          email: authForm.email,
          role: 'academic',
        },
        token: `session-${Date.now()}`,
      });
      setAuthLoading(false);
      setEntryView('landing');
    }, 400);
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setEntryView('auth');
  };

  const handleFolderChange = (e) => {
    const files = Array.from(e.target.files || []);
    setFolderFiles(files);
    setLaunchError('');
  };

  const buildResearchPrompt = (titleText, analysisData) => {
    const cleanTitle = titleText.trim();
    const summary = String(analysisData?.summary || '').replace(/\s+/g, ' ').trim();
    if (!summary) return cleanTitle;
    return `${cleanTitle}\n\nRepository context summary:\n${summary.slice(0, 1200)}`;
  };

  const handleStartResearch = async (e) => {
    e.preventDefault();
    if (!user) return;

    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setLaunchError('Title is required.');
      return;
    }

    if (inputMode === 'github' && !githubUrl.trim()) {
      setLaunchError('GitHub URL is mandatory when GitHub source is selected.');
      return;
    }

    if (inputMode === 'folder' && folderFiles.length === 0) {
      setLaunchError('Please select a folder. Zip upload is not used here.');
      return;
    }

    setIsLaunching(true);
    setLaunchError('');

    try {
      let analysisData = null;

      if (inputMode === 'github') {
        const url = githubUrl.trim();
        const res = await fetch('/api/repo/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repo_url: url,
            existing_title: cleanTitle,
            output_dir: './outputs/GitHub',
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== 'success') {
          throw new Error(data.detail || 'Repository analysis failed for GitHub URL.');
        }
        analysisData = data.data || null;
      } else {
        const formData = new FormData();
        formData.append('existing_title', cleanTitle);
        formData.append('output_dir', './outputs/GitHub');
        for (const file of folderFiles) {
          formData.append('files', file, file.webkitRelativePath || file.name);
        }

        const res = await fetch('/api/repo/analyze-folder', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== 'success') {
          throw new Error(data.detail || 'Repository analysis failed for folder upload.');
        }
        analysisData = data.data || null;
      }

      const displayTitle = (analysisData?.title || cleanTitle).trim();
      const researchPrompt = buildResearchPrompt(displayTitle, analysisData);
      setTitle(displayTitle);
      setQuery(displayTitle);
      connect(researchPrompt);
      setIsSearching(true);
    } catch (err) {
      setLaunchError(err?.message || String(err));
    } finally {
      setIsLaunching(false);
    }
  };

  if (!user) {
    if (entryView === 'landing') {
      return (
        <LandingScreen
          onLogin={() => openAuth('login')}
          onSignup={() => openAuth('signup')}
        />
      );
    }

    return (
      <AuthScreen
        mode={authMode}
        setMode={setAuthMode}
        form={authForm}
        setForm={setAuthForm}
        onSubmit={handleAuthSubmit}
        loading={authLoading}
        onBack={() => setEntryView('landing')}
      />
    );
  }

  if (!isSearching) {
    return (
      <IntakeScreen
        user={user}
        title={title}
        setTitle={setTitle}
        mode={inputMode}
        setMode={setInputMode}
        githubUrl={githubUrl}
        setGithubUrl={setGithubUrl}
        folderLabel={folderLabel}
        onFolderChange={handleFolderChange}
        onStart={handleStartResearch}
        isStarting={isLaunching}
        error={launchError}
        systemStatus={systemStatus}
        onLogout={() => {
          setUser(null);
          setEntryView('landing');
          setIsSearching(false);
          setSections([]);
          setQuery('');
          setTitle('');
          setGithubUrl('');
          setFolderFiles([]);
          setLaunchError('');
        }}
      />
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="workspace"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
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
          onNewResearch={() => {
            setIsSearching(false);
            setSections([]);
            setLaunchError('');
          }}
          systemStatus={systemStatus}
          onOpenSystemModal={() => {}}
        />
      </motion.div>
    </AnimatePresence>
  );
};

export default App;
