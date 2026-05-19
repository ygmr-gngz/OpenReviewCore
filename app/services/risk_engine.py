def calculate_risk_score(metrics: dict) -> dict:
    """
    Analiz metriklerinden 0-100 arası risk skoru üretir.

    Skor kaynakları ve ağırlıklar:
    - Complexity risk      : %25
    - Maintainability risk : %25
    - Security risk        : %30
    - Ruff risk            : %10
    - Bandit risk          : %10
    """

    # — Radon metrikleri —
    radon           = metrics.get("radon", {})
    complexity      = radon.get("cyclomatic_complexity", 0)
    maintainability = radon.get("maintainability_index", 100)

    # — Security pattern —
    security_issue_count = metrics.get("security_patterns", {}).get("security_issue_count", 0)

    # — Ruff —
    ruff_issue_count = metrics.get("ruff", {}).get("issue_count", 0)

    # — Bandit — severity bazlı ağırlıklandırma
    # HIGH → 3 puan, MEDIUM → 2 puan, LOW → 1 puan
    bandit_issues = metrics.get("bandit", {}).get("issues", [])
    bandit_severity_score = sum(
        3 if i.get("severity") == "HIGH"   else
        2 if i.get("severity") == "MEDIUM" else
        1
        for i in bandit_issues
    )

    # — Risk hesaplamaları —
    complexity_risk      = min(complexity * 5, 100)
    maintainability_risk = max(0, 100 - maintainability)
    security_risk        = min(security_issue_count * 25, 100)
    ruff_risk            = min(ruff_issue_count * 5, 100)
    bandit_risk          = min(bandit_severity_score * 10, 100)

    # — Ağırlıklı final skor —
    final_score = (
          complexity_risk      * 0.25
        + maintainability_risk * 0.25
        + security_risk        * 0.30
        + ruff_risk            * 0.10
        + bandit_risk          * 0.10
    )

    return {
        "final_risk_score": round(final_score, 2),
        "risk_breakdown": {
            "complexity_risk":      round(complexity_risk, 2),
            "maintainability_risk": round(maintainability_risk, 2),
            "security_risk":        round(security_risk, 2),
            "ruff_risk":            round(ruff_risk, 2),
            "bandit_risk":          round(bandit_risk, 2),
        },
        "risk_level": get_risk_level(final_score),
    }


def get_risk_level(score: float) -> str:
    """
    Sayısal risk skorunu okunabilir seviyeye çevirir.

    90 - 100 : critical
    75 -  89 : high
    40 -  74 : medium
     0 -  39 : low
    """

    if score >= 90:
        return "critical"

    if score >= 75:
        return "high"

    if score >= 40:
        return "medium"

    return "low"