"use client";
import Link from "next/link";
import { Shield, Zap, Globe, BarChart3, Code2, ChevronRight, Sparkles, Activity } from "lucide-react";

const features = [
  {
    icon: Shield,
    title: "Voice-First Assistance",
    desc: "FRIDAY listens continuously, answers in real time, and stays interruptible while it works.",
    color: "from-blue-500 to-cyan-400",
  },
  {
    icon: Activity,
    title: "Task-First Execution",
    desc: "Open apps, run commands, control the browser, and handle system actions before dropping into deeper analysis.",
    color: "from-red-500 to-orange-400",
  },
  {
    icon: Globe,
    title: "Live News + Verification",
    desc: "Pull current coverage fast, then switch into verification mode only when the question actually needs it.",
    color: "from-purple-500 to-pink-400",
  },
  {
    icon: BarChart3,
    title: "OS-Level Reach",
    desc: "System-aware control hooks let FRIDAY behave like an assistant instead of a dashboard tool.",
    color: "from-green-500 to-emerald-400",
  },
];

const stats = [
  { value: "6+", label: "AI Agents" },
  { value: "<500ms", label: "Response Start" },
  { value: "2", label: "Max LLM Calls" },
  { value: "24/7", label: "Listening Loop" },
];

export default function Home() {
  return (
    <div className="min-h-screen ambient-glow overflow-hidden">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-sm font-mono mb-8 animate-fade-up shadow-[0_0_15px_rgba(0,234,255,0.2)]">
            <Sparkles className="w-4 h-4" />
            Always-On AI Assistant
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold leading-tight mb-6 animate-fade-up" style={{ animationDelay: "0.1s" }}>
            <span className="text-white">Talk to</span>
            <br />
            <span className="gradient-text">FRIDAY.</span>
          </h1>

          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-up" style={{ animationDelay: "0.2s" }}>
            A human-like, voice-first assistant with system control, live interruption, and fast verification when the job calls for receipts.
          </p>

          <div className="flex items-center justify-center gap-4 animate-fade-up" style={{ animationDelay: "0.3s" }}>
            <Link
              href="/dashboard"
              className="px-8 py-4 bg-cyan-500/20 border border-cyan-500/50 text-cyan-400 font-mono font-bold uppercase tracking-wider rounded-xl shadow-[0_0_30px_rgba(0,234,255,0.4)] hover:shadow-[0_0_50px_rgba(0,234,255,0.6)] hover:bg-cyan-500/30 transition-all duration-300 flex items-center gap-2"
            >
              <Zap className="w-5 h-5" /> Wake FRIDAY
              <ChevronRight className="w-4 h-4" />
            </Link>
            <Link
              href="/developers"
              className="px-8 py-4 bg-purple-500/10 border border-purple-500/30 text-purple-400 font-mono font-bold uppercase tracking-wider rounded-xl hover:bg-purple-500/20 hover:shadow-[0_0_30px_rgba(168,85,247,0.3)] transition-all duration-300 flex items-center gap-2"
            >
              <Code2 className="w-5 h-5" /> Developer API
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-8 border-y border-white/5 glass">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s, i) => (
            <div key={i} className="flex flex-col items-center text-center">
              <span className="text-3xl font-bold text-white">{s.value}</span>
              <span className="text-xs text-gray-500 uppercase tracking-widest mt-1">{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-4">
            Assistant Architecture
          </h2>
          <p className="text-gray-500 text-center max-w-xl mx-auto mb-16">
            Fast assistant mode by default. Verification mode when the question actually needs deeper scrutiny.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map((f, i) => (
              <div
                key={i}
                className="glass rounded-2xl p-8 hover:border-white/10 transition-all duration-300 group"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${f.color} flex items-center justify-center mb-5 shadow-lg group-hover:scale-110 transition-transform`}>
                  <f.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto text-center glass rounded-3xl p-12">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to talk to your system?</h2>
          <p className="text-gray-400 mb-8">Launch FRIDAY and start speaking. No input box. No enter key.</p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-4 bg-cyan-500/20 border border-cyan-500/50 text-cyan-400 font-mono font-bold uppercase tracking-wider rounded-xl shadow-[0_0_30px_rgba(0,234,255,0.4)] hover:shadow-[0_0_50px_rgba(0,234,255,0.6)] hover:bg-cyan-500/30 transition-all"
          >
            <Zap className="w-5 h-5" /> Open FRIDAY
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-white/5 text-center text-gray-600 text-sm">
        © {new Date().getFullYear()} Friday. All rights reserved. Built with CrewAI, LangChain, and Neo4j.
      </footer>
    </div>
  );
}
