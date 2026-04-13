"use client";
import Link from "next/link";
import { Shield, Zap, Globe, BarChart3, Code2, ChevronRight, Sparkles, Activity } from "lucide-react";

const features = [
  {
    icon: Shield,
    title: "Multi-Agent Verification",
    desc: "CrewAI agents collaboratively verify claims across multiple independent sources in real-time.",
    color: "from-blue-500 to-cyan-400",
  },
  {
    icon: Activity,
    title: "Fake News Detection",
    desc: "Transformer-based ML models score probability of misinformation with explainable confidence breakdowns.",
    color: "from-red-500 to-orange-400",
  },
  {
    icon: Globe,
    title: "Knowledge Graph Intelligence",
    desc: "Neo4j-powered entity graph maps relationships between claims, sources, and contradiction patterns.",
    color: "from-purple-500 to-pink-400",
  },
  {
    icon: BarChart3,
    title: "Predictive Trend Analysis",
    desc: "Early-warning spike detection identifies astroturfed misinformation campaigns before they go viral.",
    color: "from-green-500 to-emerald-400",
  },
];

const stats = [
  { value: "6+", label: "AI Agents" },
  { value: "<2s", label: "Avg Latency" },
  { value: "94%", label: "F1 Score" },
  { value: "24/7", label: "Monitoring" },
];

export default function Home() {
  return (
    <div className="min-h-screen ambient-glow overflow-hidden">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-medium mb-8 animate-fade-up">
            <Sparkles className="w-4 h-4" />
            AI-Powered Truth Intelligence Engine
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold leading-tight mb-6 animate-fade-up" style={{ animationDelay: "0.1s" }}>
            <span className="text-white">Verify Truth.</span>
            <br />
            <span className="gradient-text">Expose Lies.</span>
          </h1>

          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-up" style={{ animationDelay: "0.2s" }}>
            Veritas AI deploys autonomous multi-agent intelligence pipelines to verify news claims, detect misinformation, and deliver explainable truth scores — in real-time.
          </p>

          <div className="flex items-center justify-center gap-4 animate-fade-up" style={{ animationDelay: "0.3s" }}>
            <Link
              href="/dashboard"
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-500 text-white font-semibold rounded-xl shadow-[0_0_30px_rgba(59,130,246,0.4)] hover:shadow-[0_0_40px_rgba(59,130,246,0.6)] transition-all duration-300 flex items-center gap-2"
            >
              <Zap className="w-5 h-5" /> Launch Intelligence
              <ChevronRight className="w-4 h-4" />
            </Link>
            <Link
              href="/developers"
              className="px-8 py-4 bg-white/5 border border-white/10 text-gray-300 font-semibold rounded-xl hover:bg-white/10 hover:text-white transition-all duration-300 flex items-center gap-2"
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
            Intelligence Architecture
          </h2>
          <p className="text-gray-500 text-center max-w-xl mx-auto mb-16">
            Six autonomous AI agents working in orchestrated consensus to deliver production-grade truth intelligence.
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
          <h2 className="text-3xl font-bold text-white mb-4">Ready to fight misinformation?</h2>
          <p className="text-gray-400 mb-8">Start verifying claims in seconds with our Siri-like voice interface.</p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-[0_0_30px_rgba(99,102,241,0.4)] hover:shadow-[0_0_40px_rgba(99,102,241,0.6)] transition-all"
          >
            <Zap className="w-5 h-5" /> Open Dashboard
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-white/5 text-center text-gray-600 text-sm">
        © {new Date().getFullYear()} Veritas AI. All rights reserved. Built with CrewAI, LangChain, and Neo4j.
      </footer>
    </div>
  );
}
