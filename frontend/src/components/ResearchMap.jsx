import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Vertical step-by-step pipeline that shows exactly what each backend agent
 * is doing in real time. Replaces the old icon-bubble diagram.
 */

const PIPELINE_STEPS = [
    { id: 'orchestrator', label: 'Orchestrator', desc: 'Coordinates all agents' },
    { id: 'planner', label: 'Planner Agent', desc: 'Breaks query into sub-questions & plan' },
    { id: 'web_agent', label: 'Web Context Agent', desc: 'Searches DuckDuckGo for context' },
    { id: 'academic_agent', label: 'Academic Research', desc: 'ArXiv, PubMed, Semantic Scholar' },
    { id: 'doc_agent', label: 'Document Processor', desc: 'Ranks & filters sources' },
    { id: 'citation_agent', label: 'Citation Agent', desc: 'Validates DOIs, formats citations' },
    { id: 'aggregator', label: 'Content Aggregator', desc: 'Unifies dataset for synthesis' },
    { id: 'synthesizer', label: 'AI Synthesizer', desc: 'Local LLM report generation' },
    { id: 'publisher', label: 'Publisher', desc: 'Generates MD / HTML / PDF / LaTeX' },
];

const statusMeta = {
    pending:    { color: 'border-white/10 bg-white/[0.02]', dot: 'bg-slate-700', text: 'text-slate-600', badge: 'WAITING' },
    analyzing:  { color: 'border-amber-500/40 bg-amber-500/5', dot: 'bg-amber-400 animate-pulse', text: 'text-amber-300', badge: 'RUNNING' },
    active:     { color: 'border-primary/40 bg-primary/5', dot: 'bg-primary animate-pulse', text: 'text-primary', badge: 'RUNNING' },
    starting:   { color: 'border-blue-500/40 bg-blue-500/5', dot: 'bg-blue-400 animate-pulse', text: 'text-blue-300', badge: 'STARTING' },
    generating: { color: 'border-emerald-500/40 bg-emerald-500/5', dot: 'bg-emerald-400 animate-pulse', text: 'text-emerald-300', badge: 'GENERATING' },
    compiling:  { color: 'border-cyan-500/40 bg-cyan-500/5', dot: 'bg-cyan-400 animate-pulse', text: 'text-cyan-300', badge: 'COMPILING' },
    step:       { color: 'border-primary/40 bg-primary/5', dot: 'bg-primary animate-pulse', text: 'text-primary', badge: 'ACTIVE' },
    completed:  { color: 'border-emerald-500/30 bg-emerald-500/5', dot: 'bg-emerald-400', text: 'text-emerald-400', badge: 'DONE' },
    error:      { color: 'border-red-500/30 bg-red-500/5', dot: 'bg-red-400', text: 'text-red-400', badge: 'ERROR' },
};

const getMeta = (s) => statusMeta[s] || statusMeta.pending;

const ResearchMap = ({ agents, logs = [] }) => {
    const bottomRef = useRef(null);
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    // Group logs by agent
    const logsByAgent = {};
    logs.forEach(l => {
        if (!logsByAgent[l.agent]) logsByAgent[l.agent] = [];
        logsByAgent[l.agent].push(l);
    });

    return (
        <div className="w-full flex flex-col gap-1 relative">
            {/* Vertical connector line */}
            <div className="absolute left-[19px] top-8 bottom-8 w-[2px] bg-gradient-to-b from-primary/20 via-white/5 to-emerald-500/20 z-0" />

            {PIPELINE_STEPS.map((step, i) => {
                const agent = agents[step.id] || { status: 'pending', message: '' };
                const meta = getMeta(agent.status);
                const agentLogs = logsByAgent[step.id] || [];
                const isIdle = agent.status === 'pending';
                const isDone = agent.status === 'completed';

                return (
                    <motion.div
                        key={step.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.04 }}
                        className="relative z-10"
                    >
                        {/* Step row */}
                        <div className={`flex items-start gap-4 px-3 py-3 rounded-2xl border transition-all duration-500 ${meta.color}`}>
                            {/* Status dot + index */}
                            <div className="flex flex-col items-center gap-1 pt-0.5">
                                <div className={`w-[10px] h-[10px] rounded-full shrink-0 ${meta.dot}`} />
                                <span className="text-[8px] font-mono text-slate-600">{String(i + 1).padStart(2, '0')}</span>
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-0.5">
                                    <span className={`text-xs font-black uppercase tracking-widest ${isIdle ? 'text-slate-600' : meta.text}`}>
                                        {step.label}
                                    </span>
                                    {!isIdle && (
                                        <span className={`text-[8px] font-black tracking-widest px-2 py-0.5 rounded-full ${
                                            isDone ? 'bg-emerald-500/20 text-emerald-400'
                                                : agent.status === 'error' ? 'bg-red-500/20 text-red-400'
                                                : 'bg-primary/20 text-primary'
                                        }`}>
                                            {meta.badge}
                                        </span>
                                    )}
                                </div>

                                {/* Description / current message */}
                                <p className="text-[10px] text-slate-500 leading-relaxed">
                                    {agent.message
                                        ? (agent.message.split('. Plan:')[0])
                                        : step.desc}
                                </p>

                                {/* Sub-log entries (collapsed to last 4) */}
                                <AnimatePresence>
                                    {agentLogs.length > 0 && !isIdle && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="mt-2 space-y-0.5 overflow-hidden"
                                        >
                                            {agentLogs.slice(-4).map((entry, j) => {
                                                const time = entry.timestamp
                                                    ? new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                                                    : '';
                                                const displayMsg = (entry.message || '').split('. Plan:')[0];
                                                return (
                                                    <motion.div
                                                        key={j}
                                                        initial={{ opacity: 0, y: 4 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        className="flex items-center gap-2 font-mono text-[9px] text-slate-500"
                                                    >
                                                        <span className="text-slate-700 w-14 shrink-0">{time}</span>
                                                        <span className="truncate">{displayMsg}</span>
                                                    </motion.div>
                                                );
                                            })}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Completion / spinner indicator */}
                            <div className="shrink-0 pt-0.5">
                                {isDone && (
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        className="w-7 h-7 rounded-lg bg-emerald-500/20 flex items-center justify-center"
                                    >
                                        <span className="text-emerald-400 text-sm font-bold">✓</span>
                                    </motion.div>
                                )}
                                {(!isIdle && !isDone && agent.status !== 'error') && (
                                    <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
                                        <motion.div
                                            className="w-3 h-3 rounded-full border-2 border-primary border-t-transparent"
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    </motion.div>
                );
            })}
            <div ref={bottomRef} />
        </div>
    );
};

export default ResearchMap;
