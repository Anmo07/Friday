"use client";
import { useEffect, useState } from "react";
import { Clock, ChevronDown, ShieldCheck, AlertCircle, Search, Loader2, Database, ShieldAlert, Activity } from "lucide-react";

import { API_BASE_URL, formatPercent } from "@/services/api";
import { HistoryEntry } from "@/types/api";

interface HistoryResponse {
  history: HistoryEntry[];
  count: number;
}

export default function TimelinePage() {
  const [searchFilter, setSearchFilter] = useState("");
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/history?limit=50`);
        if (!response.ok) {
          throw new Error("History request failed.");
        }
        const payload = (await response.json()) as HistoryResponse;
        // Fix: API returns { history: [...] }, not items
        setHistory(payload.history || []);
      } catch (err) {
        console.error(err);
        setError("Neural log retrieval failed.");
      } finally {
        setLoading(false);
      }
    };

    void loadHistory();
  }, []);

  const filtered = history.filter((entry) =>
    entry.query.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const getStatusConfig = (status: string) => {
    switch (status) {
      case "verified":
        return {
          color: "text-emerald-400",
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/30",
          icon: <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />,
          label: "VERIFIED"
        };
      case "likely_false":
        return {
          color: "text-rose-400",
          bg: "bg-rose-500/10",
          border: "border-rose-500/30",
          icon: <ShieldAlert className="w-3.5 h-3.5 mr-1.5" />,
          label: "CONTRADICTED"
        };
      default:
        return {
          color: "text-amber-400",
          bg: "bg-amber-500/10",
          border: "border-amber-500/30",
          icon: <AlertCircle className="w-3.5 h-3.5 mr-1.5" />,
          label: "UNCERTAIN"
        };
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 font-sans p-6 overflow-hidden relative">
      {/* Background Ambience */}
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(168,85,247,0.08),transparent_50%)] pointer-events-none" />
      
      <main className="relative z-10 max-w-5xl mx-auto pt-20 pb-12">
        <div className="flex flex-col items-center gap-4 mb-12 text-center">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] uppercase tracking-widest text-fuchsia-300">
            <Database className="h-3 w-3" /> Neural Log Archive
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">
            Verification <span className="text-transparent bg-clip-text bg-gradient-to-r from-fuchsia-400 to-cyan-400">Timeline</span>
          </h1>
          <p className="text-slate-400 text-sm max-w-md">Access historical multi-agent verification requests and their final consensus reports.</p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/40 p-4 mb-10 flex items-center gap-3 backdrop-blur-xl shadow-[0_0_30px_rgba(0,0,0,0.5)]">
          <Search className="w-5 h-5 text-slate-500 ml-2" />
          <input
            type="text"
            placeholder="Search queries, sources, or entities..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="bg-transparent text-white w-full text-sm focus:outline-none placeholder:text-slate-600 font-mono"
          />
          <div className="px-3 py-1 bg-white/5 rounded-lg border border-white/5 flex items-center gap-2">
            <Activity className="w-3 h-3 text-cyan-400" />
            <span className="text-[10px] font-mono text-slate-400">{filtered.length} entries</span>
          </div>
        </div>

        {loading && (
          <div className="rounded-3xl border border-white/10 bg-black/25 p-12 flex flex-col items-center gap-4 text-slate-400 backdrop-blur-xl">
            <Loader2 className="w-8 h-8 animate-spin text-fuchsia-400" />
            <span className="text-xs uppercase tracking-widest font-mono">Syncing Neural Logs...</span>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-6 flex items-center gap-4 text-rose-300 backdrop-blur-xl">
            <ShieldAlert className="w-6 h-6" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {!loading && !error && (
          <div className="relative flex flex-col gap-6">
            {/* Main Timeline Line */}
            <div className="absolute left-[39px] top-6 bottom-6 w-px bg-gradient-to-b from-fuchsia-500/50 via-cyan-500/20 to-transparent" />

            {filtered.map((entry) => {
              const status = getStatusConfig(entry.status);
              const isExpanded = expandedItem === entry.id;
              
              return (
                <div key={entry.id} className="relative pl-24 group">
                  {/* Timeline Dot */}
                  <div className={`absolute left-[35px] top-8 w-2.5 h-2.5 rounded-full border-2 bg-black z-10 transition-colors duration-300 ${isExpanded ? "border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)]" : "border-slate-600 group-hover:border-slate-400"}`} />

                  {/* Timestamp Label (Left of line) */}
                  <div className="absolute left-0 top-7 w-[28px] text-right">
                    <span className="text-[9px] text-slate-500 font-mono block">
                      {new Date(entry.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </span>
                  </div>

                  <button
                    onClick={() => setExpandedItem(isExpanded ? null : entry.id)}
                    className={`w-full rounded-[24px] border bg-black/40 backdrop-blur-md p-6 text-left transition-all duration-300 ${
                      isExpanded 
                        ? "border-cyan-500/50 shadow-[0_0_30px_rgba(34,211,238,0.15)] bg-black/60" 
                        : "border-white/10 hover:border-white/20 hover:bg-white/5"
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                      <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-1 rounded-full text-[9px] font-bold tracking-widest border flex items-center ${status.color} ${status.bg} ${status.border}`}>
                          {status.icon}
                          {status.label}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">
                          {new Date(entry.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="flex flex-col text-right">
                          <span className="text-[9px] uppercase tracking-tighter text-slate-500">Truth Score</span>
                          <span className="text-sm font-mono font-bold text-white">{formatPercent(entry.truth_score)}</span>
                        </div>
                        <div className={`p-2 rounded-full transition-colors ${isExpanded ? "bg-cyan-500/10 text-cyan-400" : "bg-white/5 text-slate-400"}`}>
                          <ChevronDown className={`w-4 h-4 transition-transform duration-300 ${isExpanded ? "rotate-180" : ""}`} />
                        </div>
                      </div>
                    </div>
                    
                    <p className={`text-lg text-slate-200 font-medium leading-relaxed transition-all ${isExpanded ? "text-white" : ""}`}>
                      "{entry.query}"
                    </p>

                    {isExpanded && (
                      <div className="mt-6 pt-6 border-t border-white/10 animate-in fade-in slide-in-from-top-4 duration-300">
                        <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-400 mb-3">
                          <Activity className="h-3 w-3 text-cyan-400" /> Final Assessment
                        </div>
                        <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap border-l-2 border-cyan-500/30 pl-4 py-1">
                          {entry.summary}
                        </p>
                      </div>
                    )}
                  </button>
                </div>
              );
            })}

            {!filtered.length && history.length > 0 && (
              <div className="pl-24">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-slate-400 backdrop-blur-xl">
                  No matching logs found in the archive.
                </div>
              </div>
            )}
            
            {!history.length && !loading && !error && (
              <div className="pl-24">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-slate-400 backdrop-blur-xl">
                  Neural archive is currently empty. Initiate a query to start logging.
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
