"use client";

import React from "react";
import { Shield, Activity, ExternalLink, AlertCircle, CheckCircle2 } from "lucide-react";
import { formatPercent } from "@/services/api";

interface FrameProps {
  source: string;
  summary: string;
  credibility: number;
  status: string;
  url?: string;
}

const Frame = ({ source, summary, credibility, status, url }: FrameProps) => {
  const isVerified = status === "verified" || credibility > 0.8;
  const isContradiction = summary.toLowerCase().includes("contradict") || summary.toLowerCase().includes("disagree");
  
  return (
    <div className={`group relative overflow-hidden rounded-2xl border transition-all hover:shadow-[0_0_20px_rgba(34,211,238,0.15)] \${isContradiction ? "border-rose-500/30 bg-rose-500/5" : "border-white/10 bg-black/40 backdrop-blur-md hover:border-cyan-500/50"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 animate-pulse rounded-full bg-cyan-500" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-cyan-400">{source}</span>
        </div>
        <div className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase ${isVerified ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
          {isVerified ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
          {status}
        </div>
      </div>
      
      <p className="line-clamp-4 text-sm leading-relaxed text-slate-300">
        {summary}
      </p>
      
      <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-3">
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-tighter text-slate-500">Credibility</span>
          <span className="text-xs font-mono font-bold text-white">{formatPercent(credibility)}</span>
        </div>
        {url && (
          <a href={url} target="_blank" rel="noreferrer" className="text-slate-500 hover:text-cyan-400 transition-colors">
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>
    </div>
  );
};

interface ControlRoomProps {
  payload: any;
}

export const ControlRoom = ({ payload }: ControlRoomProps) => {
  const [expandedFrame, setExpandedFrame] = React.useState<number | null>(null);
  // Extract frames from payload
  // We'll use sources and facts to populate 6 frames
  const sources = payload.sources || [];
  const frames = sources.slice(0, 6).map((s: any, i: number) => ({
    source: s.type || "Source " + (i + 1),
    summary: payload.facts[i] || "Analyzing data stream...",
    credibility: s.credibility_score || 0.5,
    status: s.credibility_score > 0.7 ? "verified" : "analyzing",
    url: s.url
  }));

  // Fill up to 6 frames
  while (frames.length < 6) {
    frames.push({
      source: "NEURAL FEED " + (frames.length + 1),
      summary: "Awaiting live data injection from global news matrix...",
      credibility: 0.0,
      status: "standby"
    });
  }

  return (
    <div className="w-full">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30">
            <Shield className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white uppercase tracking-wider">AI Intelligence Control Room</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <Activity className="h-3 w-3 text-emerald-400" />
              <span className="text-[10px] text-slate-500 uppercase font-mono tracking-tight">Active Multi-Agent Stream: Verified Perspectives</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-widest text-slate-500">Consensus</div>
            <div className="text-lg font-mono font-bold text-cyan-400">{formatPercent(payload.truth_score)}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {frames.map((frame: any, i: number) => (
          <div key={i} onClick={() => setExpandedFrame(expandedFrame === i ? null : i)} className={expandedFrame === i ? "lg:col-span-2 lg:row-span-2" : ""}><Frame {...frame} /></div>
        ))}
      </div>
    </div>
  );
};
