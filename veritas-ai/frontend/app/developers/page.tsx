"use client";
import { useState } from "react";
import { Code2, Key, Copy, CheckCircle, Lock, Zap, Globe, BarChart3 } from "lucide-react";
import { API_BASE_URL } from "@/services/api";

const endpoints = [
  {
    method: "POST", path: "/api/v1/verify-news", auth: true,
    desc: "Submit a claim for full multi-agent verification. Returns truth score, status, and explainability breakdown.",
    body: '{ "query": "Is Apple buying Disney?" }',
  },
  {
    method: "POST", path: "/api/v1/stream-analysis", auth: true,
    desc: "Request a WebSocket session token for real-time streaming analysis.",
    body: '{ "query": "USA election integrity" }',
  },
  {
    method: "GET", path: "/api/v1/alerts", auth: true,
    desc: "Retrieve active global anomalies and misinformation spike alerts.",
    body: null,
  },
  {
    method: "GET", path: "/api/v1/predictive-trends", auth: true,
    desc: "Fetch early-warning trend predictions from the predictive intelligence engine.",
    body: null,
  },
  {
    method: "POST", path: "/api/v1/feedback", auth: false,
    desc: "Submit user feedback on a verification result to improve model accuracy.",
    body: '{ "query": "...", "original_truth_score": 0.72, "user_flag": "incorrect" }',
  },
];

const tiers = [
  { name: "Free", price: "$0", requests: "100 req/hr", features: ["Basic verification", "Community support"] },
  { name: "Pro", price: "$49/mo", requests: "5,000 req/hr", features: ["Priority processing", "Trend alerts", "Email support"] },
  { name: "Enterprise", price: "Custom", requests: "Unlimited", features: ["Dedicated infrastructure", "SLA guarantee", "Custom models", "24/7 support"] },
];

export default function DevelopersPage() {
  const [copiedKey, setCopiedKey] = useState(false);
  const exampleKey = "YOUR_API_KEY";

  const copyKey = () => {
    navigator.clipboard.writeText(exampleKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <main className="min-h-screen pt-24 pb-12 px-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col items-center gap-2 mb-12">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Code2 className="w-7 h-7 text-blue-400" /> Developer <span className="gradient-text">Platform</span>
        </h1>
        <p className="text-gray-500 text-sm">Integrate real-time truth intelligence into your applications</p>
      </div>

      {/* API Key Section */}
      <section className="glass rounded-2xl p-8 mb-10">
        <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
          <Key className="w-5 h-5 text-yellow-400" /> API Key Setup
        </h2>
        <p className="text-gray-500 text-sm mb-4">
          Configure developer keys with <code className="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">VERITAS_DEV_API_KEY</code> or
          <code className="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded ml-1">VERITAS_ENTERPRISE_API_KEY</code> on the backend. Use the key in the
          <code className="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded ml-1">X-API-KEY</code> header for authenticated endpoints.
        </p>
        <div className="flex items-center gap-3">
          <code className="flex-1 bg-black/40 border border-white/10 rounded-xl px-5 py-3 text-green-400 font-mono text-sm">
            {exampleKey}
          </code>
          <button
            onClick={copyKey}
            className="p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
          >
            {copiedKey ? <CheckCircle className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5 text-gray-400" />}
          </button>
        </div>
      </section>

      {/* Endpoints Reference */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-white mb-6">API Endpoints</h2>
        <div className="flex flex-col gap-4">
          {endpoints.map((ep, i) => (
            <div key={i} className="glass rounded-xl p-6">
              <div className="flex items-center gap-3 mb-3">
                <span className={`px-3 py-1 rounded-md text-xs font-bold tracking-wider ${
                  ep.method === "POST" ? "bg-blue-500/15 text-blue-400" : "bg-green-500/15 text-green-400"
                }`}>{ep.method}</span>
                <code className="text-white font-mono text-sm">{ep.path}</code>
                {ep.auth && <Lock className="w-3.5 h-3.5 text-yellow-500" />}
              </div>
              <p className="text-gray-400 text-sm mb-3">{ep.desc}</p>
              {ep.body && (
                <pre className="bg-black/40 rounded-lg p-4 text-xs text-gray-300 font-mono overflow-x-auto">
                  {ep.body}
                </pre>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Pricing Tiers (Phase 33: Monetization) */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-400" /> Pricing Tiers
        </h2>
        <p className="text-gray-500 text-sm mb-6">Scale from prototype to production with transparent pricing.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tiers.map((tier, i) => (
            <div key={i} className={`glass rounded-2xl p-8 flex flex-col ${i === 1 ? "ring-2 ring-blue-500/30 shadow-[0_0_30px_rgba(59,130,246,0.15)]" : ""}`}>
              <h3 className="text-xl font-bold text-white mb-1">{tier.name}</h3>
              <p className="text-3xl font-extrabold gradient-text mb-1">{tier.price}</p>
              <p className="text-xs text-gray-500 mb-6">{tier.requests}</p>
              <ul className="flex flex-col gap-2 flex-1">
                {tier.features.map((f, j) => (
                  <li key={j} className="text-sm text-gray-400 flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5 text-blue-400 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <button className={`mt-6 w-full py-3 rounded-xl font-semibold text-sm transition-all ${
                i === 1
                  ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-[0_0_20px_rgba(99,102,241,0.3)]"
                  : "bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10"
              }`}>
                {i === 2 ? "Contact Sales" : "Get Started"}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Quick Start */}
      <section className="glass rounded-2xl p-8">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-400" /> Quick Start
        </h2>
        <pre className="bg-black/40 rounded-xl p-6 text-sm text-gray-300 font-mono overflow-x-auto leading-relaxed">
{`curl -X POST ${API_BASE_URL}/verify-news \\
  -H "Content-Type: application/json" \\
  -H "X-API-KEY: ${exampleKey}" \\
  -d '{"query": "Is climate change accelerating?"}'`}
        </pre>
      </section>
    </main>
  );
}
