import { useCallback, useEffect, useRef, useState } from "react";

import { AlertItem, QueryResponse, WebSocketMessage } from "@/types/api";

interface SendQueryOptions {
  deep?: boolean;
}

interface UseWebSocketReturn {
  streamData: QueryResponse[];
  alerts: AlertItem[];
  activeStatus: string;
  error: string | null;
  progress: number;
  currentStage: string;
  assistantMessage: string;
  sessionGreeting: string;
  mode: "assistant" | "verification";
  intent: "control" | "news" | "verification" | "chat" | "interrupt" | null;
  sendQuery: (query: string, options?: SendQueryOptions) => void;
  interrupt: (reason?: string) => void;
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [streamData, setStreamData] = useState<QueryResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [activeStatus, setActiveStatus] = useState<string>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [currentStage, setCurrentStage] = useState<string>("");
  const [assistantMessage, setAssistantMessage] = useState<string>("Connecting FRIDAY...");
  const [sessionGreeting, setSessionGreeting] = useState<string>("");
  const [mode, setMode] = useState<"assistant" | "verification">("assistant");
  const [intent, setIntent] = useState<UseWebSocketReturn["intent"]>(null);

  const ws = useRef<WebSocket | null>(null);
  const reconnectDelayMs = useRef(1500);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setActiveStatus("idle");
        setError(null);
        reconnectDelayMs.current = 1500;
      };

      ws.current.onmessage = (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data) as WebSocketMessage;

          if (payload.status === "alert") {
            setAlerts((prev) => (payload.data ? [payload.data as AlertItem, ...prev] : prev));
            return;
          }

          if (payload.status === "session") {
            const greeting = payload.greeting || payload.message || "Hello Boss.";
            setSessionGreeting(greeting);
            setAssistantMessage(greeting);
            setMode(payload.mode || "assistant");
            setActiveStatus("idle");
            return;
          }

          if (payload.status === "assistant") {
            setAssistantMessage(payload.message || "On it, Boss.");
            setMode(payload.mode || "assistant");
            setIntent(payload.intent || null);
            setActiveStatus("assistant");
            return;
          }

          if (payload.status === "processing") {
            setAssistantMessage(payload.message || "Working on it, Boss.");
            setActiveStatus("processing");
            if (payload.progress !== undefined) {
              setProgress(payload.progress);
            }
            if (payload.stage !== undefined) {
              setCurrentStage(payload.stage);
            }
            return;
          }

          if (payload.status === "interrupted") {
            setAssistantMessage(payload.message || "Alright, stopping that.");
            setActiveStatus("interrupted");
            setProgress(0);
            setCurrentStage("");
            return;
          }

          if (payload.status === "complete") {
            if (payload.data) {
              setStreamData((prev) => [payload.data as QueryResponse, ...prev]);
              const response = payload.data as QueryResponse;
              setMode(response.assistant_mode || payload.mode || "assistant");
              setIntent(response.intent || payload.intent || null);
              setAssistantMessage(payload.message || response.summary);
            }
            setActiveStatus("complete");
            setProgress(100);
            setCurrentStage("complete");
            return;
          }

          if (payload.status === "error") {
            const errMsg = typeof payload.error === "string" ? payload.error : payload.error?.message;
            setError(errMsg || "Assistant request failed.");
            setAssistantMessage(errMsg || "Something went sideways, Boss.");
            setActiveStatus("error");
            setProgress(0);
            setCurrentStage("");
          }
        } catch {
          setError("Couldn’t parse the assistant response.");
        }
      };

      ws.current.onclose = () => {
        setActiveStatus("disconnected");
        if (!shouldReconnect.current) {
          return;
        }
        reconnectTimer.current = setTimeout(() => connect(), reconnectDelayMs.current);
        reconnectDelayMs.current = Math.min(reconnectDelayMs.current * 1.5, 10000);
      };

      ws.current.onerror = () => {
        setError("WebSocket connection failed.");
      };
    } catch {
      setError("Failed to connect to FRIDAY.");
    }
  }, [url]);

  useEffect(() => {
    shouldReconnect.current = true;
    connect();

    return () => {
      shouldReconnect.current = false;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      ws.current?.close();
    };
  }, [connect]);

  const sendQuery = useCallback((query: string, options?: SendQueryOptions) => {
    if (!query.trim()) {
      return;
    }

    if (ws.current?.readyState === WebSocket.OPEN) {
      setStreamData([]);
      setAlerts([]);
      setError(null);
      setProgress(0);
      setCurrentStage("");
      setActiveStatus("transmitting");
      ws.current.send(JSON.stringify({ type: "query", query: query.trim(), deep: options?.deep || false }));
      return;
    }

    setError("FRIDAY isn’t connected right now.");
  }, []);

  const interrupt = useCallback((reason = "Stop") => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "interrupt", query: reason }));
    }
    setAssistantMessage("Alright, stopping that.");
    setActiveStatus("interrupted");
    setProgress(0);
    setCurrentStage("");
  }, []);

  return {
    streamData,
    alerts,
    activeStatus,
    error,
    progress,
    currentStage,
    assistantMessage,
    sessionGreeting,
    mode,
    intent,
    sendQuery,
    interrupt,
  };
};
