#!/usr/bin/env python3
import asyncio
import sys

from core.conversation_layer import ConversationLayer

async def async_main():
    print("Initializing FRIDAY...")
    layer = ConversationLayer()
    await layer.initialize()
    print("Hello Boss. FRIDAY online. Type 'stop' or 'exit' to quit.")

    while True:
        try:
            user_input = input("\nYou: ")
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ['exit', 'quit', 'stop']:
                print("FRIDAY: Shutting down. Goodbye Boss.")
                break
            
            print("FRIDAY:", end=" ", flush=True)
            async for chunk in layer.process_query_stream(user_input):
                print(chunk, end="", flush=True)
            print()
            
        except (KeyboardInterrupt, EOFError):
            print("\nFRIDAY: Shutting down. Goodbye Boss.")
            break
        except Exception as e:
            print(f"\n[Error]: {e}")

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
