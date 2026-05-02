"use client";

import React, { useEffect, useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import { API_BASE_URL } from "@/services/api";
import { Mic, Zap, Sparkles, Brain } from "lucide-react";

interface SiriOverlayProps {
  query: string;
  onComplete?: (finalText: string) => void;
}

export const SiriOverlay: React.FC<SiriOverlayProps> = ({ query, onComplete }) => {
  const { streamingText, isStreaming, tier, model, error, streamQuery } = useSSE(API_BASE_URL);
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (query) {
      streamQuery(query);
    }
  }, [query, streamQuery]);

  useEffect(() => {
    // Sync displayed text with streaming text
    setDisplayedText(streamingText);
    
    // Auto-close after a delay if streaming finished
    if (streamingText && !isStreaming) {
      const timer = setTimeout(() => {
        if (onComplete) onComplete(streamingText);
      }, 5000); // 5 seconds to read
      return () => clearTimeout(timer);
    }
  }, [streamingText, isStreaming, onComplete]);

  if (!query && !isStreaming && !displayedText) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none p-8">
      {/* Siri-like glassmorphism container */}
      <div className="relative w-full max-w-2xl bg-black/40 backdrop-blur-3xl rounded-[40px] border border-white/10 shadow-2xl p-8 transform transition-all duration-500 animate-in fade-in zoom-in slide-in-from-bottom-8 pointer-events-auto">
        
        {/* Close Button */}
        <button 
          onClick={() => onComplete?.(displayedText)}
          className="absolute top-6 right-6 h-8 w-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center border border-white/10 transition-colors"
        >
          <span className="text-white/40 text-xs">✕</span>
        </button>

        {/* Header Stats */}
        <div className="flex items-center justify-between mb-6 opacity-60">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/30">
              <Brain className="h-4 w-4 text-cyan-300" />
            </div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-100">
              {tier || "Analyzing..."}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="h-3 w-3 text-amber-400" />
            <span className="text-[10px] font-mono text-slate-400">{model || "Optimizing..."}</span>
          </div>
        </div>

        {/* User Query (Faded) */}
        <div className="mb-4">
          <p className="text-slate-500 text-lg font-medium italic">"{query}"</p>
        </div>

        {/* Streaming Text (The "Siri" Response) */}
        <div className="min-h-[120px] mb-8">
          <p className="text-3xl sm:text-4xl font-semibold bg-clip-text text-transparent bg-gradient-to-br from-white via-white to-slate-500 leading-tight">
            {displayedText}
            {isStreaming && (
              <span className="inline-block w-1.5 h-8 ml-1 bg-cyan-400 animate-pulse align-middle" />
            )}
          </p>
        </div>

        {/* Siri Waveform Visualizer (Mock) */}
        <div className="flex items-center justify-center gap-1 h-12">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className={`w-1 rounded-full bg-gradient-to-t from-cyan-500 via-purple-500 to-rose-500 ${isStreaming ? 'animate-wave' : 'h-1 opacity-20'}`}
              style={{
                height: isStreaming ? `${Math.random() * 100}%` : '4px',
                animationDelay: `${i * 0.05}s`,
                animationDuration: '0.8s'
              }}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="mt-8 flex items-center justify-center gap-4 opacity-40">
          <Sparkles className="h-4 w-4 text-cyan-400" />
          <span className="text-[9px] uppercase tracking-[0.3em] text-slate-300 font-bold">Friday Core v2.0</span>
          <Sparkles className="h-4 w-4 text-purple-400" />
        </div>
      </div>

      <style jsx>{`
        @keyframes wave {
          0%, 100% { height: 4px; }
          50% { height: 40px; }
        }
        .animate-wave {
          animation: wave linear infinite;
        }
      `}</style>
    </div>
  );
};
