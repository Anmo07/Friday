"use client";

import React, { useCallback, useEffect, useRef, useState, useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Brain,
  Command,
  Ear,
  Layers,
  Mic,
  MicOff,
  Newspaper,
  OctagonX,
  Sparkles,
  Volume2,
  Zap,
  Database,
} from "lucide-react";

import { useWebSocket } from "@/hooks/useWebSocket";
import { WS_BASE_URL, formatPercent } from "@/services/api";
import { QueryResponse } from "@/types/api";
import { ControlRoom } from "./ControlRoom";
import { SiriOverlay } from "./SiriOverlay";

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: any) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

const INTERRUPT_PHRASES = ["stop", "wait", "cancel", "hold on"];

const STAGE_LABELS: Record<string, string> = {
  cache_check: "Checking memory",
  action: "Working the system",
  news_fetch: "Scanning current coverage",
  processing: "Thinking",
  data_collection: "Pulling context",
  verification: "Verifying",
  generating: "Framing the answer",
  parallel_agents: "Running parallel agents",
  scoring: "Computing truth score",
  complete: "Ready",
};

const INTENT_STYLES: Record<string, { label: string; icon: React.ElementType; badge: string }> = {
  control: { label: "System Control", icon: Command, badge: "bg-amber-500/10 text-amber-200 border-amber-400/30" },
  news: { label: "News Sweep", icon: Newspaper, badge: "bg-cyan-500/10 text-cyan-200 border-cyan-400/30" },
  verification: { label: "Verification", icon: Brain, badge: "bg-fuchsia-500/10 text-fuchsia-200 border-fuchsia-400/30" },
  chat: { label: "Assistant", icon: Bot, badge: "bg-emerald-500/10 text-emerald-200 border-emerald-400/30" },
  interrupt: { label: "Interrupted", icon: OctagonX, badge: "bg-rose-500/10 text-rose-200 border-rose-400/30" },
};

const DEPTH_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: "L1 FAST", color: "text-emerald-400" },
  2: { label: "L2 ENHANCED", color: "text-cyan-400" },
  3: { label: "L3 DEEP", color: "text-purple-400" },
};

const normalizeTranscript = (value: string) => value.replace(/\s+/g, " ").trim();
const shouldInterrupt = (value: string) => INTERRUPT_PHRASES.includes(normalizeTranscript(value).toLowerCase());

export default function Dashboard() {
  const {
    streamData,
    activeStatus,
    error,
    progress,
    currentStage,
    assistantMessage,
    sessionGreeting,
    mode,
    intent,
    depthLevel,
    agentUpdates,
    voiceCommand,
    sendQuery,
    interrupt,
  } = useWebSocket(WS_BASE_URL);

  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [lastUserQuery, setLastUserQuery] = useState("");
  const [activeSSEQuery, setActiveSSEQuery] = useState("");

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const shouldKeepListeningRef = useRef(true);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSentQueryRef = useRef("");
  const lastSpokenRef = useRef("");
  const greetingSpokenRef = useRef(false);
  const busyRef = useRef(false);
  const speakingRef = useRef(false);

  const payload: QueryResponse | null = streamData[0] || null;
  const isBusy = ["transmitting", "assistant", "processing"].includes(activeStatus);
  const stageLabel = STAGE_LABELS[currentStage] || assistantMessage || "Listening";
  
  const currentIntent = intent || payload?.intent || "chat";
  const intentStyle = INTENT_STYLES[currentIntent] || INTENT_STYLES.chat;
  const IntentIcon = intentStyle.icon;
  const depthInfo = DEPTH_LABELS[depthLevel] || DEPTH_LABELS[1];

  useEffect(() => { busyRef.current = isBusy; }, [isBusy]);
  useEffect(() => { speakingRef.current = isSpeaking; }, [isSpeaking]);

  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const speakText = useCallback((text: string) => {
    if (!text || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    stopSpeaking();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => ["Samantha", "Siri", "Jenny"].some(n => v.name.includes(n)));
    if (preferred) utterance.voice = preferred;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, [stopSpeaking]);

  const handleInterrupt = useCallback((reason = "Stop") => {
    stopSpeaking();
    interrupt(reason);
    setLiveTranscript("");
  }, [interrupt, stopSpeaking]);

  const dispatchQuery = useCallback((transcript: string, isFinal = false) => {
    const cleaned = normalizeTranscript(transcript);
    if (!cleaned || cleaned === lastSentQueryRef.current) return;
    setLastUserQuery(cleaned);
    const useDeep = /(analyze deeply|compare|news breakdown|in-depth|full analysis|deep dive|investigate)/i.test(cleaned);
    
    // Switch to SSE for Siri-style typing
    setActiveSSEQuery(cleaned);
    // Still send via WebSocket if needed for other dashboard state, 
    // but SiriOverlay will handle the typing.
    sendQuery(cleaned, { deep: useDeep });
    setLiveTranscript("");
  }, [sendQuery]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try { recognitionRef.current.start(); } catch {}
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) { setMicError("Browser does not support speech recognition."); return; }

    const recognition: SpeechRecognitionInstance = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onstart = () => { setIsListening(true); setMicError(null); };
    recognition.onresult = (event: any) => {
      let final = "", interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const chunk = event.results[i][0]?.transcript || "";
        if (event.results[i].isFinal) final += chunk; else interim += chunk;
      }
      const transcript = normalizeTranscript(`${final} ${interim}`);
      setLiveTranscript(transcript);
      if (!transcript) return;
      if ((busyRef.current || speakingRef.current) && shouldInterrupt(transcript)) { handleInterrupt(transcript); return; }
      if (speakingRef.current) return;
      if (final.trim() && !interim.trim()) dispatchQuery(transcript, true);
    };
    recognition.onerror = (event: { error: string }) => {
      setIsListening(false);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        shouldKeepListeningRef.current = false;
        setMicError("Mic permission is blocked. Tap the orb to retry.");
        return;
      }
      if (event.error === "network" || event.error === "no-speech" || event.error === "aborted") {
        return;
      }
      setMicError(`Mic issue: ${event.error}`);
    };
    recognition.onend = () => { setIsListening(false); if (shouldKeepListeningRef.current) restartTimerRef.current = setTimeout(startListening, 300); };
    recognitionRef.current = recognition;
    startListening();
    return () => { shouldKeepListeningRef.current = false; recognition.abort(); stopSpeaking(); };
  }, [dispatchQuery, handleInterrupt, startListening, stopSpeaking]);

  useEffect(() => {
    if (sessionGreeting && !greetingSpokenRef.current) {
      greetingSpokenRef.current = true;
      speakText(sessionGreeting);
    }
  }, [sessionGreeting, speakText]);

  useEffect(() => {
    if (payload?.summary && payload.summary !== lastSpokenRef.current) {
      lastSpokenRef.current = payload.summary;
      speakText(payload.summary);
    }
  }, [payload, speakText]);

  const orbState = activeStatus === "interrupted" ? "interrupted" : isSpeaking ? "speaking" : isBusy ? "processing" : isListening ? "listening" : "idle";
  const orbStyles = orbState === "listening" ? "border-emerald-300 bg-emerald-400/10 shadow-[0_0_40px_rgba(52,211,153,0.2)]" :
                     orbState === "processing" ? "border-cyan-300 bg-cyan-400/10 shadow-[0_0_40px_rgba(34,211,238,0.2)] animate-pulse" :
                     orbState === "speaking" ? "border-fuchsia-300 bg-fuchsia-400/10 shadow-[0_0_40px_rgba(232,121,249,0.2)] animate-pulse" :
                     orbState === "interrupted" ? "border-rose-300 bg-rose-400/10 shadow-[0_0_40px_rgba(251,113,133,0.2)]" :
                     "border-white/10 bg-white/5";

  // Determine if Control Room should be shown
  const showControlRoom = payload && (
    mode === "verification" ||
    currentIntent === "news" ||
    currentIntent === "verification" ||
    depthLevel >= 2 ||
    payload.sources?.length > 0
  );

  return (
    <div className="relative w-full min-h-screen bg-[#020617] text-slate-200 font-sans p-6 overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,0.08),transparent_50%)]" />
      <div className="absolute inset-0 cr-grid-bg" />
      
      {/* Siri-style UI Overlay */}
      {activeSSEQuery && (
        <SiriOverlay 
          query={activeSSEQuery} 
          onComplete={() => setActiveSSEQuery("")} 
        />
      )}

      <div className="relative z-10 max-w-7xl mx-auto flex flex-col gap-8">
        
        {/* TOP CENTER ORB */}
        <div className="flex flex-col items-center justify-center gap-4 mt-4">
          <button 
            onClick={() => { if (isBusy || isSpeaking) handleInterrupt(); else startListening(); }}
            className={`relative flex h-28 w-28 items-center justify-center rounded-full border transition-all duration-500 ${orbStyles}`}
          >
            <div className="absolute inset-2 rounded-full border border-white/5" />
            {orbState === "speaking" ? <Volume2 className="h-9 w-9 text-fuchsia-200" /> :
             orbState === "processing" ? <Brain className="h-9 w-9 text-cyan-200" /> :
             isListening ? <Mic className="h-9 w-9 text-emerald-200" /> :
             <MicOff className="h-9 w-9 text-slate-500" />}
          </button>
          
          <div className="flex flex-col items-center text-center">
            {/* Status row with depth badge */}
            <div className="flex items-center gap-3 mb-2">
              <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] uppercase tracking-widest text-cyan-300">
                <Sparkles className="h-3 w-3" /> {stageLabel}
              </div>
              {isBusy && (
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] uppercase tracking-widest font-mono ${depthInfo.color}`}>
                  <Layers className="h-3 w-3" /> {depthInfo.label}
                </div>
              )}
              {agentUpdates.length > 0 && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] uppercase tracking-widest text-purple-400 font-mono">
                  <Database className="h-3 w-3" /> {agentUpdates.length} agents
                </div>
              )}
            </div>
            <p className="text-lg font-medium text-white max-w-lg h-12 overflow-hidden">{assistantMessage || "I'm listening, Boss."}</p>
          </div>
        </div>

        {/* DASHBOARD GRID / CONTROL ROOM */}
        <div className="w-full transition-all duration-700">
          {showControlRoom ? (
            <ControlRoom
              payload={payload}
              agentUpdates={agentUpdates}
              depthLevel={depthLevel}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-80">
              {/* Simple View for Chat/General Mode */}
              <div className="cr-idle-card rounded-3xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-xl h-64 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-emerald-400 mb-4">
                    <Ear className="h-4 w-4" /> Live Ear
                  </div>
                  <p className="text-xl text-slate-300">{liveTranscript || "..."}</p>
                </div>
                {lastUserQuery && <div className="text-xs text-slate-500">Last: {lastUserQuery}</div>}
              </div>
              
              <div className="cr-idle-card rounded-3xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-xl h-64 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-cyan-400 mb-4">
                    <Bot className="h-4 w-4" /> System Status
                  </div>
                  <div className="space-y-2.5">
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Neural Engine</span><span className="text-cyan-400 font-mono text-xs">ONLINE</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Voice Synthesis</span><span className="text-fuchsia-400 font-mono text-xs">READY</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Adaptive Router</span><span className="text-emerald-400 font-mono text-xs">L{depthLevel} MODE</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Smart Cache</span><span className="text-purple-400 font-mono text-xs">ACTIVE</span></div>
                  </div>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                   <div className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-500 rounded-full" style={{ width: `${progress}%` }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* VOICE COMMAND INDICATOR */}
        {voiceCommand && (
          <div className="flex items-center gap-3 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4 text-sm text-cyan-200 cr-agent-item">
            <Command className="h-5 w-5 text-cyan-400" /> Voice command: <span className="font-mono font-bold">{voiceCommand}</span>
          </div>
        )}

        {/* ERROR HANDLING */}
        {(error || micError) && (
          <div className="flex items-center gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-200">
            <AlertTriangle className="h-5 w-5 text-rose-400" /> {error || micError}
          </div>
        )}

      </div>
    </div>
  );
}
