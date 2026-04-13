import { useState, useEffect, useRef } from 'react';

export const useWebSocket = (url: string) => {
  const [streamData, setStreamData] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [activeStatus, setActiveStatus] = useState<string>("idle");
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => console.log("WebSocket actively integrated to Veritas backend.");
    
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

    ws.current.onclose = () => console.log("Edge socket decoupled natively.");
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendQuery = (query: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      setActiveStatus("transmitting");
      ws.current.send(JSON.stringify({ query }));
    }
  };

  return { streamData, alerts, activeStatus, sendQuery };
};
