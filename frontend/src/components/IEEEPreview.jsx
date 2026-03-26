/**
 * IEEEPreview.jsx
 *
 * Live IEEE-style paper preview panel.
 * Shows all sections in IEEE format as they are generated + edited.
 *
 * Features:
 *  - IEEE two-column paper look (simulated with CSS)
 *  - Title / Author / Abstract / numbered sections
 *  - Active section highlighted with violet ring
 *  - Word-count summary
 */
import { useState } from 'react';
import { Download, Eye, EyeOff, Loader2 } from 'lucide-react';
import { SECTION_ORDER, SECTION_META } from './SectionSidebar';

function wordCount(text = '') {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

// Strip markdown bold/italic markers for plain preview
function stripMd(text = '') {
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`(.*?)`/g, '$1')
    .replace(/#{1,6}\s?/g, '')
    .trim();
}

function toRoman(n) {
  const map = [
    [1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'],
    [100, 'C'], [90, 'XC'], [50, 'L'], [40, 'XL'],
    [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I'],
  ];
  let x = n;
  let out = '';
  for (const [v, sym] of map) {
    while (x >= v) {
      out += sym;
      x -= v;
    }
  }
  return out;
}

export default function IEEEPreview({
  sections,       // [{key, title, content}]
  editValues,     // {[key]: string}
  activeKey,
  plan,           // {title, query, keywords}
  approvedKeys,   // Set<string>
  sessionId,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [compiling, setCompiling] = useState(false);
  const [compileResult, setCompileResult] = useState(null);

  const paperTitle  = plan?.title || plan?.query || 'Research Paper';
  const paperDate   = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long' });

  async function handleGeneratePDF() {
    const abstractSec = sections.find(s => s.key === 'abstract');
    const abstractText = editValues?.['abstract'] ?? abstractSec?.content ?? '';

    const bodySections = SECTION_ORDER
      .filter(k => k !== 'abstract')
      .map(k => {
        const sec = sections.find(s => s.key === k);
        if (!sec) return null;
        return {
          title: SECTION_META[k]?.label || k,
          content: editValues?.[k] ?? sec.content,
        };
      })
      .filter(Boolean);

    setCompiling(true);
    setCompileResult(null);
    try {
      const res = await fetch('/api/write/partial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: paperTitle,
          abstract: abstractText,
          sections: bodySections,
          citations: {},
          compile_pdf: true,
          template: 'article',
          author: 'Yukti Research AI',
          session_id: sessionId || '',
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

  // ── Collapsed state ────────────────────────────────────────────────────
  if (collapsed) {
    return (
      <div className="w-10 bg-gray-950 border-l border-gray-800 flex flex-col items-center py-4 gap-4">
        <button onClick={() => setCollapsed(false)} className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-500 hover:text-gray-200">
          <Eye size={16} />
        </button>
        <div style={{ writingMode: 'vertical-rl' }} className="text-[9px] uppercase tracking-widest text-gray-600 rotate-180 mt-2">
          IEEE Preview
        </div>
      </div>
    );
  }

  // ── Full preview ───────────────────────────────────────────────────────
  return (
    <div className="w-80 flex flex-col bg-gray-950 border-l border-gray-800 shrink-0">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-black uppercase tracking-widest text-gray-500">IEEE Preview</span>
          <span className="text-[8px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded font-bold">LIVE</span>
        </div>
        <button onClick={() => setCollapsed(true)} className="p-1 hover:bg-gray-800 rounded transition-colors text-gray-600 hover:text-gray-300">
          <EyeOff size={13} />
        </button>
      </div>

      {/* Paper render */}
      <div className="flex-1 overflow-y-auto px-1 py-2">
        <div className="bg-white rounded-lg mx-2 my-1 p-4 text-gray-900" style={{ fontFamily: '"Times New Roman", serif' }}>

          {/* IEEE Title block */}
          <div className="text-center mb-3 pb-2 border-b border-gray-300">
            <h1 style={{ fontSize: '13px', fontWeight: 'bold', lineHeight: '1.3' }} className="mb-1">
              {paperTitle}
            </h1>
            <div style={{ fontSize: '10px' }} className="text-gray-600">
              Yukti Research AI &nbsp;•&nbsp; {paperDate}
            </div>
          </div>

          {/* Abstract */}
          {(() => {
            const absSec = sections.find(s => s.key === 'abstract');
            if (!absSec) return null;
            const content = editValues?.['abstract'] ?? absSec.content;
            return (
              <div
                className={`mb-3 rounded transition-all ${activeKey === 'abstract' ? 'ring-2 ring-violet-400 ring-offset-1 ring-offset-white' : ''}`}
              >
                <div style={{ fontSize: '9px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.08em' }} className="mb-1">
                  Abstract
                </div>
                <p style={{ fontSize: '9px', lineHeight: '1.5', fontStyle: 'italic' }}>
                  {stripMd(content).slice(0, 600)}
                  {content.length > 600 ? '…' : ''}
                </p>
              </div>
            );
          })()}

          {/* IEEE rule */}
          <hr className="border-gray-400 mb-2" style={{ borderTopWidth: '2px', borderBottomWidth: '1px' }} />

          {/* Body sections in two-column layout */}
          <div style={{ columnCount: 2, columnGap: '12px' }}>
            {SECTION_ORDER.filter(k => k !== 'abstract' && k !== 'references').map((key, idx) => {
              const sec = sections.find(s => s.key === key);
              if (!sec) return null;
              const content   = editValues?.[key] ?? sec.content;
              const isActive  = activeKey === key;
              const meta      = SECTION_META[key];
              const wc        = wordCount(content);
              const ok        = wc >= meta.min && wc <= meta.max;

              return (
                <div
                  key={key}
                  style={{ breakInside: 'avoid', marginBottom: '6px' }}
                  className={`rounded transition-all ${isActive ? 'ring-2 ring-violet-400 ring-offset-1 ring-offset-white' : ''}`}
                >
                  <div style={{ fontSize: '9px', fontWeight: 'bold', marginBottom: '2px' }}>
                    {/* Roman numeral */}
                    {toRoman(idx + 1)}. {meta.label.toUpperCase()}
                    {approvedKeys.has(key) && (
                      <span className="ml-1 text-emerald-600">✓</span>
                    )}
                  </div>
                  <p style={{ fontSize: '8.5px', lineHeight: '1.4', textAlign: 'justify' }}>
                    {stripMd(content).slice(0, 400)}
                    {content.length > 400 ? '…' : ''}
                  </p>
                  {/* Word count tag */}
                  <div style={{ fontSize: '7px', marginTop: '2px' }} className={ok ? 'text-emerald-600' : 'text-amber-600'}>
                    {wc} words
                  </div>
                </div>
              );
            })}
          </div>

          {/* References preview */}
          {(() => {
            const refSec = sections.find(s => s.key === 'references');
            if (!refSec) return null;
            const refContent = (editValues?.references ?? refSec.content ?? '').trim();
            if (!refContent) return null;

            return (
              <div className={`mt-3 rounded transition-all ${activeKey === 'references' ? 'ring-2 ring-violet-400 ring-offset-1 ring-offset-white' : ''}`}>
                <div style={{ fontSize: '9px', fontWeight: 'bold', marginBottom: '4px' }}>
                  REFERENCES
                  {approvedKeys.has('references') && (
                    <span className="ml-1 text-emerald-600">✓</span>
                  )}
                </div>
                <pre style={{ fontSize: '8px', lineHeight: '1.35', whiteSpace: 'pre-wrap', fontFamily: '"Times New Roman", serif' }}>
                  {stripMd(refContent).slice(0, 1400)}
                  {refContent.length > 1400 ? '\n…' : ''}
                </pre>
              </div>
            );
          })()}
        </div>
      </div>

      {/* Generate PDF */}
      <div className="shrink-0 px-4 py-3 border-t border-gray-800 flex flex-col gap-2">
        <button
          onClick={handleGeneratePDF}
          disabled={compiling || sections.length === 0}
          className="w-full py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {compiling
            ? <><Loader2 size={13} className="animate-spin" /> Compiling...</>
            : <><Download size={13} /> Generate IEEE PDF</>}
        </button>

        {compileResult?.error && (
          <p className="text-xs text-red-400">{compileResult.error}</p>
        )}
        {!compileResult?.error && compileResult?.status === 'success' && (
          <div className="flex gap-2 flex-wrap">
            {compileResult.download_tex && (
              <a href={compileResult.download_tex} target="_blank" rel="noreferrer"
                className="flex-1 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-[10px] text-center transition-colors">
                .tex
              </a>
            )}
            {compileResult.download_pdf && (
              <a href={compileResult.download_pdf} target="_blank" rel="noreferrer"
                className="flex-1 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-[10px] text-center font-bold transition-colors">
                PDF
              </a>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
