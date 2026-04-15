"use client";
import { useEffect, useState } from "react";
import { Clock, ChevronDown, ShieldCheck, AlertTriangle, Search, Loader2 } from "lucide-react";

import { API_BASE_URL, formatPercent } from "@/services/api";
import { HistoryEntry, HistoryResponse } from "@/types/api";


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
        setHistory(payload.items);
      } catch (err) {
        console.error(err);
        setError("History is currently unavailable.");
      } finally {
        setLoading(false);
      }
    };

    void loadHistory();
  }, []);

  const filtered = history.filter((entry) =>
    entry.query.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const statusColor = (status: string) => {
    if (status === "verified") return "text-green-400 bg-green-500/10 border-green-500/20";
    if (status === "likely_false") return "text-red-400 bg-red-500/10 border-red-500/20";
    return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
  };

  return (
    <main className="min-h-screen pt-24 pb-12 px-6 max-w-5xl mx-auto">
      <div className="flex flex-col items-center gap-2 mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Clock className="w-7 h-7 text-blue-400" /> Verification <span className="gradient-text">Timeline</span>
        </h1>
        <p className="text-gray-500 text-sm">Historical log of completed verification requests</p>
      </div>

      <div className="glass rounded-xl p-3 mb-8 flex items-center gap-3">
        <Search className="w-5 h-5 text-gray-500" />
        <input
          type="text"
          placeholder="Search verification history..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          className="bg-transparent text-white w-full focus:outline-none placeholder:text-gray-600"
        />
      </div>

      {loading && (
        <div className="glass rounded-xl p-6 flex items-center gap-3 text-gray-300">
          <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
          Loading verification history...
        </div>
      )}

      {error && !loading && (
        <div className="glass rounded-xl p-6 text-red-300 border border-red-500/20">{error}</div>
      )}

      {!loading && !error && (
        <div className="relative flex flex-col gap-4">
          <div className="absolute left-[19px] top-2 bottom-2 w-px bg-white/5" />

          {filtered.map((entry) => (
            <div key={entry.id} className="relative pl-12">
              <div className={`absolute left-2.5 top-5 w-3 h-3 rounded-full border-2 ${
                entry.status === "verified"
                  ? "bg-green-500 border-green-400"
                  : entry.status === "likely_false"
                    ? "bg-red-500 border-red-400"
                    : "bg-yellow-500 border-yellow-400"
              }`} />

              <button
                onClick={() => setExpandedItem(expandedItem === entry.id ? null : entry.id)}
                className="w-full glass rounded-xl p-5 text-left hover:border-white/10 transition-all group"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-600 font-mono">
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${statusColor(entry.status)}`}>
                      {entry.status === "verified" && <ShieldCheck className="w-3 h-3 inline mr-1" />}
                      {entry.status === "likely_false" && <AlertTriangle className="w-3 h-3 inline mr-1" />}
                      {entry.status}
                    </span>
                    <span className="text-white font-bold text-sm">{formatPercent(entry.truth_score)}</span>
                  </div>
                </div>
                <p className="text-white font-medium">{entry.query}</p>
                <ChevronDown className={`w-4 h-4 text-gray-600 absolute right-5 top-6 transition-transform ${expandedItem === entry.id ? "rotate-180" : ""}`} />
              </button>

              {expandedItem === entry.id && (
                <div className="ml-4 mt-2 p-4 glass rounded-lg border-l-2 border-blue-500/30 animate-fade-up">
                  <p className="text-gray-400 text-sm leading-relaxed">{entry.summary}</p>
                </div>
              )}
            </div>
          ))}

          {!filtered.length && (
            <div className="glass rounded-xl p-6 text-gray-400">No verification history matches your filter.</div>
          )}
        </div>
      )}
    </main>
  );
}
