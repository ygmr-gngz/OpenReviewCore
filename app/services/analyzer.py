from app.services.metrics import calculate_metrics
from app.services.risk_engine import calculate_risk_score
from app.services.llm_service import analyze_with_llm
from app.services.github_service import fetch_repo_files
from app.utils.code_cleaner import clean_code, is_empty


# ─────────────────────────────────────────
# TEK DOSYA ANALİZİ — Faz 1-6
# ─────────────────────────────────────────

def analyze_code(
    code: str,
    analysis_mode: str = "static",
    llm_provider: str = "none",
) -> dict:
    """
    Tek bir kod bloğunu analiz eder.

    Modlara göre davranış:
    - static : sadece statik analiz
    - llm    : statik analiz + LLM reasoning
    - hybrid : statik analiz + LLM reasoning
    """

    code = clean_code(code)

    if is_empty(code):
        return {"error": "Kod boş."}

    metrics     = calculate_metrics(code)
    risk_result = calculate_risk_score(metrics)

    static_result = {
        "metrics":       metrics,
        "risk_analysis": risk_result,
    }

    if analysis_mode in ("llm", "hybrid"):
        llm_result = analyze_with_llm(code, static_result, llm_provider)
        return {
            "analysis_mode": analysis_mode,
            "llm_provider":  llm_provider,
            "static_result": static_result,
            "llm_result":    llm_result,
        }

    return {
        "analysis_mode": analysis_mode,
        "llm_provider":  llm_provider,
        "static_result": static_result,
    }


# ─────────────────────────────────────────
# REPO ANALİZİ — Faz 7
# ─────────────────────────────────────────

def analyze_repo(
    github_url: str,
    max_files: int = 25,
    file_extensions: list[str] = None,
    analysis_mode: str = "static",
    llm_provider: str = "none",
) -> dict:
    """
    GitHub repo'sundaki tüm Python dosyalarını analiz eder.

    Her dosya ayrı ayrı analiz edilir.
    Sonunda repo genelinde özet risk skoru üretilir.
    """

    if file_extensions is None:
        file_extensions = [".py"]

    # 1 — Dosyaları GitHub'dan çek
    repo_data = fetch_repo_files(
        github_url      = github_url,
        max_files       = max_files,
        file_extensions = file_extensions,
    )

    if not repo_data["files"]:
        return {
            "error":       "Repoda analiz edilecek dosya bulunamadı.",
            "owner":       repo_data["owner"],
            "repo":        repo_data["repo"],
            "total_found": repo_data["total_found"],
        }

    # 2 — Her dosyayı analiz et
    file_results = []
    skipped      = []

    for file in repo_data["files"]:
        code = clean_code(file["content"])

        if is_empty(code):
            skipped.append(file["path"])
            continue

        metrics     = calculate_metrics(code)
        risk_result = calculate_risk_score(metrics)

        file_entry = {
            "path":          file["path"],
            "size":          file["size"],
            "static_result": {
                "metrics":       metrics,
                "risk_analysis": risk_result,
            },
        }

        # LLM sadece hybrid/llm modunda ve dosya başına çalışır
        # Büyük repolar için maliyetli olabilir — ileride batch yapılabilir
        if analysis_mode in ("llm", "hybrid"):
            llm_result = analyze_with_llm(
                code      = code,
                metrics   = file_entry["static_result"],
                provider  = llm_provider,
            )
            file_entry["llm_result"] = llm_result

        file_results.append(file_entry)

    # 3 — Repo geneli özet hesapla
    repo_summary = _calculate_repo_summary(file_results)

    return {
        "owner":         repo_data["owner"],
        "repo":          repo_data["repo"],
        "branch":        repo_data["branch"],
        "analysis_mode": analysis_mode,
        "llm_provider":  llm_provider,
        "stats": {
            "total_found":   repo_data["total_found"],
            "fetched":       repo_data["fetched"],
            "analyzed":      len(file_results),
            "skipped":       len(skipped),
            "skipped_files": skipped,
        },
        "repo_summary":  repo_summary,
        "file_results":  file_results,
    }


# ─────────────────────────────────────────
# REPO ÖZET HESAPLAMA
# ─────────────────────────────────────────

def _calculate_repo_summary(file_results: list[dict]) -> dict:
    """
    Tüm dosyaların risk skorlarından repo geneli özet üretir.
    """

    if not file_results:
        return {}

    scores = [
        f["static_result"]["risk_analysis"]["final_risk_score"]
        for f in file_results
        if "static_result" in f
    ]

    if not scores:
        return {}

    avg_score = round(sum(scores) / len(scores), 2)
    max_score = max(scores)

    # Repo risk seviyesi — en yüksek dosya skoru üzerinden belirlenir
    if max_score >= 90:
        repo_risk_level = "critical"
    elif max_score >= 75:
        repo_risk_level = "high"
    elif max_score >= 40:
        repo_risk_level = "medium"
    else:
        repo_risk_level = "low"

    # En riskli 3 dosya
    sorted_files = sorted(
        file_results,
        key=lambda f: f["static_result"]["risk_analysis"]["final_risk_score"],
        reverse=True,
    )
    riskiest = [
        {
            "path":       f["path"],
            "risk_score": f["static_result"]["risk_analysis"]["final_risk_score"],
            "risk_level": f["static_result"]["risk_analysis"]["risk_level"],
        }
        for f in sorted_files[:3]
    ]

    return {
        "average_risk_score": avg_score,
        "max_risk_score":     max_score,
        "repo_risk_level":    repo_risk_level,
        "riskiest_files":     riskiest,
        "total_files":        len(file_results),
    }