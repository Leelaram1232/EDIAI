import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_groq():
    from app.core.ai_provider import get_ai_provider
    provider = get_ai_provider()
    # Override model for testing
    provider.model = "llama-3.3-70b-versatile"
    print("AI Provider:", provider.__class__.__name__)
    print("Model being used:", provider.model)
    if provider.client:
        print("API Key loaded (masked):", provider.client.api_key[:10] + "..." + provider.client.api_key[-5:])
        print("Base URL:", getattr(provider.client, "_base_url", "None"))
    else:
        print("Client is None! Connection not initialized.")
        return
    
    print("\nSending a test prompt to Groq...")
    try:
        response = await provider.generate(
            system_prompt="You are a helpful ITX expert.",
            user_prompt="Explain what a Type Tree is in IBM ITX in one sentence."
        )
        print("\nResponse from Groq:")
        print(response)
    except Exception as e:
        print("Error encountered:", e)

if __name__ == "__main__":
    asyncio.run(test_groq())
