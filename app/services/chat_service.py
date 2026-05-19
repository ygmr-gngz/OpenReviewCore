from openai import OpenAI
import requests
from app.config import settings


def chat_with_analysis(message: str, analysis: dict, llm_provider: str) -> str:
    """
    Analiz sonucu bağlamında kullanıcının sorusunu cevaplar.

    Kullanıcı analiz ID'siyle soru gönderir.
    Sistem analiz sonucunu LLM'e bağlam olarak verir.
    """

    # Analiz sonucunu LLM'e bağlam olarak hazırlıyoruz
    context = f"""
    Kod analiz sonucu:
    - Risk skoru: {analysis.get('risk_analysis', {}).get('final_risk_score')}
    - Risk seviyesi: {analysis.get('risk_analysis', {}).get('risk_level')}
    - Güvenlik sorunları: {analysis.get('metrics', {}).get('security_patterns', {}).get('detected_patterns')}
    """

    if llm_provider == "openai":
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": f"Sen bir kod analiz uzmanısın. İşte analiz sonucu:\n{context}"},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content

    elif llm_provider == "ollama":
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": f"Analiz sonucu:\n{context}\n\nSoru: {message}",
                "stream": False
            }
        )
        return response.json()["response"]

    else:
        return "LLM kapalı. Sohbet için llm_provider ayarını değiştirin."