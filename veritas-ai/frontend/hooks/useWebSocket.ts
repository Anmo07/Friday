import { useEffect, useRef, useState } from "react";

import { AlertItem, QueryResponse, WebSocketMessage } from "@/types/api";

export const useWebSocket = (url: string) => {
  const [streamData, setStreamData] = useState<QueryResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [activeStatus, setActiveStatus] = useState<string>("idle");
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectDelayMs = useRef(2000);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);

  const connect = () => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log("WebSocket actively integrated to Veritas backend.");
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
            setActiveStatus(payload.message || "processing");
          } else if (payload.status === "complete") {
            if (payload.data) {
              setStreamData((prev) => [payload.data as QueryResponse, ...prev]);
            }
            setActiveStatus("complete");
          } else if (payload.status === "error") {
            setError(payload.error?.message || "Streaming request failed.");
            setActiveStatus("error");
          }
        } catch {
          console.error("Transmission decoding failed gracefully.");
        }
      };

      ws.current.onclose = () => {
        setActiveStatus("disconnected");
        if (!shouldReconnect.current) {
          return;
        }
        console.warn("WebSocket stream severed. Reconnecting organically limits...");
        reconnectTimer.current = setTimeout(() => connect(), reconnectDelayMs.current);
        reconnectDelayMs.current = Math.min(reconnectDelayMs.current * 1.5, 10000);
      };

      ws.current.onerror = (err) => {
         console.error("WebSocket edge crash.", err);
         setError("WebSocket connection failed.");
      };
    } catch (e) {
      console.error("Failed to allocate socket bounds natively.", e);
    }
  };

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
  }, [url]);

  const sendQuery = (query: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      setStreamData([]); 
      setAlerts([]);
      setError(null);
      setActiveStatus("transmitting");
      ws.current.send(JSON.stringify({ query }));
    } else {
      setError("WebSocket is not connected.");
      console.warn("Attempting query logic but stream disconnected organically.");
    }
  };

  return { streamData, alerts, activeStatus, error, sendQuery };
};
