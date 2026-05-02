import { useCallback, useState, useRef } from "react";

interface SSEOptions {
  voiceMode?: boolean;
}

interface SSEReturn {
  streamingText: string;
  isStreaming: boolean;
  tier: string | null;
  model: string | null;
  error: string | null;
  streamQuery: (query: string, options?: SSEOptions) => Promise<void>;
  resetStream: () => void;
}

export const useSSE = (baseUrl: string): SSEReturn => {
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [tier, setTier] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const streamQuery = useCallback(async (query: string, options: SSEOptions = {}) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setStreamingText("");
    setIsStreaming(true);
    setError(null);
    setTier(null);
    setModel(null);

    try {
      const response = await fetch(`${baseUrl}/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-KEY": "anonymous", // Default for local dev
        },
        body: JSON.stringify({
          query,
          voice_mode: options.voiceMode || false,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("Response body reader not available");
      }

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            const eventType = line.split("\n")[0].replace("event: ", "").trim();
            const dataLine = line.split("\n")[1];
            if (dataLine && dataLine.startsWith("data: ")) {
              const data = JSON.parse(dataLine.replace("data: ", ""));
              
              if (eventType === "meta") {
                setTier(data.tier);
                setModel(data.model);
              } else if (eventType === "token") {
                setStreamingText((prev) => prev + data.t);
              } else if (eventType === "done") {
                setIsStreaming(false);
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Stream aborted");
      } else {
        console.error("SSE Error:", err);
        setError(err.message || "Streaming failed");
        setIsStreaming(false);
      }
    }
  }, [baseUrl]);

  const resetStream = useCallback(() => {
    setStreamingText("");
    setIsStreaming(false);
    setTier(null);
    setModel(null);
    setError(null);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  return {
    streamingText,
    isStreaming,
    tier,
    model,
    error,
    streamQuery,
    resetStream,
  };
};
