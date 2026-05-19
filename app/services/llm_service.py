from openai import OpenAI
import requests
from app.config import settings


# ─────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────

def _build_system_prompt() -> str:
    return """You are an experienced Software Security and Code Quality Analysis Expert.
Aynı zamanda deneyimli bir Yazılım Güvenliği ve Kod Kalite Analiz Uzmanısın.

You will receive / Sana aşağıdaki girdiler verilecek:
1. Source code / Kaynak kod
2. Static analysis results (SAST, lint, quality scan outputs, etc.) / Statik analiz sonuçları

IMPORTANT RULES / ÖNEMLİ KURALLAR:
- Do NOT recalculate static analysis findings.
- Statik analiz sonuçlarını tekrar üretmeye çalışma.
- Do NOT behave like you are running a new scan.
- Yeni analiz çalıştırıyormuş gibi davranma.
- Only interpret the provided findings together with the source code.
- Yalnızca verilen bulguları kaynak kod ile birlikte yorumla.
- Mention possible false positives explicitly.
- Olası yanlış pozitifleri açıkça belirt.
- Prioritize risks realistically.
- Riskleri gerçekçi şekilde önceliklendir.
- Use a technical but understandable language.
- Teknik ama anlaşılır bir dil kullan.
- Avoid unnecessary verbosity.
- Gereksiz uzun açıklamalardan kaçın.

Focus especially on / Özellikle şunlara dikkat et:
- Security vulnerabilities / Güvenlik açıkları
- Injection risks / Injection riskleri
- Authentication and authorization weaknesses / Kimlik doğrulama ve yetkilendirme problemleri
- Sensitive data exposure / Hassas veri yönetimi
- Hardcoded secrets or credentials / Hardcoded secret veya credential kullanımı
- Input validation issues / Input validation eksiklikleri
- Memory, null pointer, or resource leak risks / Memory leak, null pointer veya resource leak riskleri
- Concurrency and thread-safety issues / Concurrency ve thread-safety problemleri
- Performance bottlenecks / Performans darboğazları
- Code smells / Kod kokuları
- Maintainability concerns / Maintainability problemleri
- Improper exception handling / Hatalı exception handling
- Dependency or configuration risks / Dependency ve konfigürasyon riskleri

For each issue whenever possible:
- Assign a severity level (Low / Medium / High / Critical)
- Risk seviyesi belirt (Düşük / Orta / Yüksek / Kritik)
- Explain the issue technically / Teknik açıklama yap
- Describe the real-world impact / Gerçek hayattaki etkisini açıkla
- Provide concise remediation advice / Kısa ve uygulanabilir çözüm önerisi sun

ALWAYS structure the response exactly with these sections:
## Summary / Özet
## Identified Risks / Tespit Edilen Riskler
## Recommendations / Öneriler

Response language rules / Dil kuralları:
- If the user writes in Turkish, respond in Turkish.
- Eğer kullanıcı Türkçe yazıyorsa Türkçe cevap ver.
- If the user writes in English, respond in English.
- Eğer kullanıcı İngilizce yazıyorsa İngilizce cevap ver.

If there are inconsistencies between the code and the static analysis findings, explicitly mention them.
Kod ile statik analiz sonucu arasında tutarsızlık varsa özellikle belirt.
If a finding appears to be a false positive, clearly state it.
Bir bulgu yanlış pozitif görünüyorsa bunu net şekilde ifade et."""


def _build_user_prompt(code: str, metrics: dict) -> str:
    risk      = metrics.get("risk_analysis", {})
    breakdown = risk.get("risk_breakdown", {})
    raw       = metrics.get("raw_metrics", {})
    cc        = metrics.get("complexity", {})
    sec       = metrics.get("security_patterns", {})
    bandit    = metrics.get("bandit", {})
    ruff      = metrics.get("ruff", {})

    # Güvenlik örüntüleri
    detected = sec.get("detected_patterns", [])
    detected_str = ", ".join(detected) if detected else "None detected / Tespit edilmedi"

    # Bandit bulguları — ilk 5
    bandit_issues = bandit.get("issues", [])
    if bandit_issues:
        bandit_lines = []
        for issue in bandit_issues[:5]:
            bandit_lines.append(
                f"  - [{issue.get('issue_severity', '?')}] "
                f"{issue.get('issue_text', '')} "
                f"(line/satır {issue.get('line_number', '?')})"
            )
        bandit_str = "\n".join(bandit_lines)
    else:
        bandit_str = "  No findings / Bulgu yok."

    # Ruff lint bulguları — ilk 5
    ruff_issues = ruff.get("issues", [])
    if ruff_issues:
        ruff_lines = []
        for issue in ruff_issues[:5]:
            ruff_lines.append(
                f"  - [{issue.get('code', '?')}] "
                f"{issue.get('message', '')} "
                f"(line/satır {issue.get('line', '?')})"
            )
        ruff_str = "\n".join(ruff_lines)
    else:
        ruff_str = "  No findings / Bulgu yok."

    # Kod önizleme
    code_preview = code[:3000]
    truncated_note = "\n[Code truncated at 3000 chars / Kod 3000 karakterde kesildi]" if len(code) > 3000 else ""

    return f"""## Static Analysis Results / Statik Analiz Sonuçları

### Risk Score / Risk Skoru
- Final Score / Final Skor : {risk.get('final_risk_score', 'N/A')} / 100
- Risk Level / Risk Seviyesi : {risk.get('risk_level', 'N/A')}

### Risk Breakdown / Risk Dağılımı
- Complexity Risk      : {breakdown.get('complexity_risk', 'N/A')}
- Maintainability Risk : {breakdown.get('maintainability_risk', 'N/A')}
- Security Risk        : {breakdown.get('security_risk', 'N/A')}
- Ruff Risk            : {breakdown.get('ruff_risk', 'N/A')}
- Bandit Risk          : {breakdown.get('bandit_risk', 'N/A')}

### Code Metrics / Kod Metrikleri
- LOC (Lines of Code)        : {raw.get('loc', 'N/A')}
- SLOC (Source Lines)        : {raw.get('sloc', 'N/A')}
- Cyclomatic Complexity (avg): {cc.get('average_complexity', 'N/A')}
- Maintainability Index      : {metrics.get('maintainability', {}).get('mi', 'N/A')}

### Security Pattern Scan / Güvenlik Örüntü Taraması
Detected / Tespit Edilenler: {detected_str}

### Bandit SAST Findings / Bandit Güvenlik Bulguları
{bandit_str}

### Ruff Lint Findings / Ruff Lint Bulguları
{ruff_str}

---

## Source Code / Kaynak Kod

````python
{code_preview}
```{truncated_note}

---

Interpret the static analysis results above together with the source code.
Yukarıdaki statik analiz sonuçlarını kaynak kod ile birlikte yorumla."""


# ─────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────

def analyze_with_llm(code: str, metrics: dict, provider: str) -> dict:
    """
    Kodu ve statik analiz metriklerini LLM'e gönderir,
    yapılandırılmış açıklama üretir.
    """

    if provider == "none":
        return {
            "status":      "skipped",
            "provider":    "none",
            "explanation": None,
        }

    system_prompt = _build_system_prompt()
    user_prompt   = _build_user_prompt(code, metrics)

    if provider == "openai":
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return {
            "status":      "success",
            "provider":    "openai",
            "explanation": response.choices[0].message.content,
        }

    elif provider == "ollama":
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model":  settings.ollama_model,
                "prompt": full_prompt,
                "stream": False,
            },
            timeout=60,
        )
        return {
            "status":      "success",
            "provider":    "ollama",
            "explanation": response.json()["response"],
        }

    return {
        "status":      "error",
        "provider":    provider,
        "explanation": None,
    }
