import asyncio
import httpx
import os

async def test_tts():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/v1/voice/stream",
                json={"text": "Hello, I am Friday. Testing speech recitation."},
                timeout=30
            )
            print(f"Status: {response.status_code}")
            print(f"Content Type: {response.headers.get('content-type')}")
            if response.status_code == 200:
                with open("test_audio.mp3", "wb") as f:
                    f.write(response.content)
                print("Audio saved to test_audio.mp3")
                os.system("afplay test_audio.mp3")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
