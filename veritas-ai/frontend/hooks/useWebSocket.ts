import { useEffect, useRef, useState, useCallback } from "react";

import { AlertItem, QueryResponse, WebSocketMessage } from "@/types/api";

interface UseWebSocketReturn {
  streamData: QueryResponse[];
  alerts: AlertItem[];
  activeStatus: string;
  error: string | null;
  progress: number;
  currentStage: string;
  sendQuery: (query: string) => void;
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [streamData, setStreamData] = useState<QueryResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [activeStatus, setActiveStatus] = useState<string>("idle");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [currentStage, setCurrentStage] = useState<string>("");
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectDelayMs = useRef(2000);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);
  const isProcessingRef = useRef(false);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log("WebSocket connected to Veritas backend.");
        setActiveStatus("idle");
        setError(null);
        reconnectDelayMs.current = 2000;
      };

      ws.current.onmessage = (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data) as WebSocketMessage;
          
          if (payload.status === "alert") {
            setAlerts((prev) => (payload.data ? [payload.data as AlertItem, ...prev] : prev));
          } else if (payload.status === "processing") {
            const message = payload.message || payload.stage || "Processing...";
            setActiveStatus(message);
            isProcessingRef.current = true;
            
            if (payload.progress !== undefined) {
              setProgress(payload.progress);
            }
            
            if (payload.stage !== undefined) {
              setCurrentStage(payload.stage);
            }
            
          } else if (payload.status === "complete") {
            if (payload.data) {
              setStreamData((prev) => [payload.data as QueryResponse, ...prev]);
            }
            setActiveStatus("complete");
            setProgress(100);
            setCurrentStage("complete");
            isProcessingRef.current = false;
          } else if (payload.status === "error") {
            const errMsg = typeof payload.error === 'string' ? payload.error : payload.error?.message;
            setError(errMsg || "Streaming request failed.");
            setActiveStatus("error");
            setProgress(0);
            isProcessingRef.current = false;
          }
        } catch {
          console.error("Message parsing failed.");
        }
      };

      ws.current.onclose = () => {
        setActiveStatus("disconnected");
        isProcessingRef.current = false;
        if (!shouldReconnect.current) {
          return;
        }
        console.warn("WebSocket disconnected. Reconnecting...");
        reconnectTimer.current = setTimeout(() => connect(), reconnectDelayMs.current);
        reconnectDelayMs.current = Math.min(reconnectDelayMs.current * 1.5, 10000);
      };

      ws.current.onerror = (err) => {
        console.error("WebSocket error.", err);
        setError("WebSocket connection failed.");
        isProcessingRef.current = false;
      };
    } catch (e) {
      console.error("Failed to connect WebSocket.", e);
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
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  const sendQuery = useCallback((query: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      setStreamData([]);
      setAlerts([]);
      setError(null);
      setProgress(0);
      setCurrentStage("");
      setActiveStatus("transmitting");
      isProcessingRef.current = true;
      ws.current.send(JSON.stringify({ query }));
    } else {
      setError("WebSocket is not connected.");
      console.warn("WebSocket not connected.");
    }
  }, []);

  return { 
    streamData, 
    alerts, 
    activeStatus, 
    error, 
    progress,
    currentStage,
    sendQuery 
  };
};
