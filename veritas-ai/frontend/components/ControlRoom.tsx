"use client";

import React, { useMemo } from "react";
import {
  Shield,
  Activity,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Eye,
  Crosshair,
  Radio,
  Layers,
  TrendingUp,
  AlertTriangle,
  Globe,
  Cpu,
  Zap,
} from "lucide-react";
import { formatPercent } from "@/services/api";
import { AgentOutput, QueryResponse } from "@/types/api";

/* ──────────────────────────────────────────────────────────── */
/*  Frame Types                                                 */
/* ──────────────────────────────────────────────────────────── */

type FrameType =
  | "primary"
  | "evidence"
  | "contradiction"
  | "perspective"
  | "live_feed"
  | "agent_status";

interface IntelFrame {
  id: string;
  type: FrameType;
  title: string;
  content: string;
  icon: React.ElementType;
  accentColor: string;
  glowColor: string;
  credibility?: number;
  status?: string;
  url?: string;
  meta?: Record<string, any>;
}

/* ──────────────────────────────────────────────────────────── */
/*  Frame Component                                             */
/* ──────────────────────────────────────────────────────────── */

const FrameCard = React.memo(({
  frame,
  isExpanded,
  onToggle,
}: {
  frame: IntelFrame;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  const Icon = frame.icon;

  const statusColors: Record<string, string> = {
    verified: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    uncertain: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    conflicting: "bg-rose-500/15 text-rose-400 border-rose-500/30",
    analyzing: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
    standby: "bg-slate-500/15 text-slate-400 border-slate-500/30",
    cached: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  };

  const borderAccent =
    frame.type === "primary"
      ? "border-cyan-500/40 hover:border-cyan-400/60"
      : frame.type === "contradiction"
        ? "border-rose-500/30 hover:border-rose-400/50"
        : frame.type === "perspective"
          ? "border-purple-500/30 hover:border-purple-400/50"
          : "border-white/8 hover:border-white/15";

  return (
    <button
      onClick={onToggle}
      className={`cr-frame group relative text-left w-full overflow-hidden rounded-2xl border transition-all duration-300 ${borderAccent} ${isExpanded ? "cr-frame-expanded" : ""}`}
      style={{
        background: `linear-gradient(135deg, rgba(15,18,30,0.85) 0%, rgba(10,12,22,0.95) 100%)`,
        boxShadow: isExpanded
          ? `0 0 30px ${frame.glowColor}, inset 0 1px 0 rgba(255,255,255,0.05)`
          : `inset 0 1px 0 rgba(255,255,255,0.03)`,
      }}
    >
      {/* Scan line effect on hover */}
      <div className="cr-scanline" />

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ background: frame.accentColor }}
          >
            <Icon className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-300">
            {frame.title}
          </span>
        </div>

        {frame.status && (
          <div
            className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[8px] font-bold uppercase tracking-wider ${statusColors[frame.status] || statusColors.analyzing}`}
          >
            {frame.status === "verified" ? (
              <CheckCircle2 className="h-2.5 w-2.5" />
            ) : frame.status === "conflicting" ? (
              <AlertTriangle className="h-2.5 w-2.5" />
            ) : (
              <AlertCircle className="h-2.5 w-2.5" />
            )}
            {frame.status}
          </div>
        )}
      </div>

      {/* Content */}
      <p
        className={`text-sm leading-relaxed text-slate-300/90 ${isExpanded ? "" : "line-clamp-3"}`}
      >
        {frame.content}
      </p>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-3">
        {frame.credibility !== undefined ? (
          <div className="flex items-center gap-3">
            <div className="flex flex-col">
              <span className="text-[8px] uppercase tracking-widest text-slate-500">
                Credibility
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-white">
                  {formatPercent(frame.credibility)}
                </span>
                <div className="h-1 w-16 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${frame.credibility * 100}%`,
                      background:
                        frame.credibility > 0.7
                          ? "linear-gradient(90deg, #10b981, #34d399)"
                          : frame.credibility > 0.4
                            ? "linear-gradient(90deg, #f59e0b, #fbbf24)"
                            : "linear-gradient(90deg, #ef4444, #f87171)",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div />
        )}

        {frame.url && (
          <a
            href={frame.url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-slate-500 hover:text-cyan-400 transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}

        {frame.meta?.latency_ms && (
          <span className="text-[9px] font-mono text-slate-500">
            {frame.meta.latency_ms.toFixed(0)}ms
          </span>
        )}
      </div>
    </button>
  );
});

FrameCard.displayName = "FrameCard";

/* ──────────────────────────────────────────────────────────── */
/*  Depth Level Badge                                           */
/* ──────────────────────────────────────────────────────────── */

const DepthBadge = React.memo(({ level }: { level: number }) => {
  const config: Record<number, { label: string; color: string; glow: string }> = {
    1: { label: "FAST", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30", glow: "shadow-[0_0_10px_rgba(52,211,153,0.2)]" },
    2: { label: "ENHANCED", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30", glow: "shadow-[0_0_10px_rgba(34,211,238,0.2)]" },
    3: { label: "DEEP", color: "text-purple-400 bg-purple-500/10 border-purple-500/30", glow: "shadow-[0_0_10px_rgba(168,85,247,0.2)]" },
  };
  const c = config[level] || config[1];
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[9px] font-bold uppercase tracking-widest ${c.color} ${c.glow}`}>
      <Layers className="h-3 w-3" />
      L{level} {c.label}
    </div>
  );
});

DepthBadge.displayName = "DepthBadge";

/* ──────────────────────────────────────────────────────────── */
/*  Agent Activity Feed                                         */
/* ──────────────────────────────────────────────────────────── */

const AgentFeed = React.memo(({ agents }: { agents: AgentOutput[] }) => {
  if (agents.length === 0) return null;

  const agentIcons: Record<string, React.ElementType> = {
    retrieval_agent: Globe,
    validation_agent: Shield,
    perspective_agent: Eye,
    contradiction_agent: AlertTriangle,
    summary_agent: Cpu,
    response_agent: Zap,
  };

  return (
    <div className="cr-agent-feed">
      <div className="flex items-center gap-2 mb-3">
        <Radio className="h-3 w-3 text-cyan-400 animate-pulse" />
        <span className="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-400">
          Agent Activity
        </span>
      </div>
      <div className="space-y-1.5">
        {agents.map((a, i) => {
          const Icon = agentIcons[a.agent] || Cpu;
          return (
            <div
              key={`${a.agent}-${i}`}
              className="flex items-center gap-2.5 rounded-lg bg-white/[0.02] border border-white/5 px-3 py-1.5 cr-agent-item"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <Icon className="h-3 w-3 text-cyan-400" />
              <span className="text-[10px] font-mono text-slate-300 flex-1 truncate">
                {a.agent.replace(/_/g, " ")}
              </span>
              {a.cached && (
                <span className="text-[8px] uppercase tracking-wider text-purple-400 font-bold">
                  cached
                </span>
              )}
              <span className="text-[9px] font-mono text-slate-500">
                {a.latency_ms.toFixed(0)}ms
              </span>
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            </div>
          );
        })}
      </div>
    </div>
  );
});

AgentFeed.displayName = "AgentFeed";

/* ──────────────────────────────────────────────────────────── */
/*  Main Control Room                                           */
/* ──────────────────────────────────────────────────────────── */

interface ControlRoomProps {
  payload: QueryResponse;
  agentUpdates?: AgentOutput[];
  depthLevel?: number;
}

export const ControlRoom = React.memo(({ payload, agentUpdates = [], depthLevel = 1 }: ControlRoomProps) => {
  const [expandedFrame, setExpandedFrame] = React.useState<string | null>(null);

  // Build intelligence frames from payload
  const frames: IntelFrame[] = useMemo(() => {
    const result: IntelFrame[] = [];

    // 1. Primary Answer Frame
    result.push({
      id: "primary",
      type: "primary",
      title: "Primary Intelligence",
      content: payload.summary || "Awaiting analysis...",
      icon: Crosshair,
      accentColor: "rgba(34,211,238,0.2)",
      glowColor: "rgba(34,211,238,0.15)",
      credibility: payload.truth_score,
      status: payload.status === "verified" ? "verified" : payload.status === "likely_false" ? "conflicting" : "uncertain",
    });

    // 2. Supporting Evidence Frames (from sources)
    const sources = payload.sources || [];
    sources.slice(0, 3).forEach((s, i) => {
      result.push({
        id: `evidence-${i}`,
        type: "evidence",
        title: s.type?.toUpperCase() || `SOURCE ${i + 1}`,
        content: payload.facts?.[i] || "Evidence stream active...",
        icon: Shield,
        accentColor: s.credibility_score > 0.7
          ? "rgba(52,211,153,0.2)"
          : "rgba(245,158,11,0.2)",
        glowColor: s.credibility_score > 0.7
          ? "rgba(52,211,153,0.1)"
          : "rgba(245,158,11,0.1)",
        credibility: s.credibility_score,
        status: s.credibility_score > 0.7 ? "verified" : "uncertain",
        url: s.url,
      });
    });

    // 3. Contradiction Frame
    const contradictions = payload.contradictions || [];
    if (contradictions.length > 0 || depthLevel >= 3) {
      result.push({
        id: "contradictions",
        type: "contradiction",
        title: "Contradictions",
        content: contradictions.length > 0
          ? contradictions.join(" • ")
          : "No contradictions detected across sources.",
        icon: AlertTriangle,
        accentColor: "rgba(239,68,68,0.2)",
        glowColor: "rgba(239,68,68,0.1)",
        status: contradictions.length > 0 ? "conflicting" : "verified",
        meta: { count: contradictions.length },
      });
    }

    // 4. Perspectives Frame
    if (depthLevel >= 3) {
      result.push({
        id: "perspectives",
        type: "perspective",
        title: "Multi-Perspective Analysis",
        content: "Supporting, questioning, and neutral viewpoints have been evaluated across sources.",
        icon: Eye,
        accentColor: "rgba(168,85,247,0.2)",
        glowColor: "rgba(168,85,247,0.1)",
        status: "verified",
      });
    }

    // 5. Live Feed Frame
    result.push({
      id: "live-feed",
      type: "live_feed",
      title: "Live Intelligence Feed",
      content: agentUpdates.length > 0
        ? `${agentUpdates.length} agents completed. Last: ${agentUpdates[agentUpdates.length - 1]?.agent?.replace(/_/g, " ")}`
        : "Monitoring active data streams...",
      icon: Radio,
      accentColor: "rgba(34,211,238,0.15)",
      glowColor: "rgba(34,211,238,0.08)",
      status: agentUpdates.length > 0 ? "verified" : "analyzing",
      meta: {
        latency_ms: payload.latency_ms || 0,
        agents_count: agentUpdates.length,
      },
    });

    return result;
  }, [payload, agentUpdates, depthLevel]);

  return (
    <div className="w-full cr-container">
      {/* Control Room Header */}
      <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="cr-header-icon flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30">
            <Shield className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white uppercase tracking-wider">
              AI Intelligence Control Room
            </h3>
            <div className="flex items-center gap-3 mt-1">
              <div className="flex items-center gap-1.5">
                <Activity className="h-3 w-3 text-emerald-400 animate-pulse" />
                <span className="text-[10px] text-slate-500 uppercase font-mono tracking-tight">
                  Active Stream
                </span>
              </div>
              <DepthBadge level={depthLevel} />
            </div>
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-[9px] uppercase tracking-widest text-slate-500">Truth Score</div>
            <div className="text-xl font-mono font-bold text-cyan-400 cr-score-glow">
              {formatPercent(payload.truth_score)}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[9px] uppercase tracking-widest text-slate-500">Confidence</div>
            <div className="text-xl font-mono font-bold text-emerald-400">
              {formatPercent(payload.confidence_score)}
            </div>
          </div>
          {payload.latency_ms && (
            <div className="text-right">
              <div className="text-[9px] uppercase tracking-widest text-slate-500">Latency</div>
              <div className="text-xl font-mono font-bold text-purple-400">
                {payload.latency_ms.toFixed(0)}ms
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Grid of Intelligence Frames */}
      <div className="cr-grid">
        {frames.map((frame) => (
          <div
            key={frame.id}
            className={`cr-grid-item ${expandedFrame === frame.id ? "cr-grid-item-expanded" : ""} ${frame.type === "primary" ? "cr-grid-item-primary" : ""}`}
          >
            <FrameCard
              frame={frame}
              isExpanded={expandedFrame === frame.id}
              onToggle={() => setExpandedFrame(expandedFrame === frame.id ? null : frame.id)}
            />
          </div>
        ))}
      </div>

      {/* Agent Activity Feed */}
      {agentUpdates.length > 0 && (
        <div className="mt-6">
          <AgentFeed agents={agentUpdates} />
        </div>
      )}
    </div>
  );
});

ControlRoom.displayName = "ControlRoom";
