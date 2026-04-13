import { useState, useEffect, useRef } from 'react';

export const useWebSocket = (url: string) => {
  const [streamData, setStreamData] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [activeStatus, setActiveStatus] = useState<string>("idle");
  const ws = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(2000);

  const connect = () => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log("WebSocket actively integrated to Veritas backend.");
        setActiveStatus("idle");
        reconnectDelay.current = 2000;
      };
      
      ws.current.onmessage = (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.status === "alert") {
            setAlerts((prev: any[]) => [payload.data, ...prev]);
          } else if (payload.status === "processing") {
            setActiveStatus(payload.message);
          } else if (payload.status === "complete") {
            setStreamData((prev: any[]) => [payload.data, ...prev]);
            setActiveStatus("complete");
          }
        } catch (err) {
          console.error("Transmission decoding failed gracefully.");
        }
      };

      ws.current.onclose = () => {
        setActiveStatus("disconnected");
        console.warn("WebSocket stream severed. Reconnecting organically limits...");
        setTimeout(() => connect(), reconnectDelay.current);
        reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 10000); // Backoff mapping to 10s max natively
      };

      ws.current.onerror = (err) => {
         console.error("WebSocket edge crash.", err);
      };
    } catch (e) {
      console.error("Failed to allocate socket bounds natively.", e);
    }
  };

  useEffect(() => {
    connect();
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendQuery = (query: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      // Clear previous outputs seamlessly natively
      setStreamData([]); 
      setAlerts([]);
      setActiveStatus("transmitting");
      ws.current.send(JSON.stringify({ query }));
    } else {
      console.warn("Attempting query logic but stream disconnected organically.");
    }
  };

  return { streamData, alerts, activeStatus, sendQuery };
};
