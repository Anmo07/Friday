'use client';

import { useEffect, useState } from 'react';

export default function TokenStreamDisplay({ initialText }: { initialText: string }) {
  const [displayedText, setDisplayedText] = useState(initialText);

  useEffect(() => {
    const eventSource = new EventSource('/api/tokens?text=' + encodeURIComponent(initialText));
    const processChunk = (chunk: string) => {
      const trimmed = chunk.trim();
      if (trimmed) {
        setDisplayedText(prev => prev + trimmed);
      }
    };

    eventSource.onmessage = (e) => {
      processChunk(e.data);
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [initialText]);

  return (
    <div data-testid="token-stream" style={{ fontFamily: 'monospace', whiteSpace: 'pre' }}>
      {displayedText}
    </div>
  );
}
