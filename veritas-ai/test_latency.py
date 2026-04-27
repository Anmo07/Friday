import asyncio
import time
import timeit

async def test_llm():
    from models.multi_llm import get_fast_llm
    llm = get_fast_llm()
    start = time.time()
    first_token = None
    print("Sending prompt...")
    async for chunk in llm.astream("Hello! Short answer."):
        if not first_token:
            first_token = time.time()
            print(f"Time to first token: {first_token - start:.2f}s")
        print(chunk, end="", flush=True)
    print(f"\nTotal time: {time.time() - start:.2f}s")

asyncio.run(test_llm())
