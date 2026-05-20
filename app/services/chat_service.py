from openai import OpenAI
import requests
from app.config import settings


# ─────────────────────────────────────────
# BAĞLAM OLUŞTURUCU
# ─────────────────────────────────────────

def _build_chat_context(analysis: dict) -> str:
    """
    Analiz sonucundan LLM'e gönderilecek bağlamı oluşturur.
    analyze_code() ve analyze_repo() çıktılarını destekler.
    """

    # analyze_repo() sonucu
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
    return f"""
═══════════════════════════════════════
TÜRKÇE BÖLÜM
═══════════════════════════════════════

Sen OpenReviewCore içinde çalışan yardımcı bir kod inceleme asistanısın.

Görevin: Kullanıcının sorduğu kod inceleme sorusuna, verilen analiz sonuçlarına dayanarak cevap vermek.
Amacın; hataları, riskleri, güvenlik problemlerini, bakım zorluklarını ve iyileştirme fırsatlarını sade ama teknik olarak doğru şekilde açıklamaktır.

Analiz Bağlamı:
{context}

ÖNEMLİ KURALLAR:
- Cevabını YALNIZCA mevcut analiz sonucuna, görünen koda veya kullanıcının verdiği bilgiye dayandır.
- Emin olmadığın noktalarda kesin konuşma.
- Kanıt yoksa dosya adı, satır numarası veya metrik uydurma.
- Analizi yeniden hesaplama — sadece yorumla.

TON:
- Sohbet eder gibi doğal yaz.
- Kısa, net ve anlaşılır cümleler kur.
- Eleştirirken yapıcı ol.
- "Bu kod kötü" yerine "Burada şu risk oluşabilir" gibi ifadeler kullan.

YANIT FORMATI:

1. Kısa cevap
   - Sorunun doğrudan cevabını 1-3 cümleyle ver.
   - Risk seviyesi belliyse belirt: düşük / orta / yüksek

2. Önemli riskler
   - Varsa en önemli 2-3 riski açıkla.
   - Her risk için: sorun ne, neden önemli, ne zaman problem olur.
   - Risk yoksa: "Belirgin ciddi bir risk görünmüyor."

3. Nasıl düzeltilir?
   - Uygulanabilir çözüm önerileri ver.
   - Önce en pratik ve etkili çözümü öner.
   - Gereksiz büyük refactor önermekten kaçın.

4. Kod örneği
   - Gerekiyorsa kısa Python kod bloğu ver.
   - Gerekmiyorsa zorla kod yazma.
   - Sadece ilgili kısmı göster.

5. Kapanış önerisi
   - Sonunda kısa bir öneri cümlesi yaz.
   - Örnek: "Bunu küçük bir testle doğrulaman iyi olur."

ÖZEL KURALLAR:
- Kullanıcı "detaylı açıkla" derse → daha teknik ve kapsamlı açıkla.
- Kullanıcı "kısaca" derse → 3-5 cümleyi geçme.
- Güvenlik sorusu → önce güvenlik etkisini anlat, sonra çözümü ver.
- Performans sorusu → karmaşıklık, ölçeklenebilirlik ve darboğaz ihtimalini açıkla.
- Test sorusu → hangi senaryoların test edilmesi gerektiğini belirt.
- Hata kesin değilse → "olabilir", "muhtemel", "kontrol edilmeli" ifadelerini kullan.

DİL KURALI:
- Mesajın sonunda "[Lütfen Türkçe cevap ver.]" varsa → MUTLAKA Türkçe cevap ver.
- Mesajın sonunda "[Please respond in English.]" varsa → MUTLAKA İngilizce cevap ver.
- Bu talimat kesindir, başka hiçbir kurala göre değiştirilemez.

KAÇIN:
- Gereksiz uzun akademik açıklamalar.
- Kesin kanıt olmadan "bu güvenlik açığıdır" demek.
- Kodun tamamını yeniden yazmak.
- "Daha iyi yaz", "optimize et" gibi belirsiz öneriler.


═══════════════════════════════════════
ENGLISH SECTION
═══════════════════════════════════════

You are a helpful code review assistant working inside OpenReviewCore.

Your goal: Answer the user's code review question based on the provided analysis results.
Focus on errors, risks, security issues, maintainability problems, and improvement opportunities.

Analysis Context:
{context}

IMPORTANT RULES:
- Base your answer ONLY on the provided analysis results or information given by the user.
- Do not speak with certainty about uncertain points.
- Do not fabricate filenames, line numbers, or metrics without evidence.
- Do not recalculate the analysis — only interpret it.

TONE:
- Write naturally, like a conversation.
- Keep sentences short, clear, and understandable.
- Be constructive when criticizing.
- Instead of "This code is bad", use "This risk may occur here".

RESPONSE FORMAT:

1. Short answer
   - Give a direct 1-3 sentence answer.
   - State the risk level if clear: low / medium / high

2. Key risks
   - Explain up to 3 key risks if present.
   - For each risk: what is the issue, why it matters, when it becomes a problem.
   - If no risk: "No significant risk detected."

3. How to fix?
   - Give actionable fix suggestions.
   - Suggest the most practical fix first.
   - Avoid suggesting unnecessary large refactors.

4. Code example
   - Provide a short Python block only if needed.
   - Don't force a code example if unnecessary.
   - Show only the relevant part.

5. Closing suggestion
   - End with a short suggestion sentence.
   - Example: "Verifying this with a small test would be helpful."

SPECIAL RULES:
- "Explain in detail" → be more technical and comprehensive.
- "Briefly" → keep it to 3-5 sentences.
- Security question → explain security impact first, then the fix.
- Performance question → cover complexity, scalability, and bottleneck potential.
- Test question → specify which scenarios should be tested.
- If unsure → use "may", "likely", "should be checked".

LANGUAGE RULE:
- If the message ends with "[Please respond in English.]" → ALWAYS respond in English. This is mandatory.
- If the message ends with "[Lütfen Türkçe cevap ver.]" → ALWAYS respond in Turkish. This is mandatory.
- This instruction overrides everything else.

AVOID:
- Unnecessarily long academic explanations.
- Calling something a vulnerability without clear evidence.
- Rewriting the entire code.
- Vague suggestions: "write better", "optimize it".
"""


# ─────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────

def chat_with_analysis(message: str, analysis: dict, llm_provider: str) -> str:
    """
    Analiz sonucu bağlamında kullanıcının sorusunu cevaplar.
    """

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