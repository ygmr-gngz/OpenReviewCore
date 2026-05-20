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

    if file_extensions is None:
        file_extensions = [".py"]

    # Ollama Railway'de çalışmaz — repo analizinde static'e düş
    if llm_provider == "ollama":
        analysis_mode = "static"
        llm_provider  = "none"

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

        if analysis_mode in ("llm", "hybrid"):
            llm_result = analyze_with_llm(
                code     = code,
                metrics  = file_entry["static_result"],
                provider = llm_provider,
            )
            file_entry["llm_result"] = llm_result

        file_results.append(file_entry)

    # 3 — Repo geneli özet hesapla
    repo_summary = _calculate_repo_summary(file_results)

    # 4 — Repo geneli LLM özeti üret
    repo_llm_summary = None
    if analysis_mode in ("llm", "hybrid") and llm_provider not in ("none", "ollama"):
        repo_llm_summary = _generate_repo_llm_summary(
            file_results = file_results,
            repo_summary = repo_summary,
            provider     = llm_provider,
        )

    return {
        "owner":             repo_data["owner"],
        "repo":              repo_data["repo"],
        "branch":            repo_data["branch"],
        "analysis_mode":     analysis_mode,
        "llm_provider":      llm_provider,
        "stats": {
            "total_found":   repo_data["total_found"],
            "fetched":       repo_data["fetched"],
            "analyzed":      len(file_results),
            "skipped":       len(skipped),
            "skipped_files": skipped,
        },
        "repo_summary":      repo_summary,
        "repo_llm_summary":  repo_llm_summary,
        "file_results":      file_results,
    }


# ─────────────────────────────────────────
# REPO ÖZET HESAPLAMA
# ─────────────────────────────────────────

def _calculate_repo_summary(file_results: list[dict]) -> dict:

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

    if max_score >= 90:
        repo_risk_level = "critical"
    elif max_score >= 75:
        repo_risk_level = "high"
    elif max_score >= 40:
        repo_risk_level = "medium"
    else:
        repo_risk_level = "low"

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


# ─────────────────────────────────────────
# REPO LLM ÖZETİ
# ─────────────────────────────────────────

def _generate_repo_llm_summary(
    file_results: list[dict],
    repo_summary: dict,
    provider: str,
) -> dict:
    """
    En riskli 3 dosyanın statik metriklerini birleştirip
    repo geneli LLM özeti üretir.
    """

    sorted_files = sorted(
        file_results,
        key=lambda f: f["static_result"]["risk_analysis"]["final_risk_score"],
        reverse=True,
    )
    top_files = sorted_files[:3]

    combined_metrics = {
        "risk_analysis": {
            "final_risk_score": repo_summary.get("average_risk_score", 0),
            "risk_level":       repo_summary.get("repo_risk_level", "?"),
            "risk_breakdown": {
                "security_risk":        _avg_breakdown(top_files, "security_risk"),
                "maintainability_risk": _avg_breakdown(top_files, "maintainability_risk"),
                "complexity_risk":      _avg_breakdown(top_files, "complexity_risk"),
                "bandit_risk":          _avg_breakdown(top_files, "bandit_risk"),
                "ruff_risk":            _avg_breakdown(top_files, "ruff_risk"),
            },
        },
        "complexity": {
            "average_complexity": _avg_metric(top_files, "complexity", "average_complexity"),
        },
        "security_patterns": {
            "detected_patterns":    _collect_patterns(top_files),
            "security_issue_count": sum(
                f["static_result"]["metrics"]
                .get("security_patterns", {})
                .get("security_issue_count", 0)
                for f in top_files
            ),
        },
        "bandit": {
            "issues": _collect_bandit_issues(top_files),
        },
    }

    top_path = top_files[0]["path"] if top_files else "bilinmiyor"
    top_code = (
        f"# Repo: en riskli dosya → {top_path}\n"
        f"# Toplam analiz edilen dosya: {repo_summary.get('total_files', '?')}\n"
        f"# Repo risk seviyesi: {repo_summary.get('repo_risk_level', '?')}\n"
        f"# (Dosya içerikleri repo analizinde ayrı ayrı tarandı)"
    )

    return analyze_with_llm(
        code     = top_code,
        metrics  = combined_metrics,
        provider = provider,
    )


# ─────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────

def _avg_breakdown(files: list[dict], key: str) -> float:
    vals = [
        f["static_result"]["risk_analysis"]
        .get("risk_breakdown", {})
        .get(key, 0)
        for f in files
        if "static_result" in f
    ]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _avg_metric(files: list[dict], section: str, key: str) -> float:
    vals = [
        f["static_result"]["metrics"]
        .get(section, {})
        .get(key, 0)
        for f in files
        if "static_result" in f
    ]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _collect_patterns(files: list[dict]) -> list[str]:
    patterns = set()
    for f in files:
        detected = (
            f["static_result"]["metrics"]
            .get("security_patterns", {})
            .get("detected_patterns", [])
        )
        patterns.update(detected)
    return list(patterns)


def _collect_bandit_issues(files: list[dict]) -> list[dict]:
    issues = []
    for f in files:
        issues.extend(
            f["static_result"]["metrics"]
            .get("bandit", {})
            .get("issues", [])[:2]
        )
    return issues[:5]