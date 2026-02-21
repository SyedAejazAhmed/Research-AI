import React from 'react';
import { motion } from 'framer-motion';

const ResearchMap = ({ agents }) => {
    const nodes = [
        { id: 'planner', x: 0, y: -140, label: 'Orchestrator' },
        { id: 'web_agent', x: -120, y: -40, label: 'Web Cluster' },
        { id: 'academic_agent', x: 120, y: -40, label: 'Academic Nodes' },
        { id: 'aggregator', x: 0, y: 40, label: 'Data Fusion' },
        { id: 'synthesizer', x: 0, y: 140, label: 'Neural Synthesis' },
        { id: 'publisher', x: 140, y: 140, label: 'Publication' }
    ];

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return '#10b981';
            case 'active': return '#6366f1';
            case 'error': return '#ef4444';
            default: return 'rgba(255,255,255,0.05)';
        }
    };

    const getStatusShadow = (status) => {
        switch (status) {
            case 'completed': return '0 0 40px rgba(16, 185, 129, 0.4)';
            case 'active': return '0 0 40px rgba(99, 102, 241, 0.6)';
            default: return 'none';
        }
    };

    return (
        <div className="relative w-full h-full flex items-center justify-center overflow-visible">
            <svg width="100%" height="100%" viewBox="-250 -250 500 500" className="absolute" style={{ pointerEvents: 'none' }}>
                <defs>
                    <linearGradient id="line-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.2" />
                        <stop offset="100%" stopColor="var(--secondary)" stopOpacity="0.2" />
                    </linearGradient>
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>

                {/* Connection Paths */}
                <motion.path
                    d="M 0 -140 L -120 -40 L 0 40 L 0 140"
                    fill="none"
                    stroke="url(#line-grad)"
                    strokeWidth="3"
                    strokeDasharray="10, 10"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />
                <motion.path
                    d="M 0 -140 L 120 -40 L 0 40"
                    fill="none"
                    stroke="url(#line-grad)"
                    strokeWidth="3"
                    strokeDasharray="10, 10"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear", delay: 1 }}
                />
                <motion.line
                    x1="0" y1="140" x2="140" y2="140"
                    stroke="url(#line-grad)"
                    strokeWidth="3"
                    strokeDasharray="10, 10"
                />
            </svg>

            {nodes.map((node, i) => {
                const agent = agents[node.id] || { status: 'pending' };
                const isActive = agent.status === 'active';
                const isCompleted = agent.status === 'completed';

                return (
                    <motion.div
                        key={node.id}
                        className={`absolute flex flex-col items-center justify-center transition-all duration-700`}
                        style={{
                            left: `calc(50% + ${node.x}px)`,
                            top: `calc(50% + ${node.y}px)`,
                            transform: 'translate(-50%, -50%)',
                        }}
                    >
                        <motion.div
                            className={`w-20 h-20 rounded-3xl backdrop-blur-3xl flex items-center justify-center text-2xl border-2 z-10`}
                            style={{
                                backgroundColor: isCompleted ? 'rgba(16, 185, 129, 0.2)' : isActive ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.03)',
                                borderColor: getStatusColor(agent.status),
                                boxShadow: getStatusShadow(agent.status),
                            }}
                            initial={{ scale: 0, opacity: 0, rotate: -45 }}
                            animate={{ scale: 1, opacity: 1, rotate: 0 }}
                            transition={{ delay: i * 0.1, type: 'spring', damping: 12 }}
                            whileHover={{ scale: 1.15, rotate: 5 }}
                        >
                            {isCompleted ? (
                                <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} className="text-success text-3xl font-bold">✓</motion.span>
                            ) : (
                                <span className={isActive ? 'animate-pulse text-primary' : 'text-slate-600'}>
                                    {agents[node.id]?.icon || '01'}
                                </span>
                            )}

                            {isActive && (
                                <motion.div
                                    className="absolute inset-0 rounded-3xl border-2 border-primary"
                                    animate={{ scale: [1, 1.3, 1], opacity: [1, 0, 1] }}
                                    transition={{ duration: 2, repeat: Infinity }}
                                />
                            )}
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="mt-4 text-center"
                        >
                            <p className={`text-[10px] font-black uppercase tracking-[0.2em] ${isActive ? 'text-primary' : 'text-slate-500'}`}>
                                {node.label}
                            </p>
                            {agent.message && (isActive || isCompleted) && (
                                <p className="text-[8px] text-slate-400 mt-1 max-w-[100px] leading-tight truncate">
                                    {agent.message}
                                </p>
                            )}
                        </motion.div>
                    </motion.div>
                );
            })}
        </div>
    );
};

export default ResearchMap;
