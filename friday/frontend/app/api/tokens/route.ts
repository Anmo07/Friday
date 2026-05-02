import { NextResponse } from 'next/server';
import { Readable } from 'stream';

export const GET = async (request: Request) => {
  const { searchParams } = new URL(request.url);
  const text = searchParams.get('text') ?? 'Hello, Friday!';

  // Simulate token generation – split into words
  const words = text.split(' ');
  let index = 0;

  const stream = new ReadableStream({
    async start(controller) {
      const interval = setInterval(() => {
        if (index >= words.length) {
          clearInterval(interval);
          controller.close();
          return;
        }
        const word = words[index];
        const event = {
          type: 'token',
          content: word,
          timestamp: Date.now(),
        };
        // SSE format: "data: {...}\n\n"
        const data = `data: ${JSON.stringify(event)}\n\n`;
        controller.enqueue(data);
        index++;
      }, 200); // 200ms per token ~ 5 tokens/sec
      return () => clearInterval(interval);
    },
  });

  return new NextResponse(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
};
