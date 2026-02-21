/**
 * SectionReviewPanel.jsx
 *
 * Section-by-section academic paper review flow.
 *
 * Props:
 *   sections      {Array}    - sections from WS section_ready events
 *   setSections   {Function} - update sections (for edits)
 *   sessionId     {string}   - current session ID (used for LaTeX compile)
 *   status        {string}   - pipeline status ('synthesising', 'completed', etc.)
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Canonical order for academic sections
const SECTION_ORDER = [
  'abstract',
  'introduction',
  'related_studies',
  'methodology',
  'result_discussion',
  'conclusion',
];

const SECTION_LABELS = {
  abstract:          'Abstract',
  introduction:      'Introduction',
  related_studies:   'Related Studies',
  methodology:       'Methodology',
  result_discussion: 'Result and Discussion',
  conclusion:        'Conclusion',
};

function statusBadge(state) {
  if (state === 'approved')   return 'bg-green-500/20 text-green-400 border border-green-500/30';
  if (state === 'editing')    return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
  if (state === 'pending')    return 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
  if (state === 'waiting')    return 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30';
  return 'bg-gray-500/20 text-gray-400 border border-gray-500/30';
}

export default function SectionReviewPanel({ sections, setSections, sessionId, status, plan }) {
  const [activeKey, setActiveKey] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [approvedKeys, setApprovedKeys] = useState(new Set());
  const [compiling, setCompiling] = useState(false);
  const [compileResult, setCompileResult] = useState(null);
  const [partialGenerating, setPartialGenerating] = useState(new Set());
  const [partialResults, setPartialResults] = useState({});
  const textareaRef = useRef(null);

  // Sort sections in canonical academic order
  const sorted = [...sections].sort(
    (a, b) => SECTION_ORDER.indexOf(a.key) - SECTION_ORDER.indexOf(b.key)
  );

  const allKeysAvailable = SECTION_ORDER.every(k => sorted.some(s => s.key === k));
  const allApproved = allKeysAvailable && SECTION_ORDER.every(k => approvedKeys.has(k));

  // Auto-open first un-approved section when it arrives
  useEffect(() => {
    if (!activeKey && sorted.length > 0) {
      const firstPending = sorted.find(s => !approvedKeys.has(s.key));
      if (firstPending) setActiveKey(firstPending.key);
    }
  }, [sorted.length]);

  // Keep textarea in sync when switching sections
  useEffect(() => {
    if (activeKey && textareaRef.current) {
      const sec = sorted.find(s => s.key === activeKey);
      if (sec) {
        setEditValues(prev => ({ ...prev, [activeKey]: prev[activeKey] ?? sec.content }));
        textareaRef.current.focus();
      }
    }
  }, [activeKey]);

  function handleApprove(key) {
    // Save edited content back into sections
    const editedContent = editValues[key];
    if (editedContent !== undefined) {
      setSections(prev => prev.map(s => s.key === key ? { ...s, content: editedContent } : s));
    }
    setApprovedKeys(prev => new Set([...prev, key]));

    // Auto-advance to next section
    const idx = SECTION_ORDER.indexOf(key);
    const nextKey = SECTION_ORDER.slice(idx + 1).find(k => !approvedKeys.has(k));
    setActiveKey(nextKey || null);
  }

  function handleUnapprove(key) {
    setApprovedKeys(prev => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
    setActiveKey(key);
  }

  async function handleGeneratePartial(upToKey) {
    // Collect all sections from canonical order up to and including upToKey
    const upToIdx = SECTION_ORDER.indexOf(upToKey);
    const keysToInclude = SECTION_ORDER.slice(0, upToIdx + 1);

    const paperTitle = plan?.title || plan?.query || 'Research Paper';

    // Abstract is handled separately; body sections go into the sections array
    const abstractSec = sorted.find(s => s.key === 'abstract');
    const abstractText = abstractSec
      ? (editValues['abstract'] ?? abstractSec.content)
      : '';

    const bodySections = keysToInclude
      .filter(k => k !== 'abstract')
      .map(k => {
        const sec = sorted.find(s => s.key === k);
        if (!sec) return null;
        return {
          title:   SECTION_LABELS[k] || k,
          content: editValues[k] ?? sec.content,
        };
      })
      .filter(Boolean);

    setPartialGenerating(prev => new Set([...prev, upToKey]));
    setPartialResults(prev => ({ ...prev, [upToKey]: null }));

    try {
      const res = await fetch('/api/write/partial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title:      paperTitle,
          abstract:   abstractText,
          sections:   bodySections,
          citations:  {},
          compile_pdf: true,
          template:   'article',
          author:     'Yukti Research AI',
          session_id: sessionId || '',
        }),
      });
      const data = await res.json();
      setPartialResults(prev => ({ ...prev, [upToKey]: data }));
    } catch (err) {
      setPartialResults(prev => ({ ...prev, [upToKey]: { error: String(err) } }));
    } finally {
      setPartialGenerating(prev => {
        const next = new Set(prev);
        next.delete(upToKey);
        return next;
      });
    }
  }

  async function handleCompileLaTeX() {
    if (!sessionId) return;
    setCompiling(true);
    setCompileResult(null);
    try {
      const res = await fetch('/api/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          compile_pdf: true,
          template: 'article',
          author: 'Yukti Research AI',
        }),
      });
      const data = await res.json();
      setCompileResult(data);
    } catch (err) {
      setCompileResult({ error: String(err) });
    } finally {
      setCompiling(false);
    }
  }

  if (sections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500 gap-3">
        {status === 'synthesising' || status === 'researching' || status === 'planning' ? (
          <>
            <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm">Generating sections — they will appear here for review…</p>
          </>
        ) : (
          <p className="text-sm">Run a research query to generate sections for review.</p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-gray-800 rounded-full h-2">
          <div
            className="bg-violet-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${(approvedKeys.size / SECTION_ORDER.length) * 100}%` }}
          />
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {approvedKeys.size} / {SECTION_ORDER.length} approved
        </span>
      </div>

      {/* Section stepper */}
      <div className="flex gap-2 flex-wrap">
        {SECTION_ORDER.map((key, idx) => {
          const sec = sorted.find(s => s.key === key);
          const isApproved = approvedKeys.has(key);
          const isActive = activeKey === key;
          const isReady = !!sec;

          return (
            <button
              key={key}
              disabled={!isReady}
              onClick={() => isReady && setActiveKey(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                ${isActive ? 'ring-2 ring-violet-500 bg-violet-500/20 text-violet-300' : ''}
                ${isApproved && !isActive ? 'bg-green-500/20 text-green-400' : ''}
                ${!isApproved && !isActive && isReady ? 'bg-gray-800 text-gray-400 hover:bg-gray-700' : ''}
                ${!isReady ? 'bg-gray-800/40 text-gray-600 cursor-not-allowed' : ''}
              `}
            >
              {isApproved ? '✓ ' : ''}{SECTION_LABELS[key] || key}
              {!isReady && (
                <span className="ml-1 inline-block w-2 h-2 border border-yellow-500 border-t-transparent rounded-full animate-spin align-middle" />
              )}
            </button>
          );
        })}
      </div>

      {/* Active section editor */}
      <AnimatePresence mode="wait">
        {activeKey && (() => {
          const sec = sorted.find(s => s.key === activeKey);
          if (!sec) return null;
          const isApproved = approvedKeys.has(activeKey);
          const currentEdit = editValues[activeKey] ?? sec.content;

          return (
            <motion.div
              key={activeKey}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="bg-gray-900 border border-gray-700 rounded-xl p-5 flex flex-col gap-4"
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-white">
                  {SECTION_LABELS[activeKey] || activeKey}
                </h3>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(isApproved ? 'approved' : 'editing')}`}>
                  {isApproved ? 'APPROVED' : 'REVIEWING'}
                </span>
              </div>

              {/* Textarea */}
              <textarea
                ref={textareaRef}
                value={currentEdit}
                onChange={e => setEditValues(prev => ({ ...prev, [activeKey]: e.target.value }))}
                disabled={isApproved}
                rows={12}
                className={`w-full bg-gray-950 border rounded-lg p-3 text-sm text-gray-200 font-mono resize-y
                  focus:outline-none focus:ring-1 focus:ring-violet-500 transition-colors
                  ${isApproved ? 'border-green-700/40 opacity-70 cursor-default' : 'border-gray-700'}
                `}
              />

              {/* Action buttons */}
              <div className="flex gap-3 justify-end flex-wrap">
                {isApproved ? (
                  <button
                    onClick={() => handleUnapprove(activeKey)}
                    className="px-4 py-2 rounded-lg text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
                  >
                    Edit Again
                  </button>
                ) : (
                  <>
                    <span className="text-xs text-gray-500 self-center mr-auto">
                      {currentEdit.trim().split(/\s+/).length} words
                    </span>
                    <button
                      onClick={() => handleApprove(activeKey)}
                      className="px-4 py-2 rounded-lg text-sm bg-green-600 hover:bg-green-500 text-white font-medium transition-colors"
                    >
                      Approve &amp; Next
                    </button>
                  </>
                )}

                {/* ── Per-section Generate PDF button ───────────────── */}
                <button
                  onClick={() => handleGeneratePartial(activeKey)}
                  disabled={partialGenerating.has(activeKey)}
                  title={`Generate PDF up to "${SECTION_LABELS[activeKey] || activeKey}"`}
                  className="px-4 py-2 rounded-lg text-sm bg-indigo-700 hover:bg-indigo-600 text-white font-medium transition-colors disabled:opacity-60 flex items-center gap-2"
                >
                  {partialGenerating.has(activeKey)
                    ? <><span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" /> Generating…</>
                    : <>📄 Generate PDF</>}
                </button>
              </div>

              {/* ── Partial PDF result for this section ──────────────── */}
              {partialResults[activeKey] && (
                <div className="bg-gray-800 rounded-lg p-3 text-sm">
                  {partialResults[activeKey].error ? (
                    <p className="text-red-400">Error: {partialResults[activeKey].error}</p>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <p className={`font-medium text-xs ${partialResults[activeKey].pdf_success ? 'text-green-400' : 'text-yellow-400'}`}>
                        {partialResults[activeKey].pdf_success
                          ? `✓ PDF ready — includes all sections up to "${SECTION_LABELS[activeKey] || activeKey}"`
                          : '✓ LaTeX generated (PDF compilation skipped or failed)'}
                      </p>
                      <div className="flex gap-3 flex-wrap">
                        {partialResults[activeKey].download_tex && (
                          <a
                            href={partialResults[activeKey].download_tex}
                            target="_blank" rel="noreferrer"
                            className="px-3 py-1 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs transition-colors"
                          >
                            Download .tex
                          </a>
                        )}
                        {partialResults[activeKey].download_pdf && (
                          <a
                            href={partialResults[activeKey].download_pdf}
                            target="_blank" rel="noreferrer"
                            className="px-3 py-1 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-xs transition-colors"
                          >
                            ⬇ Download PDF
                          </a>
                        )}
                      </div>
                      {partialResults[activeKey].compile_errors?.length > 0 && (
                        <details className="mt-1">
                          <summary className="text-yellow-400 text-xs cursor-pointer">
                            {partialResults[activeKey].compile_errors.length} compile warning(s)
                          </summary>
                          <pre className="text-xs text-gray-400 mt-1 whitespace-pre-wrap">
                            {partialResults[activeKey].compile_errors.join('\n')}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          );
        })()}
      </AnimatePresence>

      {/* All approved — compile button */}
      {allApproved && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-gray-900 border border-green-700/40 rounded-xl p-5 flex flex-col gap-4"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎓</span>
            <div>
              <p className="text-sm font-semibold text-white">All sections approved!</p>
              <p className="text-xs text-gray-400 mt-0.5">Compile the paper to a LaTeX / PDF document.</p>
            </div>
          </div>

          {!compileResult ? (
            <button
              onClick={handleCompileLaTeX}
              disabled={compiling}
              className="self-start px-5 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-colors disabled:opacity-60 flex items-center gap-2"
            >
              {compiling && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              {compiling ? 'Compiling…' : 'Compile to LaTeX / PDF'}
            </button>
          ) : (
            <div className="bg-gray-800 rounded-lg p-4 text-sm">
              {compileResult.error ? (
                <p className="text-red-400">Error: {compileResult.error}</p>
              ) : (
                <div className="flex flex-col gap-2">
                  <p className="text-green-400 font-medium">
                    {compileResult.pdf_success ? '✓ PDF compiled successfully' : '✓ LaTeX generated (PDF compilation skipped)'}
                  </p>
                  <div className="flex gap-3 flex-wrap mt-1">
                    {compileResult.download_tex && (
                      <a
                        href={compileResult.download_tex}
                        className="px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs transition-colors"
                      >
                        Download .tex
                      </a>
                    )}
                    {compileResult.download_pdf && (
                      <a
                        href={compileResult.download_pdf}
                        className="px-3 py-1.5 rounded-lg bg-violet-700 hover:bg-violet-600 text-white text-xs transition-colors"
                      >
                        Download PDF
                      </a>
                    )}
                  </div>
                  {compileResult.compile_errors?.length > 0 && (
                    <details className="mt-2">
                      <summary className="text-yellow-400 text-xs cursor-pointer">
                        {compileResult.compile_errors.length} compile warning(s)
                      </summary>
                      <pre className="text-xs text-gray-400 mt-1 whitespace-pre-wrap">
                        {compileResult.compile_errors.join('\n')}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
