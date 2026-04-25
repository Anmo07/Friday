"use client";
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { TruthGauge } from "./TruthGauge";
import { Loader2, AlertTriangle, ShieldCheck, Zap, ServerCrash, Mic, MicOff, Volume2, CheckCircle2, Clock, Brain, Search, Shield, FileSearch, MessageSquareWarning, Activity } from "lucide-react";
import { WS_BASE_URL, formatPercent } from "@/services/api";
import { QueryResponse } from "@/types/api";

const PROGRESS_STAGES = [
  { key: "cache_check", label: "Checking cache...", icon: Clock },
  { key: "routing", label: "Analyzing query...", icon: Brain },
  { key: "processing", label: "Processing...", icon: Loader2 },
  { key: "data_collection", label: "Collecting data...", icon: Search },
  { key: "verification", label: "Verifying sources...", icon: Shield },
  { key: "fact_check", label: "Cross-referencing facts...", icon: CheckCircle2 },
  { key: "scoring", label: "Computing truth score...", icon: FileSearch },
  { key: "generating", label: "Generating response...", icon: Zap },
  { key: "finalizing", label: "Finalizing response...", icon: Loader2 },
];

export default function Dashboard() {
  const { streamData, alerts, activeStatus, error, progress, currentStage, sendQuery } = useWebSocket(WS_BASE_URL);
  const [query, setQuery] = useState("");
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const [lastSpokenSummary, setLastSpokenSummary] = useState<string>("");
  const sendQueryRef = useRef(sendQuery);
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    sendQueryRef.current = sendQuery;
  }, [sendQuery]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      // @ts-ignore
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition && !recognitionRef.current) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = 'en-US';

        recognitionRef.current.onstart = () => {
          console.log("Speech recognition started");
        };

        recognitionRef.current.onresult = (event: any) => {
          let fullTranscript = '';
          for (let i = 0; i < event.results.length; ++i) {
            fullTranscript += event.results[i][0].transcript;
          }
          setQuery(fullTranscript);
        };

        recognitionRef.current.onend = () => {
          setIsListening(false);
          setQuery((prev) => {
            if (prev.trim().length > 2) {
              sendQueryRef.current(prev.trim());
            }
            return prev;
          });
        };

        recognitionRef.current.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsListening(false);
        };
      }
    }
  }, []);

  const toggleVoice = () => {
    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch (e) {
        console.error("Error stopping recognition", e);
      }
      setIsListening(false);
    } else {
      setQuery("");
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (e) {
        console.error("Error starting recognition", e);
        setIsListening(false);
      }
    }
  };

  const handleExecute = useCallback(() => {
    if (!query.trim()) return;
    sendQuery(query);
  }, [query, sendQuery]);

  const payload: QueryResponse | null = streamData.length > 0 ? streamData[0] : null;
  const isProcessing = activeStatus !== "idle" && activeStatus !== "complete" && activeStatus !== "error" && activeStatus !== "disconnected";

  useEffect(() => {
    if (payload && payload.summary && payload.summary !== lastSpokenSummary) {
      if (typeof window !== "undefined" && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(payload.summary);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        const voices = window.speechSynthesis.getVoices();
        const idealVoice = voices.find(v => v.name.includes("Samantha") || v.name.includes("Google") || v.name.includes("Siri") || v.name.includes("Alex"));
        if (idealVoice) utterance.voice = idealVoice;
        
        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);

        window.speechSynthesis.speak(utterance);
        setLastSpokenSummary(payload.summary);
      }
    }
  }, [payload, lastSpokenSummary]);

  const currentStageInfo = PROGRESS_STAGES.find(s => s.key === currentStage);
  const CurrentStageIcon = currentStageInfo?.icon || Loader2;

  // Determine orb state
  let orbState = "idle";
  if (isSpeaking) orbState = "speaking";
  else if (isProcessing) orbState = "processing";
  else if (isListening) orbState = "listening";

  const getOrbStyles = () => {
    switch (orbState) {
      case "listening":
        return "bg-cyan-500/20 border-cyan-400 shadow-[0_0_40px_rgba(0,234,255,0.6)] animate-pulse";
      case "processing":
        return "bg-purple-500/20 border-purple-400 shadow-[0_0_40px_rgba(168,85,247,0.6)] animate-[orb-pulse_2s_ease-in-out_infinite]";
      case "speaking":
        return "bg-pink-500/20 border-pink-400 shadow-[0_0_40px_rgba(236,72,153,0.6)] animate-[orb-pulse_1s_ease-in-out_infinite]";
      default:
        return "bg-gray-800/50 border-gray-600 hover:border-cyan-400 hover:shadow-[0_0_20px_rgba(0,234,255,0.3)] transition-all";
    }
  };

  const getOrbIconColor = () => {
    switch (orbState) {
      case "listening": return "text-cyan-400";
      case "processing": return "text-purple-400";
      case "speaking": return "text-pink-400";
      default: return "text-gray-400";
    }
  };

  return (
    <div className="w-full min-h-[80vh] flex flex-col items-center justify-start pt-10 gap-8 relative pb-20 font-sans">
      
      {/* Background elements */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-20 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-900/40 via-transparent to-transparent"></div>

      {/* Top Status Indicators */}
      <div className="w-full max-w-4xl flex justify-between px-4 z-10 text-xs font-mono uppercase tracking-widest text-cyan-500/70">
        <div className="flex items-center gap-2">
          <Activity className={`w-4 h-4 ${activeStatus === 'disconnected' ? 'text-red-500' : 'text-cyan-400'} ${activeStatus !== 'idle' && activeStatus !== 'disconnected' ? 'animate-pulse' : ''}`} />
          SYS: {activeStatus.toUpperCase()}
        </div>
        <div className="flex items-center gap-2">
           NET: {activeStatus === 'disconnected' ? 'OFFLINE' : 'SECURE'}
        </div>
      </div>

      {/* Center Focus: Voice Orb */}
      <div className="z-10 flex flex-col items-center gap-6 mt-10">
        <button
          onClick={toggleVoice}
          className={`relative w-32 h-32 rounded-full border-2 flex items-center justify-center backdrop-blur-md transition-all duration-500 ${getOrbStyles()}`}
        >
          {/* Inner ring */}
          <div className={`absolute inset-2 rounded-full border border-white/10 ${orbState !== 'idle' ? 'animate-ping opacity-20' : ''}`}></div>
          
          {orbState === 'processing' ? (
            <Brain className={`w-12 h-12 ${getOrbIconColor()} animate-pulse`} />
          ) : orbState === 'speaking' ? (
            <Volume2 className={`w-12 h-12 ${getOrbIconColor()} animate-pulse`} />
          ) : isListening ? (
            <Mic className={`w-12 h-12 ${getOrbIconColor()}`} />
          ) : (
            <MicOff className={`w-12 h-12 ${getOrbIconColor()}`} />
          )}
        </button>
        <div className="text-sm font-medium tracking-widest uppercase text-gray-400/80 animate-fade-up">
           {orbState === 'listening' ? "Listening..." : orbState === 'processing' ? "Analyzing Data" : orbState === 'speaking' ? "Vocalizing" : "System Ready"}
        </div>
      </div>

      {/* Live Transcript / Input */}
      <div className="w-full max-w-2xl z-10 animate-fade-up" style={{ animationDelay: "0.2s" }}>
        <div className="relative group">
           <input
             type="text"
             className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-white text-lg text-center focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_30px_rgba(0,234,255,0.2)] transition-all placeholder:text-gray-600 backdrop-blur-xl"
             placeholder="Initiate query or enable microphone..."
             value={query}
             onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
             onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && handleExecute()}
             disabled={isProcessing || isSpeaking}
           />
           {!isProcessing && !isListening && query.trim() && (
             <button
               onClick={handleExecute}
               className="absolute right-4 top-1/2 -translate-y-1/2 bg-cyan-500/20 hover:bg-cyan-500/40 text-cyan-400 p-2 rounded-xl border border-cyan-500/50 transition-all shadow-[0_0_15px_rgba(0,234,255,0.3)]"
             >
               <Zap className="w-5 h-5" />
             </button>
           )}
        </div>
      </div>

      {/* Processing Status Panel */}
      {isProcessing && !payload && (
        <div className="w-full max-w-2xl bg-[#01030a]/80 backdrop-blur-xl border border-purple-500/30 rounded-2xl p-6 mt-4 z-10 shadow-[0_0_30px_rgba(168,85,247,0.15)] animate-fade-up">
          <div className="flex items-center gap-4 mb-4">
            <CurrentStageIcon className={`w-6 h-6 text-purple-400 ${currentStageInfo?.key === "parallel_agents" ? "animate-pulse" : ""}`} />
            <span className="text-purple-200 font-mono tracking-wide uppercase text-sm">
              {activeStatus === "transmitting" ? "INITIALIZING UPLINK..." : activeStatus}
            </span>
          </div>
          
          <div className="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-purple-600 to-cyan-400 transition-all duration-500 ease-out shadow-[0_0_10px_rgba(0,234,255,0.8)]"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          <div className="flex justify-between mt-3 text-xs text-gray-500 font-mono">
            <span>SYS.START</span>
            <span className="text-cyan-400 font-bold">{progress}%</span>
            <span>SYS.END</span>
          </div>
          
          <div className="mt-5 flex flex-wrap gap-2 justify-center">
            {PROGRESS_STAGES.map((stage, idx) => {
              const isComplete = progress > (idx * 100 / PROGRESS_STAGES.length);
              const isActive = currentStage === stage.key;
              const StageIcon = stage.icon;
              return (
                <div 
                  key={stage.key}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-mono tracking-wider uppercase transition-all ${
                    isComplete 
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' 
                      : isActive 
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50 shadow-[0_0_10px_rgba(168,85,247,0.4)] animate-pulse'
                        : 'bg-black/50 text-gray-600 border border-white/5'
                  }`}
                >
                  <StageIcon className="w-3 h-3" />
                  <span className="hidden sm:inline">{stage.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Alerts & Errors */}
      <div className="w-full max-w-4xl z-10 flex flex-col gap-4">
        {error && (
          <div className="w-full bg-pink-950/20 border border-pink-500/40 rounded-xl p-4 flex items-center gap-3 backdrop-blur-md shadow-[0_0_20px_rgba(236,72,153,0.15)]">
            <AlertTriangle className="w-5 h-5 text-pink-400" />
            <span className="text-pink-200 text-sm font-mono">{error}</span>
          </div>
        )}

        {alerts.length > 0 && (
          <div className="w-full flex flex-col gap-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alerts.slice(0, 4).map((alert: any, i: number) => (
                <div key={i} className={`p-4 rounded-xl border flex items-start gap-3 backdrop-blur-md ${alert.severity === 'high' ? 'bg-pink-950/20 border-pink-500/30 shadow-[0_0_15px_rgba(236,72,153,0.1)]' : 'bg-purple-950/20 border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.1)]'}`}>
                  {alert.severity === 'high' ? <ServerCrash className="text-pink-400 mt-1" /> : <AlertTriangle className="text-purple-400 mt-1" />}
                  <div className="flex flex-col">
                    <span className={`text-xs font-mono font-bold uppercase tracking-wider ${alert.severity === 'high' ? 'text-pink-400' : 'text-purple-400'}`}>{alert.alert_type}</span>
                    <span className="text-gray-300 text-sm mt-1">{alert.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Payload / Output Panel */}
      {payload && (
        <div className="w-full max-w-5xl z-10 mt-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Status & Gauge */}
            <div className="glass bg-[#01030a]/60 border border-white/10 rounded-3xl p-8 flex flex-col items-center relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              
              <TruthGauge score={payload.truth_score !== undefined ? payload.truth_score : 0.0} />

              <div className="mt-8 flex flex-col items-center gap-3 w-full z-10">
                <div className={`px-6 py-2.5 rounded-full font-mono font-bold uppercase tracking-widest text-sm flex items-center gap-2 shadow-[0_0_20px_rgba(0,0,0,0.5)] ${payload.status === 'verified' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/40 shadow-[0_0_20px_rgba(0,234,255,0.2)]' : payload.status === 'likely_false' ? 'bg-pink-500/10 text-pink-400 border border-pink-500/40 shadow-[0_0_20px_rgba(236,72,153,0.2)]' : 'bg-purple-500/10 text-purple-400 border border-purple-500/40 shadow-[0_0_20px_rgba(168,85,247,0.2)]'}`}>
                  {payload.status === 'verified' ? <ShieldCheck className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                  {payload.status}
                </div>

                {payload._cached && (
                  <div className="px-3 py-1 rounded-full text-[10px] font-mono bg-white/5 text-gray-400 border border-white/10 flex items-center gap-1 mt-2">
                    <Zap className="w-3 h-3 text-cyan-500" /> CACHED_RES
                  </div>
                )}

                {payload.explanation && payload.explanation.confidence_breakdown && (
                  <div className="grid grid-cols-3 gap-2 w-full mt-6">
                    <div className="flex flex-col items-center bg-black/60 p-3 rounded-xl border border-white/5">
                      <span className="text-cyan-400 font-mono font-bold text-lg">{payload.explanation.confidence_breakdown.authority}</span>
                      <span className="text-[9px] text-gray-500 uppercase tracking-widest font-mono mt-1">AUTH</span>
                    </div>
                    <div className="flex flex-col items-center bg-black/60 p-3 rounded-xl border border-white/5">
                      <span className="text-cyan-400 font-mono font-bold text-lg">{payload.explanation.confidence_breakdown.agreement}</span>
                      <span className="text-[9px] text-gray-500 uppercase tracking-widest font-mono mt-1">AGREE</span>
                    </div>
                    <div className="flex flex-col items-center bg-black/60 p-3 rounded-xl border border-white/5">
                      <span className="text-pink-400 font-mono font-bold text-lg">{payload.explanation.confidence_breakdown.bias}</span>
                      <span className="text-[9px] text-gray-500 uppercase tracking-widest font-mono mt-1">BIAS</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Content Panel */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              <div className="glass bg-[#01030a]/60 border border-white/10 rounded-3xl p-8 relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 opacity-50"></div>
                
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-sm font-mono uppercase tracking-widest text-cyan-400 flex items-center gap-2">
                    <Volume2 className="w-4 h-4" /> Vocalized Output
                  </h2>
                </div>
                
                <p className="text-gray-300 leading-relaxed text-lg font-light tracking-wide typing-effect" style={{animationDuration: "1s"}}>
                  {payload.summary}
                </p>
              </div>

              {payload.explanation && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="glass bg-cyan-950/10 border border-cyan-500/20 rounded-2xl p-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-cyan-500/5 rounded-bl-full pointer-events-none"></div>
                    <h4 className="text-cyan-500 font-mono font-bold uppercase tracking-widest text-xs mb-5 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4" /> Supportive Evidence
                    </h4>
                    <ul className="flex flex-col gap-3">
                      {payload.explanation.why_true.map((item: string, i: number) => (
                        <li key={i} className="text-sm text-gray-400 flex items-start gap-3">
                          <div className="w-1 h-1 rounded-full bg-cyan-500 mt-2.5 shrink-0 shadow-[0_0_5px_#00eaff]" />
                          <span className="leading-relaxed">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="glass bg-pink-950/10 border border-pink-500/20 rounded-2xl p-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-pink-500/5 rounded-bl-full pointer-events-none"></div>
                    <h4 className="text-pink-500 font-mono font-bold uppercase tracking-widest text-xs mb-5 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" /> Contradictory Evidence
                    </h4>
                    <ul className="flex flex-col gap-3">
                      {payload.explanation.why_false.map((item: string, i: number) => (
                        <li key={i} className="text-sm text-gray-400 flex items-start gap-3">
                          <div className="w-1 h-1 rounded-full bg-pink-500 mt-2.5 shrink-0 shadow-[0_0_5px_#ec4899]" />
                          <span className="leading-relaxed">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
            
          </div>
        </div>
      )}

    </div>
  );
}
