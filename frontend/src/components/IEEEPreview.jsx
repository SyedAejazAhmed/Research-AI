/**
 * IEEEPreview.jsx
 *
 * Exact PDF preview panel.
 * - Starts as a blank paper canvas
 * - Auto-compiles partial PDF as sections arrive
 * - Renders only real compiled PDF output (no simulated draft)
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Download, Eye, EyeOff, Loader2 } from 'lucide-react';
import { SECTION_ORDER, SECTION_META } from './SectionSidebar';

export default function IEEEPreview({
  sections,       // [{key, title, content}]
  editValues,     // {[key]: string}
  plan,           // {title, query, keywords}
  sessionId,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [compiling, setCompiling] = useState(false);
  const [compileResult, setCompileResult] = useState(null);
  const [pdfVersion, setPdfVersion] = useState(0);
  const debounceRef = useRef(null);
  const lastCompiledSignatureRef = useRef('');

  const paperTitle  = plan?.title || plan?.query || 'Research Paper';
  const previewPdfUrl = compileResult?.preview_pdf || compileResult?.download_pdf || null;
  const downloadPdfUrl = compileResult?.download_pdf || null;

  const abstractText = useMemo(() => {
    const absSec = sections.find(s => s.key === 'abstract');
    return (editValues?.abstract ?? absSec?.content ?? '').trim();
  }, [sections, editValues]);

  const bodySections = useMemo(() => (
    SECTION_ORDER
      .filter(k => k !== 'abstract')
      .map(k => {
        const sec = sections.find(s => s.key === k);
        if (!sec) return null;
        return {
          title: SECTION_META[k]?.label || k,
          content: (editValues?.[k] ?? sec.content ?? '').trim(),
        };
      })
      .filter(Boolean)
      .filter(s => s.content.length > 0)
  ), [sections, editValues]);

  const hasRenderableContent = abstractText.length > 0 || bodySections.length > 0;
  const compileSignature = useMemo(() => JSON.stringify({
    t: paperTitle,
    a: abstractText,
    b: bodySections,
  }), [paperTitle, abstractText, bodySections]);

  async function compileCurrentContent() {
    if (!hasRenderableContent) return;
    setCompiling(true);
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
      if (data?.status === 'success' && data?.download_pdf) {
        setPdfVersion(v => v + 1);
        lastCompiledSignatureRef.current = compileSignature;
      }
    } catch (err) {
      setCompileResult({ error: String(err) });
    } finally {
      setCompiling(false);
    }
  }

  function handleGeneratePDF() {
    compileCurrentContent();
  }

  useEffect(() => {
    if (!hasRenderableContent) return;
    if (compileSignature === lastCompiledSignatureRef.current) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      compileCurrentContent();
    }, 1200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [compileSignature, hasRenderableContent]);

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
    <div className="w-[32rem] max-w-[46vw] min-w-[26rem] flex flex-col bg-gray-950 border-l border-gray-800 shrink-0">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-black uppercase tracking-widest text-gray-500">PDF Preview</span>
          <span className="text-[8px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded font-bold">EXACT</span>
        </div>
        <button onClick={() => setCollapsed(true)} className="p-1 hover:bg-gray-800 rounded transition-colors text-gray-600 hover:text-gray-300">
          <EyeOff size={13} />
        </button>
      </div>

      {/* Exact PDF render */}
      <div className="flex-1 overflow-y-auto px-2 py-2 bg-gray-900/50">
        <div className="mx-1 my-1 h-full rounded-lg overflow-hidden border border-gray-700 bg-black/20">
          {previewPdfUrl ? (
            <iframe
              key={`${previewPdfUrl}-${pdfVersion}`}
              title="Generated PDF Preview"
              src={`${previewPdfUrl}#toolbar=0&navpanes=0&view=FitH`}
              className="w-full h-full"
            />
          ) : (
            <div className="h-full flex items-center justify-center p-4">
              <div className="bg-white rounded-md border border-gray-300 w-full max-w-[19rem] aspect-[210/297] shadow-sm flex items-center justify-center text-center px-5 text-[11px] text-gray-500" style={{ fontFamily: '"Times New Roman", serif' }}>
                Blank page preview. As each section is generated, the PDF will compile automatically and appear here.
              </div>
            </div>
          )}
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
            {previewPdfUrl && (
              <a href={previewPdfUrl} target="_blank" rel="noreferrer"
                className="flex-1 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-[10px] text-center font-bold transition-colors">
                Open PDF
              </a>
            )}
            {downloadPdfUrl && (
              <a href={downloadPdfUrl} download
                className="flex-1 py-1.5 rounded-lg bg-violet-700 hover:bg-violet-600 text-white text-[10px] text-center font-bold transition-colors">
                Download PDF
              </a>
            )}
          </div>
        )}

        <div className="text-[9px] text-gray-500 text-center">
          Auto-compiles as new sections arrive and shows exact PDF output.
        </div>
      </div>

    </div>
  );
}
