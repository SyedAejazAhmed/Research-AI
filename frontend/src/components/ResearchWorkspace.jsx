/**
 * ResearchWorkspace.jsx
 *
 * Main 3-pane research workspace. Replaces the old tab-based dashboard
 * when a research session is active.
 *
 * Layout:
 * ┌────────────────────────────────────────────────────────────────────────┐
 * │  TOP BAR:  [Y logo] [research query]         [status] [progress] [⚙] │
 * ├──────────┬──────────────────────────────────┬──────────────────────────┤
 * │ SIDEBAR  │  SECTION CHAT (center)            │  IEEE PREVIEW (right)   │
 * │ sections │  ┌──────────────────────────────┐│                          │
 * │ list     │  │ editable section content      ││  [paper preview]         │
 * │ / status │  │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─││                          │
 * │          │  │ chat messages                 ││  [Generate PDF btn]      │
 * │          │  └──────────────────────────────┘│                          │
 * │          │  [input bar]                      │                          │
 * └──────────┴──────────────────────────────────┴──────────────────────────┘
 *
 * Props forwarded from App.jsx:
 *   query, sections, setSections, plan, status (pipeline), sessionId,
 *   agents, logs, report, messages, sendMessage, onNewResearch,
 *   systemStatus, onOpenSystemModal
 */
import { useState, useCallback } from 'react';
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Cpu, RefreshCw, Download, FileText, Activity, ChevronRight,
  BarChart2, MessageSquare, CheckCheck,
} from 'lucide-react';

import SectionSidebar, { SECTION_ORDER, SECTION_META } from './SectionSidebar';
import SectionChat from './SectionChat';
import IEEEPreview from './IEEEPreview';
import GradientText from './GradientText';
import ResearchMap from './ResearchMap';

// ── Progress helper ────────────────────────────────────────────────────────

const STATUS_PROGRESS = {
  idle:        0,
  planning:    15,
  researching: 45,
  synthesising: 75,
  publishing:  90,
  completed:   100,
  error:       100,
};

function statusColour(s) {
  if (s === 'completed') return 'text-emerald-400';
  if (s === 'error')     return 'text-red-400';
  return 'text-violet-400';
}

// ── Component ──────────────────────────────────────────────────────────────

export default function ResearchWorkspace({
  query,
  sections,
  setSections,
  plan,
  status,           // pipeline status
  sessionId,
  agents,
  logs,
  report,
  messages,
  sendMessage,
  onNewResearch,    // () => void  — back to search
  systemStatus,
  onOpenSystemModal,
}) {
  // Which section is currently focused in the center pane
  const [activeKey, setActiveKey] = useState('abstract');

  // Per-section edited text (users can type in the SectionChat textarea)
  const [editValues, setEditValues] = useState({});

  // Per-section approved state
  const [approvedKeys, setApprovedKeys] = useState(new Set());

  // Left panel tab: 'sections' | 'pipeline' | 'chat'
  const [sideMode, setSideMode] = useState('sections');

  // Keep references as a persistent editable section in the workspace.
  useEffect(() => {
    setSections(prev => {
      if (prev.some(s => s.key === 'references')) return prev;
      return [...prev, {
        index: 999,
        key: 'references',
        title: 'References',
        content: '',
      }];
    });
  }, [setSections]);

  const setEditValue = useCallback((key, val) => {
    setEditValues(prev => ({ ...prev, [key]: val }));
    // Also update the canonical sections array so preview stays in sync
    setSections(prev => prev.map(s => s.key === key ? { ...s, content: val } : s));
  }, [setSections]);

  function handleApprove(key) {
    // Save any edits back into sections before approving
    const edited = editValues[key];
    if (edited !== undefined) {
      setSections(prev => prev.map(s => s.key === key ? { ...s, content: edited } : s));
    }
    setApprovedKeys(prev => new Set([...prev, key]));
    // Auto-advance to next unapproved section
    const idx     = SECTION_ORDER.indexOf(key);
    const nextKey = SECTION_ORDER.slice(idx + 1).find(k => !approvedKeys.has(k));
    if (nextKey) setActiveKey(nextKey);
  }

  function handleUnapprove(key) {
    setApprovedKeys(prev => { const n = new Set(prev); n.delete(key); return n; });
  }

  const progress  = STATUS_PROGRESS[status] ?? 0;
  const activeSec = sections.find(s => s.key === activeKey) || null;

  // Abstract content — passed to SectionChat as context for other sections
  const abstractContent = editValues['abstract'] ?? sections.find(s => s.key === 'abstract')?.content ?? '';

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gray-950">

      {/* ╔═══════════════════════════════════════════════════════╗
          ║  TOP BAR                                              ║
          ╚═══════════════════════════════════════════════════════╝ */}
      <div className="flex items-center gap-4 px-5 py-2.5 border-b border-gray-800 shrink-0 bg-gray-950/90 backdrop-blur-xl z-10">
        {/* Logo */}
        <div className="flex items-center gap-2 cursor-pointer select-none" onClick={onNewResearch}>
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center font-black text-sm text-white shadow-lg">Y</div>
          <GradientText colors={["#6366f1","#a855f7","#22d3ee","#6366f1"]} animationSpeed={8} className="font-outfit font-black text-lg tracking-tighter hidden sm:block">
            YUKTI.AI
          </GradientText>
        </div>

        <div className="h-5 w-px bg-gray-700" />

        {/* Query title */}
        <div className="flex-1 min-w-0">
          <div className="text-[9px] font-black uppercase tracking-widest text-gray-600">Research Query</div>
          <div className="text-sm font-medium text-gray-200 truncate">{plan?.title || query}</div>
        </div>

        {/* Progress bar */}
        <div className="w-40 hidden md:block">
          <div className="flex items-center gap-2 mb-0.5">
            <div className={`w-1.5 h-1.5 rounded-full ${status === 'completed' ? 'bg-emerald-500' : 'bg-violet-500 animate-ping'}`} />
            <span className={`text-[9px] font-black uppercase tracking-widest ${statusColour(status)}`}>{status}</span>
          </div>
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
            <motion.div
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.7 }}
              className="h-full bg-gradient-to-r from-violet-500 to-emerald-400 rounded-full"
            />
          </div>
        </div>

        {/* Section mode toggles (sidebar content) */}
        <div className="hidden lg:flex items-center gap-1 bg-gray-900 rounded-xl p-1 border border-gray-700">
          {[
            { key: 'sections',  icon: <FileText  size={13} />, label: 'Sections' },
            { key: 'pipeline',  icon: <Activity  size={13} />, label: 'Pipeline' },
            { key: 'chat',      icon: <MessageSquare size={13} />, label: 'Chat' },
          ].map(({ key, icon, label }) => (
            <button
              key={key}
              onClick={() => setSideMode(key)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 transition-all ${
                sideMode === key ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {icon} {label}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {report && (
            <a href={`/api/export/${sessionId}/pdf`} target="_blank" rel="noreferrer"
              className="p-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-all border border-gray-700">
              <Download size={15} />
            </a>
          )}
          <button
            onClick={onOpenSystemModal}
            className="p-2 rounded-xl bg-gray-800 hover:bg-gray-700 border border-gray-700 transition-all"
          >
            <Cpu size={15} className={systemStatus?.available ? 'text-emerald-400' : 'text-gray-500'} />
          </button>
          <button
            onClick={onNewResearch}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold border border-gray-700 transition-all"
          >
            <RefreshCw size={13} /> New
          </button>
        </div>
      </div>

      {/* ╔═══════════════════════════════════════════════════════╗
          ║  MAIN 3-PANE BODY                                     ║
          ╚═══════════════════════════════════════════════════════╝ */}
      <div className="flex-1 flex overflow-hidden">

        {/* LEFT PANE — Sidebar controlled by sideMode */}
        <AnimatePresence mode="wait">
          {sideMode === 'sections' && (
            <motion.div
              key="sections-sidebar"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="flex"
            >
              <SectionSidebar
                sections={sections}
                approvedKeys={approvedKeys}
                activeKey={activeKey}
                setActiveKey={setActiveKey}
                editValues={editValues}
                pipelineStatus={status}
              />
            </motion.div>
          )}

          {sideMode === 'pipeline' && (
            <motion.div
              key="pipeline-sidebar"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="w-72 bg-gray-950 border-r border-gray-800 flex flex-col overflow-y-auto p-3 gap-3"
            >
              <div className="text-[9px] font-black uppercase tracking-widest text-gray-600 px-1 mb-1">Pipeline</div>
              <ResearchMap agents={agents} logs={logs} compact />
            </motion.div>
          )}

          {sideMode === 'chat' && (
            <motion.div
              key="chat-sidebar"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="w-72 bg-gray-950 border-r border-gray-800 flex flex-col overflow-hidden"
            >
              <div className="px-4 py-2.5 border-b border-gray-800 text-[9px] font-black uppercase tracking-widest text-gray-600">
                Research Chat
              </div>
              <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-3">
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`text-xs px-3 py-2 rounded-2xl max-w-[90%] leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-violet-600 text-white rounded-br-sm'
                        : 'bg-gray-800 text-gray-300 rounded-bl-sm'
                    }`}>
                      {m.content}
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-3 border-t border-gray-800">
                <form onSubmit={e => { e.preventDefault(); const v = e.target.msg.value.trim(); if(v){sendMessage(v);e.target.reset();} }} className="flex gap-2">
                  <input name="msg" placeholder="Ask Yukti…" className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500/50 transition-colors" />
                  <button type="submit" className="p-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white transition-colors"><ChevronRight size={14} /></button>
                </form>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* CENTER PANE — Section Chat */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeKey}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <SectionChat
                sectionKey={activeKey}
                section={activeSec}
                editValue={editValues[activeKey] ?? activeSec?.content}
                setEditValue={(val) => setEditValue(activeKey, val)}
                isApproved={approvedKeys.has(activeKey)}
                onApprove={() => handleApprove(activeKey)}
                onUnapprove={() => handleUnapprove(activeKey)}
                plan={plan}
                abstractContent={abstractContent}
              />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* RIGHT PANE — IEEE Preview */}
        <IEEEPreview
          sections={sections}
          editValues={editValues}
          activeKey={activeKey}
          plan={plan}
          query={query}
          approvedKeys={approvedKeys}
          sessionId={sessionId}
        />
      </div>
    </div>
  );
}
