from openai import OpenAI
import requests
from app.config import settings


# ─────────────────────────────────────────
# BAĞLAM OLUŞTURUCU
# ─────────────────────────────────────────

def _build_chat_context(analysis: dict) -> str:
    """
    Analiz sonucundan LLM'e gönderilecek bağlamı oluşturur.

    analyze_code() ve analyze_repo() farklı yapılar döndürür —
    ikisini de destekler.
    """

    # analyze_repo() sonucu
    if "repo_summary" in analysis:
        summary  = analysis.get("repo_summary", {})
        riskiest = summary.get("riskiest_files", [])

        riskiest_str = ""
        if riskiest:
            lines = [
                f"  - {f['path']} → {f['risk_score']} / 100 ({f['risk_level']})"
                for f in riskiest
            ]
            riskiest_str = "\n".join(lines)
        else:
            riskiest_str = "  Bilgi yok."

        return f"""
Analiz tipi      : GitHub Repo Analizi
Repo             : {analysis.get('owner', '?')}/{analysis.get('repo', '?')}
Branch           : {analysis.get('branch', '?')}
Analiz modu      : {analysis.get('analysis_mode', '?')}

Repo Risk Özeti:
- Ortalama risk skoru : {summary.get('average_risk_score', 'N/A')} / 100
- Maksimum risk skoru : {summary.get('max_risk_score', 'N/A')} / 100
- Repo risk seviyesi  : {summary.get('repo_risk_level', 'N/A')}
- Analiz edilen dosya : {summary.get('total_files', 'N/A')}

En Riskli Dosyalar:
{riskiest_str}
""".strip()

    # analyze_code() sonucu
    static  = analysis.get("static_result", {})
    metrics = static.get("metrics", {})
    risk    = static.get("risk_analysis", {})
    sec     = metrics.get("security_patterns", {})
    bandit  = metrics.get("bandit", {})
    cc      = metrics.get("complexity", {})

    detected     = sec.get("detected_patterns", [])
    detected_str = ", ".join(detected) if detected else "Yok"

    bandit_issues = bandit.get("issues", [])
    if bandit_issues:
        bandit_lines = [
            f"  - [{i.get('issue_severity', '?')}] {i.get('issue_text', '')} (satır {i.get('line_number', '?')})"
            for i in bandit_issues[:3]
        ]
        bandit_str = "\n".join(bandit_lines)
    else:
        bandit_str = "  Bulgu yok."

    return f"""
Analiz tipi      : Kod Analizi
Analiz modu      : {analysis.get('analysis_mode', '?')}

Risk Skoru       : {risk.get('final_risk_score', 'N/A')} / 100
Risk Seviyesi    : {risk.get('risk_level', 'N/A')}
Cyclomatic CC    : {cc.get('average_complexity', 'N/A')}

Güvenlik Örüntüleri : {detected_str}

Bandit Bulguları:
{bandit_str}
""".strip()


# ─────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────

def chat_with_analysis(message: str, analysis: dict, llm_provider: str) -> str:
    """
    Analiz sonucu bağlamında kullanıcının sorusunu cevaplar.
    """

    if llm_provider == "none":
        return "LLM kapalı. Sohbet için llm_provider ayarını değiştirin."

    context        = _build_chat_context(analysis)
    system_content = (
        "Sen bir kod güvenlik ve kalite analiz uzmanısın. "
        "Aşağıdaki analiz sonucunu bağlam olarak kullan. "
        "Kullanıcının sorularını bu bağlama dayanarak cevapla. "
        "Analizi yeniden hesaplama — sadece yorumla. "
        "Türkçe yaz, teknik ama anlaşılır ol.\n\n"
        f"Analiz Bağlamı:\n{context}"
    )

    if llm_provider == "openai":
        client   = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model    = settings.openai_model,
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user",   "content": message},
            ],
            temperature = 0.3,
            max_tokens  = 800,
        )
        return response.choices[0].message.content

    elif llm_provider == "ollama":
        full_prompt = f"{system_content}\n\nSoru: {message}"
        response    = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json = {
                "model":  settings.ollama_model,
                "prompt": full_prompt,
                "stream": False,
            },
            timeout = 60,
        )
        return response.json()["response"]

    return "Desteklenmeyen LLM sağlayıcı."