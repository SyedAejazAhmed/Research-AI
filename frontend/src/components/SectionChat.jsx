/**
 * SectionChat.jsx
 *
 * Chat-like interface for reviewing and refining a single paper section.
 *
 * Layout (top → bottom):
 *  ┌──────────────────────────────────────────────┐
 *  │  Section title  •  word count badge           │
 *  ├──────────────────────────────────────────────┤
 *  │  [Editable content textarea]                  │
 *  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
 *  │  [AI chat reply]                              │
 *  │  [User message]                               │
 *  │  ...                                          │
 *  ├──────────────────────────────────────────────┤
 *  │  [✓ Approve]     [input……]           [Send▶] │
 *  └──────────────────────────────────────────────┘
 *
 * Props:
 *   sectionKey      — e.g. "abstract"
 *   section         — {key, title, content, index}  (null = not yet generated)
 *   editValue       — current edited text for this section
 *   setEditValue    — (text) => void
 *   isApproved      — boolean
 *   onApprove       — () => void
 *   onUnapprove     — () => void
 *   plan            — {title, query, ...}  (for refine context)
 *   abstractContent — string  (used as context for non-abstract sections)
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, CheckCheck, RotateCcw, Loader2, FileText } from 'lucide-react';
import { SECTION_META } from './SectionSidebar';

// ── Helpers ────────────────────────────────────────────────────────────────

function wordCount(text = '') {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function referenceCount(text = '') {
  const t = (text || '').trim();
  if (!t) return 0;

  const bracketed = t.match(/^\[(\d+)\]/gm);
  if (bracketed?.length) return bracketed.length;

  return t.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean).length;
}

function WordCountBadge({ count, min, max }) {
  const ok  = count >= min && count <= max;
  const low = count < min;
  return (
    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
      ok  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
      low ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' :
            'bg-red-500/10 text-red-400 border-red-500/30'
    }`}>
      {count} / {max} words
    </span>
  );
}

function ReferenceCountBadge({ count, min, max }) {
  const ok = count >= min && count <= max;
  const low = count < min;
  return (
    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
      ok ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
      low ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' :
            'bg-red-500/10 text-red-400 border-red-500/30'
    }`}>
      {count} / {max} references
    </span>
  );
}

// ── Component ──────────────────────────────────────────────────────────────

export default function SectionChat({
  sectionKey,
  section,
  editValue,
  setEditValue,
  isApproved,
  onApprove,
  onUnapprove,
  plan,
  abstractContent = '',
  referenceStyle = 'IEEE',
  onReferenceStyleChange,
  referencesLoading = false,
  referencesError = '',
}) {
  const meta = SECTION_META[sectionKey] || {};
  const isReferences = sectionKey === 'references';

  const buildIntroMessage = () => {
    if (isReferences) {
      return `The **${meta.label || sectionKey}** section has been generated. Select citation style (**IEEE** or **Harvard**) and review the entries.

• *"Use Harvard format"*
• *"Keep only sources from 2020 onwards"*
• *"Remove duplicate citations"*`;
    }

    return `The **${meta.label || sectionKey}** section has been generated. Review the content above and make any edits. You can also ask me to refine it — for example:\n\n• *"Make it more concise"*\n• *"Add more detail about methodology"*\n• *"Focus on recent works from 2020 onwards"*`;
  };

  // Per-section chat thread
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      content: section
        ? buildIntroMessage()
        : `Waiting for the **${meta.label || sectionKey}** section to be generated…`,
    },
  ]);
  const [userInput, setUserInput]     = useState('');
  const [refining, setRefining]       = useState(false);
  const chatEndRef  = useRef(null);
  const textareaRef = useRef(null);

  // Re-initialise chat greeting when section first arrives
  useEffect(() => {
    if (section && chatMessages.length === 1 && chatMessages[0].content.includes('Waiting')) {
      setChatMessages([{
        role: 'assistant',
        content: `The **${meta.label || sectionKey}** section is ready ✓\n\nTarget: ${meta.ieee}. You can edit the text directly above or tell me how to refine it.`,
      }]);
    }
  }, [section, chatMessages, meta.label, meta.ieee, sectionKey]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, refining]);

  async function handleSend() {
    const msg = userInput.trim();
    if (!msg || refining || !section) return;
    setUserInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: msg }]);
    setRefining(true);

    try {
      const res = await fetch('/api/section/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_key:     sectionKey,
          section_title:   meta.label || sectionKey,
          current_content: editValue ?? section.content,
          user_message:    msg,
          paper_title:     plan?.title || plan?.query || 'Research Paper',
          context_summary: sectionKey !== 'abstract' ? abstractContent : '',
          session_id:      '',
        }),
      });
      const data = await res.json();

      if (data.status === 'success' && data.content) {
        setEditValue(data.content);
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `Done ✓ I've updated the **${meta.label}** section. Feel free to review the changes above or ask for further adjustments.`,
        }]);
      } else {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `Sorry, I ran into an issue: ${data.detail || 'Unknown error'}. Please try again.`,
        }]);
      }
    } catch (err) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `Network error: ${err.message}`,
      }]);
    } finally {
      setRefining(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const wc = wordCount(editValue ?? section?.content ?? '');
  const rc = referenceCount(editValue ?? section?.content ?? '');

  // ── Not yet generated ──────────────────────────────────────────────────
  if (!section) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-gray-500">
        <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center">
          <Loader2 size={28} className="animate-spin text-violet-400" />
        </div>
        <div className="text-sm font-medium">Generating {meta.label}…</div>
        <div className="text-xs text-gray-600">{meta.ieee}</div>
      </div>
    );
  }

  // ── Generated ──────────────────────────────────────────────────────────
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* ── Section header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-3">
          <FileText size={16} className="text-violet-400 shrink-0" />
          <div>
            <h2 className="text-sm font-bold text-white">{meta.label}</h2>
            <div className="text-[9px] text-gray-500 uppercase tracking-widest">
              {isReferences ? `${referenceStyle} reference list` : meta.ieee}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isReferences && (
            <>
              <select
                value={referenceStyle}
                onChange={(e) => onReferenceStyleChange?.(e.target.value)}
                disabled={referencesLoading || isApproved}
                className="px-2 py-1 rounded-lg text-xs bg-gray-900 border border-gray-700 text-gray-200 focus:outline-none focus:border-violet-500/50 disabled:opacity-50"
              >
                <option value="IEEE">IEEE</option>
                <option value="HARVARD">Harvard</option>
              </select>
              {referencesLoading && (
                <span className="text-[10px] text-blue-400 flex items-center gap-1">
                  <Loader2 size={11} className="animate-spin" /> generating
                </span>
              )}
            </>
          )}
          {isReferences ? (
            <ReferenceCountBadge count={rc} min={meta.minRefs || 24} max={meta.maxRefs || 30} />
          ) : (
            <WordCountBadge count={wc} min={meta.min} max={meta.max} />
          )}
          {isApproved ? (
            <button
              onClick={onUnapprove}
              className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors flex items-center gap-1.5"
            >
              <RotateCcw size={11} /> Edit
            </button>
          ) : (
            <button
              onClick={onApprove}
              className="px-3 py-1.5 rounded-lg text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors flex items-center gap-1.5"
            >
              <CheckCheck size={11} /> Approve
            </button>
          )}
        </div>
      </div>

      {/* ── Content + chat scroll area ────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">

        {isReferences && referencesError && (
          <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            {referencesError}
          </div>
        )}

        {/* Editable section content block */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800/60 border-b border-gray-700">
            <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">
              Section Content
            </span>
            <span className={`text-[9px] font-mono ${isApproved ? 'text-emerald-500' : 'text-blue-400'}`}>
              {isApproved ? '✓ APPROVED' : '● EDITING'}
            </span>
          </div>
          <textarea
            ref={textareaRef}
            value={editValue ?? section.content}
            onChange={e => setEditValue(e.target.value)}
            disabled={isApproved}
            rows={10}
            className={`w-full bg-transparent px-4 py-3 text-sm text-gray-200 font-mono resize-y leading-relaxed
              focus:outline-none transition-colors
              ${isApproved ? 'opacity-60 cursor-default' : ''}
            `}
          />
        </div>

        {/* Chat divider */}
        <div className="flex items-center gap-3 text-[10px] text-gray-600 uppercase tracking-widest">
          <div className="flex-1 h-px bg-gray-800" />
          <span>AI Refinement Chat</span>
          <div className="flex-1 h-px bg-gray-800" />
        </div>

        {/* Chat messages */}
        {chatMessages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-violet-600 text-white rounded-br-sm'
                : 'bg-gray-800 text-gray-200 rounded-bl-sm border border-gray-700'
            }`}>
              {msg.content}
            </div>
          </motion.div>
        ))}

        {/* Refining spinner */}
        <AnimatePresence>
          {refining && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex justify-start"
            >
              <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-sm px-4 py-2.5 flex items-center gap-2 text-sm text-gray-400">
                <Loader2 size={14} className="animate-spin text-violet-400" />
                <span>Refining section…</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={chatEndRef} />
      </div>

      {/* ── Input bar ─────────────────────────────────────────────────── */}
      <div className="shrink-0 px-5 py-3 border-t border-gray-800 bg-gray-950">
        <div className="flex items-end gap-2">
          <textarea
            value={userInput}
            onChange={e => setUserInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isApproved
                ? 'Section approved — click Edit to make changes'
                : 'Ask AI to refine this section… (Enter to send)'
            }
            disabled={!section || isApproved || refining}
            rows={2}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-200
              placeholder:text-gray-600 resize-none focus:outline-none focus:border-violet-500/50
              transition-colors disabled:opacity-40"
          />
          <button
            onClick={handleSend}
            disabled={!userInput.trim() || !section || isApproved || refining}
            className="p-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white transition-colors disabled:opacity-30 shrink-0"
          >
            {refining ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
        <div className="text-[9px] text-gray-700 mt-1.5 pl-1">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
