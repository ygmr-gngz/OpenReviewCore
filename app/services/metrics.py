import subprocess
import tempfile
import json
import os

from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit
from radon.raw import analyze as raw_analyze


# ─────────────────────────────────────────
# SECURITY PATTERN DETECTION
# ─────────────────────────────────────────

def detect_security_patterns(code: str) -> dict:
    """
    Kod içinde basit güvenlik riski oluşturabilecek pattern'leri arar.
    İleride Bandit çıktısıyla birleştirilecek.
    """

    patterns = {
        "eval_usage": "eval(" in code,
        "exec_usage": "exec(" in code,
        "subprocess_usage": "subprocess" in code,
        "os_system_usage": "os.system" in code,
        "hardcoded_password": "password" in code.lower(),
        "hardcoded_secret": "secret" in code.lower(),
        "hardcoded_api_key": "api_key" in code.lower() or "apikey" in code.lower(),
    }

    detected_patterns = [
        name for name, found in patterns.items() if found
    ]

    return {
        "detected_patterns": detected_patterns,
        "security_issue_count": len(detected_patterns),
    }


# ─────────────────────────────────────────
# RUFF — LINT ANALİZİ
# ─────────────────────────────────────────

def run_ruff(code: str) -> dict:
    """
    Ruff ile lint analizi yapar.

    Geçici bir .py dosyası oluşturur, Ruff'ı subprocess ile çalıştırır,
    JSON çıktısını parse eder ve temizler.

    Ruff kurulu değilse ya da hata olursa boş sonuç döner.
    """

    # Kodu geçici bir dosyaya yazıyoruz.
    # Ruff dosya bazlı çalıştığı için bu gerekli.
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", tmp_path],
            capture_output=True,
            text=True,
        )

        issues = json.loads(result.stdout) if result.stdout.strip() else []

        return {
            "issue_count": len(issues),
            "issues": [
                {
                    "code": i.get("code"),
                    "message": i.get("message"),
                    "row": i.get("location", {}).get("row"),
                }
                for i in issues
            ],
        }

    except FileNotFoundError:
        # Ruff kurulu değil
        return {"issue_count": 0, "issues": [], "error": "ruff not installed"}

    except Exception as e:
        return {"issue_count": 0, "issues": [], "error": str(e)}

    finally:
        # Geçici dosyayı her durumda sil
        os.unlink(tmp_path)


# ─────────────────────────────────────────
# BANDIT — GÜVENLİK ANALİZİ
# ─────────────────────────────────────────

def run_bandit(code: str) -> dict:
    """
    Bandit ile statik güvenlik analizi yapar.

    Geçici .py dosyası oluşturur, Bandit'i JSON modda çalıştırır,
    severity ve confidence bilgilerini toplar.

    Bandit kurulu değilse ya da hata olursa boş sonuç döner.
    """

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            capture_output=True,
            text=True,
        )

        output = json.loads(result.stdout) if result.stdout.strip() else {}
        raw_results = output.get("results", [])

        return {
            "issue_count": len(raw_results),
            "issues": [
                {
                    "test_id": i.get("test_id"),
                    "issue_text": i.get("issue_text"),
                    "severity": i.get("issue_severity"),
                    "confidence": i.get("issue_confidence"),
                    "line": i.get("line_number"),
                }
                for i in raw_results
            ],
        }

    except FileNotFoundError:
        return {"issue_count": 0, "issues": [], "error": "bandit not installed"}

    except Exception as e:
        return {"issue_count": 0, "issues": [], "error": str(e)}

    finally:
        os.unlink(tmp_path)


# ─────────────────────────────────────────
# ANA METRİK HESAPLAMA
# ─────────────────────────────────────────

def calculate_metrics(code: str) -> dict:
    """
    Verilen Python kodu için tüm analiz metriklerini hesaplar.

    Metrikler:
    - Cyclomatic Complexity   : karar karmaşıklığı
    - Maintainability Index   : bakım yapılabilirlik skoru
    - Halstead Metrics        : hacim, zorluk, tahmini bug sayısı
    - Raw Metrics             : satır sayıları
    - Security Pattern        : basit pattern tarama
    - Ruff                    : lint analizi
    - Bandit                  : güvenlik analizi
    """

    # — Cyclomatic Complexity —
    complexity_results = cc_visit(code)

    if complexity_results:
        total_complexity = sum(item.complexity for item in complexity_results)
        average_complexity = total_complexity / len(complexity_results)
    else:
        average_complexity = 0

    # — Maintainability Index —
    maintainability_index = mi_visit(code, multi=True)

    # — Halstead Metrics —
    try:
        halstead = h_visit(code)
        # h_visit birden fazla fonksiyon varsa liste döner; toplamı alıyoruz.
        if halstead:
            total = halstead.total
            halstead_data = {
                "volume": round(total.volume, 2),
                "difficulty": round(total.difficulty, 2),
                "effort": round(total.effort, 2),
                "bugs_delivered": round(total.bugs, 4),
                "time_to_program_sec": round(total.time, 2),
            }
        else:
            halstead_data = {}
    except Exception:
        halstead_data = {}

    # — Raw Metrics —
    try:
        raw = raw_analyze(code)
        raw_data = {
            "loc": raw.loc,           # toplam satır
            "lloc": raw.lloc,         # mantıksal satır
            "sloc": raw.sloc,         # kod satırı (boş/yorum hariç)
            "comments": raw.comments, # yorum satırı
            "blank": raw.blank,       # boş satır
        }
    except Exception:
        raw_data = {}

    # — Security Pattern Detection —
    security_patterns = detect_security_patterns(code)

    # — Ruff —
    ruff_result = run_ruff(code)

    # — Bandit —
    bandit_result = run_bandit(code)

    return {
        "radon": {
            "cyclomatic_complexity": round(average_complexity, 2),
            "maintainability_index": round(maintainability_index, 2),
            "analyzed_blocks": len(complexity_results),
            "halstead": halstead_data,
            "raw": raw_data,
        },
        "security_patterns": security_patterns,
        "ruff": ruff_result,
        "bandit": bandit_result,
    }