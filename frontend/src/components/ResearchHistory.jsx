import { motion } from 'framer-motion';
import { Clock, ChevronRight, FileText, Calendar } from 'lucide-react';

const ResearchHistory = ({ sessions, onSelect, activeSessionId }) => {
    return (
        <div className="flex flex-col gap-6 h-full overflow-hidden">
            <div className="flex items-center justify-between px-2">
                <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                    <Clock size={14} className="text-primary" /> Past Creations
                </h3>
                <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded-full border border-white/10 text-slate-500">
                    {Object.keys(sessions).length}
                </span>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
                {Object.entries(sessions)
                    .sort((a, b) => new Date(b[1].started_at) - new Date(a[1].started_at))
                    .map(([id, session]) => (
                        <motion.button
                            key={id}
                            whileHover={{ x: 4 }}
                            onClick={() => onSelect(id)}
                            className={`w-full text-left p-4 rounded-2xl border transition-all group ${activeSessionId === id
                                ? 'bg-primary/20 border-primary/40 shadow-lg shadow-primary/5'
                                : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/20'
                                }`}
                        >
                            <div className="flex items-center gap-3 mb-2">
                                <div className={`p-2 rounded-lg ${activeSessionId === id ? 'bg-primary text-white' : 'bg-slate-800 text-slate-500'}`}>
                                    <FileText size={14} />
                                </div>
                                <p className="text-[11px] font-black uppercase tracking-widest text-slate-400 group-hover:text-white transition-colors truncate">
                                    {session.status === 'completed' ? 'Verified Paper' : 'Processing...'}
                                </p>
                            </div>

                            <p className="text-xs font-medium text-slate-200 line-clamp-2 mb-3 leading-relaxed">
                                {session.query}
                            </p>

                            <div className="flex items-center justify-between mt-auto opacity-40 group-hover:opacity-100 transition-opacity">
                                <div className="flex items-center gap-1.5 text-[9px] font-bold">
                                    <Calendar size={10} />
                                    {new Date(session.started_at).toLocaleDateString()}
                                </div>
                                <ChevronRight size={12} className={activeSessionId === id ? 'text-primary' : ''} />
                            </div>
                        </motion.button>
                    ))}

                {Object.keys(sessions).length === 0 && (
                    <div className="h-40 flex flex-col items-center justify-center text-center opacity-30 px-4">
                        <Clock size={32} className="mb-4" />
                        <p className="text-xs font-medium">Your research vault is empty. Ignite your first query to begin.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ResearchHistory;
