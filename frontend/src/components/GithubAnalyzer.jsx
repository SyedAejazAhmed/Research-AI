/**
 * GithubAnalyzer.jsx
 *
 * Simple UI panel for the GitHub Repository Intelligence Agent.
 * Calls POST /api/github/analyze and shows the result.
 */
import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';

const STEPS = [
  { label: 'Validate URL', icon: '🔗' },
  { label: 'Fetch Repo Metadata', icon: '📊' },
  { label: 'Fetch README & Files', icon: '📄' },
  { label: 'Synthesise Concepts (AI)', icon: '🧠' },
  { label: 'Generate Title (AI)', icon: '🏷️' },
  { label: 'Save Outputs', icon: '💾' },
];

export default function GithubAnalyzer() {
  const [repoUrl, setRepoUrl] = useState('');
  const [existingTitle, setExistingTitle] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');

  async function handleAnalyze() {
    const url = repoUrl.trim();
    if (!url) return;
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch('/api/github/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: url,
          existing_title: existingTitle.trim() || null,
          github_token: githubToken.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Analysis failed');
      setResult(data.data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-3xl">🔬</span>
        <div>
          <h2 className="text-lg font-bold text-white">GitHub Repository Intelligence</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Scrapes any public GitHub repository via the GitHub API — no cloning needed.
            Extracts README, topics, languages and key files, then synthesises concepts
            with local AI (gpt-oss:20b). Typically completes in under 30 s.
          </p>
        </div>
      </div>

      {/* Input form */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            GitHub Repository URL *
          </label>
          <input
            type="text"
            value={repoUrl}
            onChange={e => setRepoUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !loading && handleAnalyze()}
            placeholder="https://github.com/owner/repository"
            className="bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200
              placeholder:text-gray-600 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">
            Existing Title (optional — will be refined)
          </label>
          <input
            type="text"
            value={existingTitle}
            onChange={e => setExistingTitle(e.target.value)}
            placeholder="Leave blank to auto-generate"
            className="bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200
              placeholder:text-gray-600 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>

        {/* Advanced toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(v => !v)}
          className="self-start text-xs text-gray-500 hover:text-gray-300 transition-colors underline underline-offset-2"
        >
          {showAdvanced ? '▲ Hide advanced' : '▼ Advanced (optional GitHub token)'}
        </button>
        {showAdvanced && (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">
              GitHub Personal Access Token
              <span className="ml-2 text-gray-600 normal-case font-normal">(raises rate limit from 60 → 5000 req/h)</span>
            </label>
            <input
              type="password"
              value={githubToken}
              onChange={e => setGithubToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              className="bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200
                placeholder:text-gray-600 focus:outline-none focus:ring-1 focus:ring-violet-500 font-mono"
            />
          </div>
        )}
        <button
          onClick={handleAnalyze}
          disabled={loading || !repoUrl.trim()}
          className="self-start px-5 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500
            text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
          {loading ? 'Analysing…' : 'Analyse Repository'}
        </button>
      </div>

      {/* Loading pipeline display */}
      {loading && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <p className="text-xs text-gray-400 mb-4 uppercase tracking-wider font-medium">Pipeline Running</p>
          <div className="flex flex-col gap-3">
            {STEPS.map((step) => (
              <div key={step.label} className="flex items-center gap-3">
                <span className="text-lg">{step.icon}</span>
                <span className="text-sm text-gray-300">{step.label}</span>
                <span className="ml-auto text-xs text-gray-500">
                  <span className="inline-block w-3 h-3 border border-violet-500 border-t-transparent rounded-full animate-spin" />
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-4"
          >
            {/* Meta row */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">✅</span>
                <span className="text-sm font-semibold text-white">
                  Analysis complete in {result.elapsed_seconds?.toFixed(1)}s
                </span>
              </div>

              {/* Repo stats row */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-gray-800 rounded-lg p-3">
                  <p className="text-gray-500 mb-1">Repository</p>
                  <p className="text-gray-200 font-medium truncate">{result.repo_name}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3">
                  <p className="text-gray-500 mb-1">⭐ Stars</p>
                  <p className="text-gray-200 font-medium">{result.stars?.toLocaleString() ?? '—'}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3">
                  <p className="text-gray-500 mb-1">Files Scraped</p>
                  <p className="text-gray-200 font-medium">{result.files_analysed}</p>
                </div>
              </div>

              {/* Description */}
              {result.description && (
                <p className="text-xs text-gray-400 leading-relaxed border-l-2 border-violet-700 pl-3">
                  {result.description}
                </p>
              )}

              {/* Languages */}
              {result.languages?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {result.languages.slice(0, 8).map(lang => (
                    <span key={lang} className="px-2 py-0.5 bg-blue-900/30 border border-blue-700/30 rounded text-[10px] text-blue-300">{lang}</span>
                  ))}
                </div>
              )}

              {/* Topics */}
              {result.topics?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {result.topics.map(t => (
                    <span key={t} className="px-2 py-0.5 bg-gray-700/50 rounded text-[10px] text-gray-400">#{t}</span>
                  ))}
                </div>
              )}

              {/* Title */}
              <div className="bg-violet-900/20 border border-violet-700/30 rounded-lg p-3">
                <p className="text-xs text-violet-400 mb-1 font-medium uppercase tracking-wider">Generated Academic Title</p>
                <p className="text-sm text-white font-semibold leading-relaxed">{result.title}</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2">
              {['summary', 'tree'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 rounded-lg text-xs font-medium capitalize transition-colors
                    ${activeTab === tab
                      ? 'bg-violet-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                >
                  {tab === 'summary' ? '📋 Summary' : '🌳 Directory Tree'}
                </button>
              ))}
            </div>

            {activeTab === 'summary' && (
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed overflow-auto max-h-[500px]">
                  {result.summary}
                </pre>
              </div>
            )}
            {activeTab === 'tree' && (
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <pre className="text-xs text-gray-300 whitespace-pre font-mono leading-relaxed overflow-auto max-h-[500px]">
                  {result.tree}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
