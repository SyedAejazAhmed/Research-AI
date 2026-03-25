/**
 * SectionSidebar.jsx
 *
 * Left sidebar for the Research Workspace.
 * Shows each academic section with:
 *  - Real-time status (pending / generating / ready / approved)
 *  - Word count vs IEEE target
 *  - Click to focus that section in the chat panel
 */
import { motion } from 'framer-motion';
import { CheckCheck, Check, Loader2, Clock, FileText } from 'lucide-react';

// ── Constants ──────────────────────────────────────────────────────────────

export const SECTION_ORDER = [
  'abstract',
  'introduction',
  'related_studies',
  'methodology',
  'result_discussion',
  'conclusion',
  'references',
];

export const SECTION_META = {
  abstract:          { label: 'Abstract',              icon: '✦', min: 150,  max: 250,  ieee: '150–250 words'  },
  introduction:      { label: 'Introduction',           icon: '①', min: 400,  max: 600,  ieee: '400–600 words'  },
  related_studies:   { label: 'Related Studies',        icon: '②', min: 600,  max: 900,  ieee: '600–900 words'  },
  methodology:       { label: 'Methodology',            icon: '③', min: 500,  max: 800,  ieee: '500–800 words'  },
  result_discussion: { label: 'Result & Discussion',    icon: '④', min: 800,  max: 1200, ieee: '800–1200 words' },
  conclusion:        { label: 'Conclusion',             icon: '⑤', min: 200,  max: 350,  ieee: '200–350 words'  },
  references:        { label: 'References',             icon: '⑥', min: 120,  max: 600,  ieee: 'IEEE reference list' },
};

function wordCount(text = '') {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function WordBar({ count, min, max }) {
  const pct = Math.min(100, Math.round((count / max) * 100));
  const ok  = count >= min && count <= max;
  const low = count < min;
  return (
    <div className="mt-1.5">
      <div className="h-1 w-full bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            ok ? 'bg-emerald-500' : low ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className={`text-[10px] mt-0.5 font-mono ${ok ? 'text-emerald-500' : 'text-gray-500'}`}>
        {count} / {max}
      </div>
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────────────

export default function SectionSidebar({
  sections,          // [{key, title, content, index}]
  approvedKeys,      // Set<string>
  activeKey,
  setActiveKey,
  editValues,        // {[key]: string}
  pipelineStatus,    // 'idle'|'planning'|'researching'|'synthesising'|'completed'
}) {
  return (
    <div className="flex flex-col h-full bg-gray-950 border-r border-gray-800 w-56 shrink-0">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-violet-400" />
          <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">
            Sections
          </span>
        </div>
        <div className="text-[9px] text-gray-600 mt-0.5 uppercase tracking-widest">
          IEEE Paper Format
        </div>
      </div>

      {/* Section list */}
      <div className="flex-1 overflow-y-auto py-2">
        {SECTION_ORDER.map((key) => {
          const meta    = SECTION_META[key];
          const secData = sections.find(s => s.key === key);
          const isReady = !!secData;
          const isApproved = approvedKeys.has(key);
          const isActive   = activeKey === key;
          const isGenerating =
            pipelineStatus === 'synthesising' &&
            !isReady;

          // Use edited value if present, else original
          const displayContent = editValues?.[key] ?? secData?.content ?? '';
          const wc = wordCount(displayContent);

          return (
            <motion.button
              key={key}
              onClick={() => isReady && setActiveKey(key)}
              disabled={!isReady}
              whileHover={isReady ? { x: 2 } : {}}
              className={`
                w-full text-left px-4 py-2.5 transition-all relative
                ${isActive
                  ? 'bg-violet-500/10 border-r-2 border-violet-500'
                  : isReady
                    ? 'hover:bg-gray-900'
                    : 'opacity-40 cursor-not-allowed'}
              `}
            >
              {/* Status dot */}
              <div className="flex items-start gap-2.5">
                <div className={`mt-0.5 shrink-0 ${isActive ? 'text-violet-400' : isApproved ? 'text-emerald-400' : isReady ? 'text-blue-400' : 'text-gray-600'}`}>
                  {isApproved ? (
                    <CheckCheck size={13} />
                  ) : isGenerating ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : isReady ? (
                    <Check size={13} />
                  ) : (
                    <Clock size={13} />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className={`text-xs font-semibold truncate ${
                    isActive ? 'text-violet-300' :
                    isApproved ? 'text-emerald-300' :
                    isReady ? 'text-gray-200' : 'text-gray-500'
                  }`}>
                    {meta.label}
                  </div>
                  <div className="text-[9px] text-gray-600 mt-0.5">{meta.ieee}</div>

                  {/* Word progress bar */}
                  {isReady && (
                    <WordBar count={wc} min={meta.min} max={meta.max} />
                  )}
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Footer: overall progress */}
      <div className="px-4 py-3 border-t border-gray-800 shrink-0">
        <div className="text-[9px] text-gray-600 uppercase tracking-widest mb-1.5">
          {approvedKeys.size} / {SECTION_ORDER.length} approved
        </div>
        <div className="h-1 w-full bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-emerald-500 transition-all duration-700"
            style={{ width: `${(approvedKeys.size / SECTION_ORDER.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
