import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_NIM_API_KEY")
base_url = "https://integrate.api.nvidia.com/v1"

async def test_model(model_id):
    print(f"Testing model: {model_id}")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Try with thinking enabled (as in current code)
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1024,
        "extra_body": {
            "thinking": {"type": "enabled"},
            "reasoning_split": True,
            "chat_template_kwargs": {
                "thinking": True,
                "enable_thinking": True,
                "reasoning_split": True,
                "clear_thinking": False,
            }
        }
    }
    
    print("Testing with thinking=enabled...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
            else:
                print("Success!")
        except Exception as e:
            print(f"Exception: {e}")
        
        # Try without thinking
        print("\nTesting without thinking...")
        payload.pop("extra_body")
        try:
            response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
            else:
                print("Success without thinking!")
        except Exception as e:
            print(f"Exception: {e}")

async def main():
    await test_model("z-ai/glm4.7")
    print("-" * 20)
    await test_model("deepseek-ai/deepseek-v3.1")
    print("-" * 20)
    await test_model("deepseek-ai/deepseek-v3.2")

if __name__ == "__main__":
    asyncio.run(main())
