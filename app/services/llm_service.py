from openai import OpenAI
import requests
from app.config import settings


def analyze_with_llm(code: str, metrics: dict, provider: str) -> dict:
    """
    Kodu LLM'e gönderir, açıklama üretir.
    """

    if provider == "openai":
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "Sen bir kod analiz uzmanısın."},
                {"role": "user", "content": f"Bu kodu analiz et:\n{code}"}
            ]
        )
        return {
            "status": "success",
            "provider": "openai",
            "explanation": response.choices[0].message.content
        }

    elif provider == "ollama":
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": f"Bu kodu analiz et:\n{code}",
                "stream": False
            }
        )
        return {
            "status": "success",
            "provider": "ollama",
            "explanation": response.json()["response"]
        }

    else:
        return {
            "status": "skipped",
            "provider": "none",
            "explanation": None
        }