import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Lock, Mail, ChevronRight, ArrowLeft, ShieldCheck, Globe, Linkedin, Sparkles } from 'lucide-react';

const Auth = ({ onLogin, onBack }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [formData, setFormData] = useState({ name: '', email: '', password: '' });
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        // Accept any email/password — no strict authentication required
        setTimeout(() => {
            const displayName = formData.name || formData.email.split('@')[0] || 'Scholar';
            onLogin({
                status: 'success',
                user: {
                    name: displayName,
                    email: formData.email,
                    role: 'academic'
                },
                token: 'session-' + Date.now()
            });
            setIsLoading(false);
        }, 600);
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Decorative Blobs */}
            <div className="absolute top-0 left-0 w-full h-full -z-10 bg-background">
                <div className="absolute top-1/2 left-1/4 w-[500px] h-[500px] bg-primary/20 blur-[150px] -translate-y-1/2" />
                <div className="absolute top-1/2 right-1/4 w-[500px] h-[500px] bg-secondary/20 blur-[150px] -translate-y-1/2" />
            </div>

            <motion.button
                onClick={onBack}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                whileHover={{ x: -4 }}
                className="absolute top-8 left-8 flex items-center gap-2 text-slate-500 hover:text-white transition-all text-xs font-black uppercase tracking-widest"
            >
                <ArrowLeft size={16} /> Return to hub
            </motion.button>

            <div className="flex w-full max-w-5xl h-[700px] glass-card overflow-hidden shadow-[0_0_100px_rgba(0,0,0,0.5)] border-white/5">
                {/* Left Side: Illustration & Branding */}
                <div className="hidden lg:flex flex-1 bg-primary relative p-16 flex-col justify-between overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-primary via-secondary to-accent opacity-80" />
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />

                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-3xl flex items-center justify-center mb-8">
                            <Sparkles className="text-white" />
                        </div>
                        <h2 className="text-6xl font-black font-outfit tracking-tighter text-white leading-none">
                            Decipher the <br />Unseen.
                        </h2>
                    </div>

                    <div className="relative z-10 space-y-6">
                        <blockquote className="text-xl font-light text-white/80 italic leading-relaxed">
                            "Yukti represents the paradigm shift in academic research where AI doesn't just assist, it orchestrates logic."
                        </blockquote>
                        <div className="flex items-center gap-4 border-t border-white/10 pt-6">
                            <div className="w-10 h-10 rounded-full bg-white/20" />
                            <div>
                                <p className="text-white font-bold text-sm">Team Dart Vadar</p>
                                <p className="text-white/40 text-[10px] uppercase font-black tracking-widest">Protocol Architects</p>
                            </div>
                        </div>
                    </div>

                    {/* Abstract Design Elements */}
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                        className="absolute -bottom-20 -right-20 w-80 h-80 border border-white/10 rounded-full flex items-center justify-center"
                    >
                        <div className="w-60 h-60 border border-white/5 rounded-full" />
                    </motion.div>
                </div>

                {/* Right Side: Form */}
                <div className="flex-1 bg-slate-950/20 backdrop-blur-3xl p-12 lg:p-16 flex flex-col justify-center relative">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={isLogin ? 'login' : 'register'}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.3 }}
                        >
                            <div className="mb-10">
                                <h3 className="text-3xl font-black font-outfit tracking-tight mb-2">
                                    {isLogin ? 'Academic Login' : 'Scholar Signup'}
                                </h3>
                                <p className="text-slate-400 text-sm font-light">
                                    {isLogin ? 'Access your research vault and creations.' : 'Join 2,000+ researchers globally.'}
                                </p>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                {!isLogin && (
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 ml-1">Full Name</label>
                                        <div className="relative group">
                                            <input
                                                type="text"
                                                required
                                                className="w-full bg-white/5 border border-white/10 rounded-xl py-4 pl-12 focus:border-primary focus:bg-primary/5 transition-all outline-none text-sm group-hover:border-white/20"
                                                placeholder="Prof. Julian Wright"
                                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                            />
                                            <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-primary transition-colors" />
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 ml-1">Institutional Email</label>
                                    <div className="relative group">
                                        <input
                                            type="email"
                                            required
                                            className="w-full bg-white/5 border border-white/10 rounded-xl py-4 pl-12 focus:border-primary focus:bg-primary/5 transition-all outline-none text-sm group-hover:border-white/20"
                                            placeholder="research@university.edu"
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        />
                                        <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-primary transition-colors" />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex justify-between items-center">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 ml-1">Password</label>
                                        {isLogin && <button type="button" className="text-[10px] font-black uppercase tracking-widest text-primary hover:underline">Forgot?</button>}
                                    </div>
                                    <div className="relative group">
                                        <input
                                            type="password"
                                            required
                                            className="w-full bg-white/5 border border-white/10 rounded-xl py-4 pl-12 focus:border-primary focus:bg-primary/5 transition-all outline-none text-sm group-hover:border-white/20"
                                            placeholder="••••••••••••"
                                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                        />
                                        <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-primary transition-colors" />
                                    </div>
                                </div>

                                <motion.button
                                    whileHover={{ scale: 1.01 }}
                                    whileTap={{ scale: 0.98 }}
                                    disabled={isLoading}
                                    type="submit"
                                    className="w-full bg-white text-slate-900 font-black py-4 rounded-xl shadow-xl flex items-center justify-center gap-3 transition-all mt-8 relative overflow-hidden"
                                >
                                    {isLoading ? (
                                        <div className="w-5 h-5 border-2 border-slate-900/10 border-t-slate-900 rounded-full animate-spin" />
                                    ) : (
                                        <>
                                            {isLogin ? 'Authenticate' : 'Initialize Vault'}
                                            <ChevronRight size={18} />
                                        </>
                                    )}
                                </motion.button>
                            </form>

                            <div className="mt-8">
                                <div className="relative flex items-center justify-center mb-8">
                                    <div className="p-2 bg-slate-900 relative z-10 text-[9px] font-black uppercase tracking-widest text-slate-500">Academic Portals</div>
                                    <div className="absolute w-full h-[1px] bg-white/5" />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <button className="flex items-center justify-center gap-2 py-3 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/5 transition-all text-xs font-bold text-slate-400">
                                        <Globe size={14} /> ORCID
                                    </button>
                                    <button className="flex items-center justify-center gap-2 py-3 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/5 transition-all text-xs font-bold text-slate-400">
                                        <Linkedin size={14} /> LinkedIn
                                    </button>
                                </div>
                            </div>

                            <div className="mt-12 text-center">
                                <button
                                    onClick={() => setIsLogin(!isLogin)}
                                    className="text-xs text-slate-400 hover:text-white transition-colors"
                                >
                                    {isLogin ? "New to Yukti Research? " : "Already verified? "}
                                    <span className="text-white font-bold">{isLogin ? 'Create Workspace' : 'Sign In'}</span>
                                </button>
                            </div>
                        </motion.div>
                    </AnimatePresence>

                    {/* Trust Footer */}
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 opacity-20 whitespace-nowrap">
                        <ShieldCheck size={12} />
                        <span className="text-[8px] font-black uppercase tracking-[0.2em]">End-to-End Encryption &bull; GDPL Compliant</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Auth;
