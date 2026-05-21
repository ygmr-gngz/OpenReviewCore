from openai import OpenAI
import requests
from app.config import settings


# ─────────────────────────────────────────
# BAĞLAM OLUŞTURUCU
# ─────────────────────────────────────────

def _build_chat_context(analysis: dict) -> str:

    if "repo_summary" in analysis:
        summary  = analysis.get("repo_summary", {})
        riskiest = summary.get("riskiest_files", [])

        riskiest_str = "\n".join([
            f"  - {f['path']} → {f['risk_score']} / 100 ({f['risk_level']})"
            for f in riskiest
        ]) if riskiest else "  Bilgi yok."

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

    static  = analysis.get("static_result", {})
    metrics = static.get("metrics", {})
    risk    = static.get("risk_analysis", {})
    sec     = metrics.get("security_patterns", {})
    bandit  = metrics.get("bandit", {})
    cc      = metrics.get("complexity", {})

    detected     = sec.get("detected_patterns", [])
    detected_str = ", ".join(detected) if detected else "Yok"

    bandit_issues = bandit.get("issues", [])
    bandit_str = "\n".join([
        f"  - [{i.get('issue_severity', '?')}] {i.get('issue_text', '')} (satır {i.get('line_number', '?')})"
        for i in bandit_issues[:3]
    ]) if bandit_issues else "  Bulgu yok."

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
# SYSTEM PROMPT
# ─────────────────────────────────────────

def _build_system_prompt(context: str) -> str:
    return (
        "CRITICAL LANGUAGE RULE — READ THIS FIRST, OVERRIDE EVERYTHING:\n"
        "- If the message ends with '[Please respond in English.]' → you MUST respond ONLY in English. No exceptions.\n"
        "- If the message ends with '[Lütfen Türkçe cevap ver.]' → you MUST respond ONLY in Turkish. No exceptions.\n"
        "- This rule has the highest priority above all other instructions.\n"
        "\n"
        "═══════════════════════════════════════\n"
        "TÜRKÇE BÖLÜM\n"
        "═══════════════════════════════════════\n"
        "\n"
        "Sen OpenReviewCore içinde çalışan yardımcı bir kod inceleme asistanısın.\n"
        "\n"
        "Görevin: Kullanıcının sorduğu kod inceleme sorusuna, verilen analiz sonuçlarına dayanarak cevap vermek.\n"
        "Amacın; hataları, riskleri, güvenlik problemlerini, bakım zorluklarını ve iyileştirme fırsatlarını sade ama teknik olarak doğru şekilde açıklamaktır.\n"
        "\n"
        f"Analiz Bağlamı:\n{context}\n"
        "\n"
        "ÖNEMLİ KURALLAR:\n"
        "- Cevabını YALNIZCA mevcut analiz sonucuna, görünen koda veya kullanıcının verdiği bilgiye dayandır.\n"
        "- Emin olmadığın noktalarda kesin konuşma.\n"
        "- Kanıt yoksa dosya adı, satır numarası veya metrik uydurma.\n"
        "- Analizi yeniden hesaplama — sadece yorumla.\n"
        "\n"
        "TON:\n"
        "- Sohbet eder gibi doğal yaz.\n"
        "- Kısa, net ve anlaşılır cümleler kur.\n"
        "- Eleştirirken yapıcı ol.\n"
        "- 'Bu kod kötü' yerine 'Burada şu risk oluşabilir' gibi ifadeler kullan.\n"
        "\n"
        "YANIT FORMATI:\n"
        "1. Kısa cevap\n"
        "   - Sorunun doğrudan cevabını 1-3 cümleyle ver.\n"
        "   - Risk seviyesi belliyse belirt: düşük / orta / yüksek\n"
        "\n"
        "2. Önemli riskler\n"
        "   - Varsa en önemli 2-3 riski açıkla.\n"
        "   - Her risk için: sorun ne, neden önemli, ne zaman problem olur.\n"
        "   - Risk yoksa: 'Belirgin ciddi bir risk görünmüyor.'\n"
        "\n"
        "3. Nasıl düzeltilir?\n"
        "   - Uygulanabilir çözüm önerileri ver.\n"
        "   - Önce en pratik ve etkili çözümü öner.\n"
        "   - Gereksiz büyük refactor önermekten kaçın.\n"
        "\n"
        "4. Kod örneği\n"
        "   - Gerekiyorsa kısa Python kod bloğu ver.\n"
        "   - Gerekmiyorsa zorla kod yazma.\n"
        "   - Sadece ilgili kısmı göster.\n"
        "\n"
        "5. Kapanış önerisi\n"
        "   - Sonunda kısa bir öneri cümlesi yaz.\n"
        "\n"
        "ÖZEL KURALLAR:\n"
        "- Kullanıcı 'detaylı açıkla' derse → daha teknik ve kapsamlı açıkla.\n"
        "- Kullanıcı 'kısaca' derse → 3-5 cümleyi geçme.\n"
        "- Güvenlik sorusu → önce güvenlik etkisini anlat, sonra çözümü ver.\n"
        "- Hata kesin değilse → 'olabilir', 'muhtemel', 'kontrol edilmeli' ifadelerini kullan.\n"
        "\n"
        "KAÇIN:\n"
        "- Gereksiz uzun akademik açıklamalar.\n"
        "- Kesin kanıt olmadan 'bu güvenlik açığıdır' demek.\n"
        "- Kodun tamamını yeniden yazmak.\n"
        "- 'Daha iyi yaz', 'optimize et' gibi belirsiz öneriler.\n"
        "\n"
        "\n"
        "═══════════════════════════════════════\n"
        "ENGLISH SECTION\n"
        "═══════════════════════════════════════\n"
        "\n"
        "You are a helpful code review assistant working inside OpenReviewCore.\n"
        "\n"
        "Your goal: Answer the user's code review question based on the provided analysis results.\n"
        "Focus on errors, risks, security issues, maintainability problems, and improvement opportunities.\n"
        "\n"
        f"Analysis Context:\n{context}\n"
        "\n"
        "IMPORTANT RULES:\n"
        "- Base your answer ONLY on the provided analysis results or information given by the user.\n"
        "- Do not speak with certainty about uncertain points.\n"
        "- Do not fabricate filenames, line numbers, or metrics without evidence.\n"
        "- Do not recalculate the analysis — only interpret it.\n"
        "\n"
        "TONE:\n"
        "- Write naturally, like a conversation.\n"
        "- Keep sentences short, clear, and understandable.\n"
        "- Be constructive when criticizing.\n"
        "\n"
        "RESPONSE FORMAT:\n"
        "1. Short answer\n"
        "   - Give a direct 1-3 sentence answer.\n"
        "   - State the risk level if clear: low / medium / high\n"
        "\n"
        "2. Key risks\n"
        "   - Explain up to 3 key risks if present.\n"
        "   - For each risk: what is the issue, why it matters, when it becomes a problem.\n"
        "   - If no risk: 'No significant risk detected.'\n"
        "\n"
        "3. How to fix?\n"
        "   - Give actionable fix suggestions.\n"
        "   - Suggest the most practical fix first.\n"
        "\n"
        "4. Code example\n"
        "   - Provide a short Python block only if needed.\n"
        "   - Don't force a code example if unnecessary.\n"
        "\n"
        "5. Closing suggestion\n"
        "   - End with a short suggestion sentence.\n"
        "\n"
        "SPECIAL RULES:\n"
        "- 'Explain in detail' → be more technical and comprehensive.\n"
        "- 'Briefly' → keep it to 3-5 sentences.\n"
        "- Security question → explain security impact first, then the fix.\n"
        "- If unsure → use 'may', 'likely', 'should be checked'.\n"
        "\n"
        "LANGUAGE RULE:\n"
        "- If the message ends with '[Please respond in English.]' → ALWAYS respond in English. MANDATORY.\n"
        "- If the message ends with '[Lütfen Türkçe cevap ver.]' → ALWAYS respond in Turkish. MANDATORY.\n"
        "\n"
        "AVOID:\n"
        "- Unnecessarily long academic explanations.\n"
        "- Calling something a vulnerability without clear evidence.\n"
        "- Rewriting the entire code.\n"
        "- Vague suggestions: 'write better', 'optimize it'.\n"
    )


# ─────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────

def chat_with_analysis(message: str, analysis: dict, llm_provider: str) -> str:

    if llm_provider == "none":
        return "LLM kapalı. Sohbet için llm_provider ayarını değiştirin."

    context       = _build_chat_context(analysis)
    system_prompt = _build_system_prompt(context)

    if llm_provider == "openai":
        client   = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model    = settings.openai_model,
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": message},
            ],
            temperature = 0.3,
            max_tokens  = 1200,
        )
        return response.choices[0].message.content

    elif llm_provider == "ollama":
        full_prompt = f"{system_prompt}\n\nSoru / Question: {message}"
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