"use client";
import { useState } from "react";
import { Clock, ChevronDown, ShieldCheck, AlertTriangle, Search } from "lucide-react";

interface HistoryEntry {
  id: number;
  timestamp: string;
  query: string;
  status: string;
  truth_score: number;
  summary: string;
}

// Simulated historical data — in production, fetched from backend /api/v1/history
const mockHistory: HistoryEntry[] = [
  {
    id: 1, timestamp: "2026-04-13T09:12:00Z", query: "Is Apple acquiring Disney?",
    status: "likely_false", truth_score: 12, summary: "No credible financial filings or SEC disclosures support this claim."
  },
  {
    id: 2, timestamp: "2026-04-13T08:45:00Z", query: "NASA confirms water on Mars surface",
    status: "verified", truth_score: 91, summary: "Multiple peer-reviewed studies and NASA press releases confirm subsurface water ice."
  },
  {
    id: 3, timestamp: "2026-04-12T22:30:00Z", query: "Global markets to crash 40% next week",
    status: "likely_false", truth_score: 8, summary: "No major financial institution or central bank has issued such a forecast."
  },
  {
    id: 4, timestamp: "2026-04-12T18:10:00Z", query: "New COVID variant detected in Southeast Asia",
    status: "uncertain", truth_score: 55, summary: "WHO monitoring reports mention surveillance but no official variant designation."
  },
];

export default function TimelinePage() {
  const [searchFilter, setSearchFilter] = useState("");
  const [expandedItem, setExpandedItem] = useState<number | null>(null);

  const filtered = mockHistory.filter(
    (h) => h.query.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const statusColor = (s: string) => {
    if (s === "verified") return "text-green-400 bg-green-500/10 border-green-500/20";
    if (s === "likely_false") return "text-red-400 bg-red-500/10 border-red-500/20";
    return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
  };

  return (
    <main className="min-h-screen pt-24 pb-12 px-6 max-w-5xl mx-auto">
      <div className="flex flex-col items-center gap-2 mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Clock className="w-7 h-7 text-blue-400" /> Verification <span className="gradient-text">Timeline</span>
        </h1>
        <p className="text-gray-500 text-sm">Historical log of all intelligence operations</p>
      </div>

      {/* Search Filter */}
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

      {/* Timeline */}
      <div className="relative flex flex-col gap-4">
        {/* Vertical line */}
        <div className="absolute left-[19px] top-2 bottom-2 w-px bg-white/5" />

        {filtered.map((entry) => (
          <div key={entry.id} className="relative pl-12">
            {/* Dot */}
            <div className={`absolute left-2.5 top-5 w-3 h-3 rounded-full border-2 ${
              entry.status === "verified" ? "bg-green-500 border-green-400" :
              entry.status === "likely_false" ? "bg-red-500 border-red-400" :
              "bg-yellow-500 border-yellow-400"
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
                  <span className="text-white font-bold text-sm">{entry.truth_score}%</span>
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
      </div>
    </main>
  );
}
