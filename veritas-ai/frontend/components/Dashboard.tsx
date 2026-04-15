"use client";
import React, { useState, useEffect, useRef } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { TruthGauge } from "./TruthGauge";
import { Loader2, AlertTriangle, ShieldCheck, Zap, ServerCrash, Mic, MicOff, Volume2 } from "lucide-react";
import { WS_BASE_URL, formatPercent } from "@/services/api";
import { QueryResponse } from "@/types/api";

export default function Dashboard() {
  const { streamData, alerts, activeStatus, error, sendQuery } = useWebSocket(WS_BASE_URL);
  const [query, setQuery] = useState("");
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const [lastSpokenSummary, setLastSpokenSummary] = useState<string>("");
  const sendQueryRef = useRef(sendQuery);

  useEffect(() => {
    sendQueryRef.current = sendQuery;
  }, [sendQuery]);

  useEffect(() => {
    // Inject SpeechRecognition securely 
    if (typeof window !== "undefined") {
      // @ts-ignore
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = 'en-US';

        recognitionRef.current.onresult = (event: any) => {
          let currentTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            currentTranscript += event.results[i][0].transcript;
          }
          setQuery(currentTranscript);
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

        recognitionRef.current.onerror = () => {
          setIsListening(false);
        };
      }
    }
  }, []);

  const toggleVoice = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      setQuery("");
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const handleExecute = () => {
    if (!query.trim()) return;
    sendQuery(query);
  };

  const payload: QueryResponse | null = streamData.length > 0 ? streamData[0] : null;
  const isProcessing = activeStatus === "transmitting" || activeStatus === "processing" || activeStatus.startsWith("Verifying");

  // Speak automatically when a new payload explicitly finalizes dynamically
  useEffect(() => {
    if (payload && payload.summary && payload.summary !== lastSpokenSummary) {
      if (typeof window !== "undefined" && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(payload.summary);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        // Find Siri/Google equivalents organically if possible
        const voices = window.speechSynthesis.getVoices();
        const idealVoice = voices.find(v => v.name.includes("Samantha") || v.name.includes("Google") || v.name.includes("Siri") || v.name.includes("Alex"));
        if (idealVoice) utterance.voice = idealVoice;

        window.speechSynthesis.speak(utterance);
        setLastSpokenSummary(payload.summary);
      }
    }
  }, [payload, lastSpokenSummary]);

  return (
    <div className="w-full flex flex-col gap-6 relative pb-20">

      {/* Search Input Mapping Bounds */}
      <div className="w-full relative shadow-[0_0_30px_rgba(59,130,246,0.15)] rounded-2xl overflow-hidden ring-1 ring-white/10 glass">
        <div className="bg-gray-900/60 backdrop-blur-xl p-6 flex flex-row items-center gap-4 border border-white/5">
          <button
            onClick={toggleVoice}
            className={`p-4 rounded-xl flex items-center justify-center transition-all duration-300 ${isListening ? 'bg-red-500 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.6)]' : 'bg-gray-800 hover:bg-gray-700'}`}
          >
            {isListening ? <Mic className="w-6 h-6 text-white" /> : <MicOff className="w-6 h-6 text-gray-400" />}
          </button>
          <input
            type="text"
            className="w-full bg-gray-950/50 border border-white/10 rounded-xl px-5 py-4 text-white text-lg focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-gray-600"
            placeholder="Type or click the microphone to speak..."
            value={query}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
            onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && handleExecute()}
          />
          <button
            onClick={handleExecute}
            disabled={isProcessing}
            className="bg-primary hover:bg-blue-500 text-white px-8 py-4 rounded-xl font-semibold tracking-wide transition-all duration-300 shadow-[0_0_20px_rgba(59,130,246,0.4)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isProcessing ? (
              <><Loader2 className="animate-spin w-5 h-5" /> Parsing</>
            ) : (
              <><Zap className="w-5 h-5" /> Execute</>
            )}
          </button>
        </div>
      </div>

      {isProcessing && !payload && (
        <div className="w-full bg-blue-900/20 border border-blue-500/30 rounded-xl p-4 flex items-center gap-4 animate-pulse mt-4">
          <Loader2 className="animate-spin text-blue-400 w-6 h-6" />
          <span className="text-blue-200 font-medium tracking-wide">{activeStatus === "transmitting" ? "Starting verification..." : activeStatus}</span>
        </div>
      )}

      {error && (
        <div className="w-full bg-red-950/30 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <span className="text-red-200 text-sm">{error}</span>
        </div>
      )}

      {alerts.length > 0 && (
        <div className="w-full flex flex-col gap-3 mt-4">
          <h3 className="text-gray-400 uppercase tracking-widest text-xs font-bold px-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500" /> Active Anomalies
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {alerts.slice(0, 4).map((alert: any, i: number) => (
              <div key={i} className={`p-4 rounded-xl border border-white/10 flex items-start gap-3 backdrop-blur-md ${alert.severity === 'high' ? 'bg-red-950/40 border-red-500/30' : 'bg-yellow-950/40 border-yellow-500/30'}`}>
                {alert.severity === 'high' ? <ServerCrash className="text-red-400 mt-1" /> : <AlertTriangle className="text-yellow-400 mt-1" />}
                <div className="flex flex-col">
                  <span className={`text-sm font-bold uppercase ${alert.severity === 'high' ? 'text-red-400' : 'text-yellow-400'}`}>{alert.alert_type}</span>
                  <span className="text-gray-300 text-sm mt-1">{alert.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {payload && (
        <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

          <div className="bg-gray-900/40 border border-white/5 rounded-3xl p-8 flex flex-col items-center shadow-2xl backdrop-blur-3xl ring-1 ring-white/5 relative">
            <TruthGauge score={payload.truth_score !== undefined ? payload.truth_score : 0.0} />

            <div className="mt-8 flex flex-col items-center gap-2 w-full">
              <div className={`px-6 py-2 rounded-full font-bold uppercase tracking-widest text-sm flex items-center gap-2 ${payload.status === 'verified' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : payload.status === 'likely_false' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'}`}>
                {payload.status === 'verified' ? <ShieldCheck className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                {payload.status}
              </div>

              {payload.explanation && payload.explanation.confidence_breakdown && (
                <div className="grid grid-cols-3 gap-2 w-full mt-6">
                  <div className="flex flex-col items-center bg-black/40 p-3 rounded-xl border border-white/5">
                    <span className="text-primary font-bold text-lg">{payload.explanation.confidence_breakdown.authority}</span>
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest">Authority</span>
                  </div>
                  <div className="flex flex-col items-center bg-black/40 p-3 rounded-xl border border-white/5">
                    <span className="text-primary font-bold text-lg">{payload.explanation.confidence_breakdown.agreement}</span>
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest">Agreement</span>
                  </div>
                  <div className="flex flex-col items-center bg-black/40 p-3 rounded-xl border border-white/5">
                    <span className="text-red-400 font-bold text-lg">{payload.explanation.confidence_breakdown.bias}</span>
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest">Bias</span>
                  </div>
                </div>
              )}

              <div className="mt-5 text-xs text-gray-500 uppercase tracking-widest">
                Confidence {formatPercent(payload.confidence_score)} • Bias {formatPercent(payload.fake_probability)}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 flex flex-col gap-6">
            <div className="bg-gray-900/40 border border-white/5 rounded-3xl p-8 backdrop-blur-3xl shadow-2xl relative overflow-hidden flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Volume2 className="w-5 h-5 text-primary" /> Vocalized Intelligence Summary
                </h2>
              </div>
              <p className="text-gray-300 leading-relaxed text-lg">{payload.summary}</p>
            </div>

            {payload.explanation && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-green-950/20 border border-green-500/10 rounded-2xl p-6">
                  <h4 className="text-green-500 font-bold uppercase tracking-wider text-xs mb-4">Why True</h4>
                  <ul className="flex flex-col gap-2">
                    {payload.explanation.why_true.map((item: string, i: number) => (
                      <li key={i} className="text-sm text-gray-400 flex items-start gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-red-950/20 border border-red-500/10 rounded-2xl p-6">
                  <h4 className="text-red-500 font-bold uppercase tracking-wider text-xs mb-4">Why False</h4>
                  <ul className="flex flex-col gap-2">
                    {payload.explanation.why_false.map((item: string, i: number) => (
                      <li key={i} className="text-sm text-gray-400 flex items-start gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
