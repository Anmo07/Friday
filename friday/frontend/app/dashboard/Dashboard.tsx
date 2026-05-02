'use client';

import { WaveformVisualizer } from './WaveformVisualizer';
import TokenStreamDisplay from './TokenStreamDisplay';
import { useEffect, useState } from 'react';

export function Dashboard() {
  // Simulated audio buffer (replace with real microphone/audio input)
  const [audioBuffer, setAudioBuffer] = useState<Float32Array | null>(null);
  // Simulated token stream text
  const [streamingText, setStreamingText] = useState('');

  useEffect(() => {
    // Mock audio data every second
    const interval = setInterval(() => {
      const buffer = new Float32Array(128);
      // Fill with random-ish data for demo
      for (let i = 0; i < buffer.length; i++) {
        buffer[i] = (Math.random() - 0.5) * 0.5;
      }
      setAudioBuffer(buffer);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Simulate SSE token stream subscription
  useEffect(() => {
    const eventSource = new EventSource('/api/tokens?text=' + encodeURIComponent('Hello, this is a test of the token streaming functionality.'));
    const processChunk = (chunk: string) => {
      const trimmed = chunk.trim();
      if (trimmed) {
        setStreamingText(prev => prev + trimmed);
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
  }, []);

  return (
    <div className="bg-gray-900 text-white w-full max-w-4xl p-6 space-y-8">
      {/* Waveform Visualizer */}
      <div className="flex justify-center">
        <WaveformVisualizer audioBuffer={audioBuffer ?? new Float32Array()} />
      </div>

      {/* Token Streaming Display */}
      <TokenStreamDisplay initialText={streamingText} />

      {/* Speaker Diarization Placeholder */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="p-3 bg-gray-800 rounded">
          <strong>Speaker 1</strong>: User
        </div>
        <div className="p-3 bg-gray-800 rounded">
          <strong>Speaker 2</strong>: Assistant
        </div>
      </div>

      {/* System Status Indicator */}
      <div className="flex items-center gap-2 text-xs">
        <span className="px-2 py-1 bg-blue-600 rounded">
          LISTENING
        </span>
      </div>
    </div>
  );
}
