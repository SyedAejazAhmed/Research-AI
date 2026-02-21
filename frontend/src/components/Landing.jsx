import { motion } from 'framer-motion';
import { Sparkles, Brain, Search, Shield, Zap, Globe, BookOpen, ChevronRight, Share2, GraduationCap, Layers, Cpu, Database, CheckCircle2, Terminal, Code } from 'lucide-react';
import DarkVeil from './DarkVeil';
import PixelSnow from './PixelSnow';
import GradientText from './GradientText';

const FeatureCard = ({ icon: Icon, title, description, delay = 0 }) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay }}
        className="glass-card p-8 group hover:border-primary/50 transition-all duration-500"
    >
        <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-6 group-hover:scale-110 group-hover:bg-primary group-hover:text-white transition-all">
            <Icon size={24} />
        </div>
        <h3 className="text-xl font-black font-outfit mb-4">{title}</h3>
        <p className="text-slate-400 font-light leading-relaxed text-sm">{description}</p>
    </motion.div>
);

const Landing = ({ onStart, onAuth }) => {
    return (
        <div className="min-h-screen relative overflow-x-hidden pt-20">
            {/* Background Mask */}
            <div className="fixed inset-0 -z-20 pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/50 to-background" />
            </div>

            {/* Hero Section */}
            <section className="relative min-h-[95vh] flex flex-col items-center justify-center p-6 text-center overflow-hidden">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/20 blur-[180px] -z-10 animate-pulse-slow" />

                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mb-10"
                >
                    <div className="inline-flex items-center gap-3 px-6 py-2 rounded-full border border-primary/30 bg-primary/10 text-[11px] font-black uppercase tracking-[0.4em] text-primary shadow-2xl shadow-primary/20 backdrop-blur-md">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                        </span>
                        CORE_ENGINE v4.0 Active
                    </div>
                </motion.div>

                <GradientText
                    colors={["#6366f1", "#a855f7", "#22d3ee", "#6366f1"]}
                    animationSpeed={8}
                    showBorder={false}
                    className="text-8xl md:text-[11.5rem] font-black tracking-tighter leading-[0.8] font-outfit mb-10 drop-shadow-[0_0_50px_rgba(99,102,241,0.2)]"
                >
                    YUKTI.AI
                </GradientText>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-xl md:text-2xl text-slate-400 max-w-3xl font-light leading-relaxed font-outfit mb-14 px-4"
                >
                    An <span className="text-white font-medium italic underline decoration-primary/50 underline-offset-8">Autonomous Research Machine</span> engineered to decode high-density complexity with absolute academic transparency.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="flex flex-col sm:flex-row items-center justify-center gap-6"
                >
                    <button
                        onClick={onStart}
                        className="group relative px-10 py-5 rounded-[2rem] bg-white text-slate-950 font-black text-xl flex items-center gap-4 hover:bg-primary hover:text-white hover:scale-105 active:scale-95 transition-all duration-300 shadow-[0_0_50px_rgba(255,255,255,0.2)] overflow-hidden"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                        Start Researching
                        <div className="p-2 rounded-xl bg-slate-900 text-white group-hover:bg-white group-hover:text-primary transition-all">
                            <Search size={22} className="group-hover:rotate-12 transition-transform" />
                        </div>
                    </button>
                    <button
                        onClick={onAuth}
                        className="group px-10 py-5 rounded-[2rem] border border-white/10 bg-white/5 backdrop-blur-3xl font-black text-xl text-white hover:bg-white/10 hover:border-white/20 transition-all flex items-center gap-4"
                    >
                        Access Dashboard
                        <div className="p-2 rounded-xl border border-white/10 text-white group-hover:border-primary/50 group-hover:text-primary transition-all">
                            <Shield size={22} />
                        </div>
                    </button>
                </motion.div>
            </section>

            {/* Core Capability Section */}
            <section className="py-32 px-6">
                <div className="container mx-auto max-w-7xl">
                    <div className="text-center mb-24">
                        <h2 className="text-5xl font-black font-outfit tracking-tighter mb-6">Neural Orchestration</h2>
                        <p className="text-slate-400 max-w-xl mx-auto font-light">
                            Yukti coordinates a cluster of 9 specialized AI agents to ensure every finding is cross-referenced and verified.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={Layers}
                            title="Strategic Planning"
                            description="PlannerAgent decomposes your query into logical sub-questions and research directives based on academic ontologies."
                            delay={0.1}
                        />
                        <FeatureCard
                            icon={Globe}
                            title="Global Synthesis"
                            description="Concurrent access to ArXiv, PubMed, and Semantic Scholar nodes for deep background context and source grounding."
                            delay={0.2}
                        />
                        <FeatureCard
                            icon={Shield}
                            title="Verified Citations"
                            description="Native DOI validation ensures zero hallucinations. All references are verified against real-world scientific databases."
                            delay={0.3}
                        />
                    </div>
                </div>
            </section>

            {/* High-Impact Workflow Section */}
            <section className="bg-slate-950/80 border-y border-white/5 py-32 px-6">
                <div className="container mx-auto max-w-7xl">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
                        <div>
                            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest border border-primary/20 mb-8">
                                The Pipeline
                            </div>
                            <h2 className="text-6xl font-black font-outfit tracking-tight mb-10 leading-[0.9]">Autonomous <br /><span className="text-gradient">Logic Flow.</span></h2>

                            <div className="space-y-10">
                                {[
                                    { step: '01', title: 'Contextual Ingestion', desc: 'Analyzing the root query using deep language models to understand intent and scope.' },
                                    { step: '02', title: 'Multi-Node Research', desc: 'Deploying agents to academic and web clusters simultaneously to gather raw intelligence.' },
                                    { step: '03', title: 'Synthesis & Proofing', desc: 'Aggregating findings into a cohesive narrative with algorithmic cross-validation.' }
                                ].map(item => (
                                    <div key={item.step} className="flex gap-6">
                                        <div className="text-4xl font-black text-white/10 font-outfit">{item.step}</div>
                                        <div>
                                            <h4 className="text-xl font-bold mb-2">{item.title}</h4>
                                            <p className="text-slate-400 font-light leading-relaxed text-sm">{item.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="relative">
                            <div className="absolute -inset-10 bg-primary/20 blur-[100px] rounded-full" />
                            <div className="glass-card p-4 relative bg-slate-900/40 backdrop-blur-3xl border border-white/10 rounded-3xl group">
                                <div className="flex items-center gap-3 p-4 border-b border-white/5">
                                    <div className="flex gap-1.5">
                                        <div className="w-2 h-2 rounded-full bg-red-400/50" />
                                        <div className="w-2 h-2 rounded-full bg-yellow-400/50" />
                                        <div className="w-2 h-2 rounded-full bg-green-400/50" />
                                    </div>
                                    <div className="text-[10px] font-black text-slate-500 tracking-[0.2em] uppercase">SYSTEM_CORE: RESEARCH_LIVE</div>
                                </div>
                                <div className="p-8 font-mono text-xs text-primary/80 space-y-4">
                                    <p className="flex items-center gap-3"><ChevronRight size={14} /> INITIALIZING PLANNER_AGENT...</p>
                                    <p className="flex items-center gap-3 text-white/40"><ChevronRight size={14} /> SCANNING ARXIV CLUSTER (12 NODES)...</p>
                                    <p className="flex items-center gap-3"><ChevronRight size={14} /> EXTRACTING SEMANTIC ENTITIES...</p>
                                    <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: '70%' }}
                                            transition={{ duration: 2, repeat: Infinity }}
                                            className="h-full bg-primary shadow-[0_0_15px_#6366f1]"
                                        />
                                    </div>
                                    <p className="text-emerald-400 tracking-widest animate-pulse">&gt; SYNTHESIS_COMPLETE: READY_FOR_RENDER</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Philosophy Section */}
            <section className="py-48 px-6 relative overflow-hidden bg-slate-950/20 backdrop-blur-sm">
                <div className="container mx-auto max-w-7xl">
                    <motion.div
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        className="grid grid-cols-1 lg:grid-cols-12 gap-20 items-stretch"
                    >
                        <div className="lg:col-span-4 flex flex-col justify-center">
                            <div className="flex items-center gap-4 mb-10">
                                <div className="p-3 rounded-2xl bg-primary/10 text-primary border border-primary/20">
                                    <Brain size={24} />
                                </div>
                                <div className="h-px flex-1 bg-gradient-to-r from-primary/20 to-transparent" />
                            </div>
                            <h2 className="text-7xl font-black font-outfit tracking-tighter leading-none mb-10">युति: <br />Synthesis <br /><span className="text-gradient">Logic.</span></h2>
                            <p className="text-lg text-slate-400 font-light leading-relaxed mb-10">
                                Derived from the Sanskrit word for "Union", Yukti is built on the hypothesis that research shouldn't be a search for data, but a synthesis of truth.
                            </p>
                            <div className="p-8 rounded-[2rem] bg-white/[0.02] border border-white/5 relative group">
                                <div className="absolute top-0 left-0 w-1 h-full bg-primary rounded-full transition-all group-hover:w-2" />
                                <p className="text-sm font-bold italic text-white/50 mb-4 leading-relaxed italic">"To research is to see what everyone else has seen, and to think what nobody else has thought."</p>
                                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-primary">Project Vision v4.0</span>
                            </div>
                        </div>

                        <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                            {[
                                { title: 'Semantic Core', desc: 'Understanding ontological relationships between academic concepts.', icon: Brain, color: 'text-blue-400' },
                                { title: 'Hallucination Shield', desc: 'Claims are traceably linked to verified academic publications.', icon: Shield, color: 'text-emerald-400' },
                                { title: 'Agent Swarm', desc: 'Parallel execution across multiple cloud nodes for extreme speed.', icon: Zap, color: 'text-amber-400' },
                                { title: 'Open Knowledge', desc: 'Built to democratize high-end intelligence for researchers.', icon: BookOpen, color: 'text-purple-400' }
                            ].map((item, idx) => (
                                <motion.div
                                    key={idx}
                                    initial={{ opacity: 0, y: 30 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: idx * 0.1 }}
                                    className="p-10 rounded-[2.5rem] bg-white/[0.02] border border-white/5 hover:border-white/10 hover:bg-white/[0.04] transition-all group flex flex-col gap-6"
                                >
                                    <div className={`p-4 w-fit rounded-2xl bg-white/5 ${item.color} group-hover:scale-110 transition-transform`}>
                                        <item.icon size={28} />
                                    </div>
                                    <div>
                                        <h4 className="text-xl font-black mb-3">{item.title}</h4>
                                        <p className="text-sm text-slate-400 font-light leading-relaxed">{item.desc}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                </div>
            </section>

            <section className="py-48 px-6 relative">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-primary/10 blur-[150px] -z-10" />

                <div className="container mx-auto max-w-7xl">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 lg:gap-24 items-center">
                        {/* Visualizer Side */}
                        <div className="lg:col-span-7 order-2 lg:order-1 relative rounded-[2rem] overflow-hidden shadow-[0_0_100px_rgba(0,0,0,0.4)] border border-white/5 group bg-slate-900/40 backdrop-blur-3xl">
                            <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950 to-transparent z-10" />
                            <div className="absolute inset-x-0 top-0 h-20 bg-gradient-to-b from-slate-950/50 to-transparent z-10" />

                            <div style={{ width: '100%', height: '540px', position: 'relative' }}>
                                <PixelSnow
                                    density={0.35}
                                    speed={0.8}
                                />
                            </div>

                            <div className="absolute bottom-10 left-10 z-20 flex flex-col gap-2">
                                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 backdrop-blur-2xl text-[10px] font-black uppercase tracking-[0.2em] text-white border border-white/10 shadow-2xl">
                                    <Sparkles size={12} className="text-primary" /> Core Mechanism: Atmospheric Depth
                                </div>
                                <p className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500 ml-1">Visualization Instance v1.0.4</p>
                            </div>

                            {/* Geometric Accent */}
                            <div className="absolute top-10 right-10 w-12 h-12 border-t-2 border-r-2 border-white/10 rounded-tr-2xl group-hover:border-primary/40 transition-colors" />
                        </div>

                        {/* Content Side */}
                        <div className="lg:col-span-5 order-1 lg:order-2">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-[9px] font-black uppercase tracking-widest border border-primary/20 mb-8">
                                Visual Intelligence
                            </div>
                            <h2 className="text-6xl font-black font-outfit tracking-tighter mb-8 leading-[0.9]">Clarity through <br /><span className="text-gradient">Depth.</span></h2>
                            <p className="text-lg text-slate-400 font-light leading-relaxed mb-12">
                                Yukti processes mathematical noise into actionable research signal. Our visualization engine maps high-dimensional search nodes into a navigatable volumetric space.
                            </p>

                            <div className="grid grid-cols-1 gap-4">
                                {[
                                    { title: 'Dynamic Resolution', desc: 'Adapting node density to your search scope.', icon: Search },
                                    { title: 'Volumetric Depth', desc: 'Stereoscopic analysis of interconnected nodes.', icon: Layers }
                                ].map(i => (
                                    <motion.div
                                        key={i.title}
                                        whileHover={{ x: 8 }}
                                        className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 flex gap-5 items-center group/item hover:bg-white/[0.05] transition-all"
                                    >
                                        <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover/item:bg-primary group-hover/item:text-white transition-all">
                                            <i.icon size={20} />
                                        </div>
                                        <div>
                                            <h4 className="font-black text-sm text-white uppercase tracking-tight">{i.title}</h4>
                                            <p className="text-xs text-slate-500 font-light">{i.desc}</p>
                                        </div>
                                        <ChevronRight className="ml-auto text-slate-700 group-hover/item:text-primary transition-colors" size={16} />
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Presentation Meta Section */}
            <section className="py-32 px-6 relative overflow-hidden">
                <div className="container mx-auto max-w-7xl text-center">
                    <h2 className="text-4xl font-black font-outfit mb-20">The Technology Stack</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 opacity-40 hover:opacity-100 transition-opacity">
                        {[
                            { icon: Terminal, name: 'FASTAPI BACKEND' },
                            { icon: Database, name: 'LOCAL OLLAMA NODES' },
                            { icon: Code, name: 'REACT FRAMEWORK' },
                            { icon: Cpu, name: 'MULTI-AGENT ARCH' }
                        ].map(tech => (
                            <div key={tech.name} className="flex flex-col items-center gap-4 grayscale hover:grayscale-0 transition-all">
                                <tech.icon size={32} />
                                <span className="text-[10px] font-black tracking-widest uppercase">{tech.name}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-20 text-center relative border-t border-white/5 bg-slate-950/50">
                <div className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-500">
                    TEAM DART VADAR &bull; ST. JOSEPH'S COLLEGE OF ENGINEERING &bull; PROTOTHON 2026
                </div>
                <div className="mt-8 flex justify-center gap-8 opacity-40">
                    <GraduationCap size={20} />
                    <Brain size={20} />
                    <Shield size={20} />
                </div>
            </footer>
        </div>
    );
};

export default Landing;
