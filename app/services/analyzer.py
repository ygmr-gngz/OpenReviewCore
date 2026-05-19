from app.services.metrics import calculate_metrics
from app.services.risk_engine import calculate_risk_score
from app.services.llm_service import analyze_with_llm
from app.utils.code_cleaner import clean_code, is_empty


def analyze_code(code: str, analysis_mode: str = "static", llm_provider: str = "none") -> dict:
    """
    Ana analiz akışı.

    Modlara göre davranış:
    - static : sadece statik analiz çalışır
    - llm    : sadece LLM reasoning çalışır
    - hybrid : statik analiz + LLM reasoning birlikte çalışır
    """

    # Kodu temizle
    code = clean_code(code)

    # Boş kod kontrolü
    if is_empty(code):
        return {"error": "Kod boş."}

    # — Static analiz — her modda çalışır
    metrics     = calculate_metrics(code)
    risk_result = calculate_risk_score(metrics)

    static_result = {
        "metrics":       metrics,
        "risk_analysis": risk_result,
    }

    # — LLM modu —
    if analysis_mode == "llm":
        llm_result = analyze_with_llm(code, metrics, llm_provider)
        return {
            "analysis_mode": analysis_mode,
            "llm_provider":  llm_provider,
            "static_result": static_result,
            "llm_result":    llm_result,
        }

    # — Hybrid mod —
    if analysis_mode == "hybrid":
        llm_result = analyze_with_llm(code, metrics, llm_provider)
        return {
            "analysis_mode": analysis_mode,
            "llm_provider":  llm_provider,
            "static_result": static_result,
            "llm_result":    llm_result,
        }

    # — Static mod (default) —
    return {
        "analysis_mode": analysis_mode,
        "llm_provider":  llm_provider,
        "static_result": static_result,
    }