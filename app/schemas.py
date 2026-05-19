from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────
# ENUM'LAR
# ─────────────────────────────────────────

class InputType(str, Enum):
    """
    Kullanıcının ne gönderdiğini belirtir.
    code        : direkt kod metni
    github_repo : GitHub repo URL'i (Faz 7)
    """
    code        = "code"
    github_repo = "github_repo"


class AnalysisMode(str, Enum):
    """
    Hangi analiz modunun çalışacağını belirtir.
    static : sadece statik analiz
    llm    : sadece LLM reasoning
    hybrid : ikisi birlikte (ana hedef mod)
    """
    static = "static"
    llm    = "llm"
    hybrid = "hybrid"


class LLMProvider(str, Enum):
    """
    Hangi LLM sağlayıcısının kullanılacağını belirtir.
    openai : OpenAI API
    ollama : lokal model
    auto   : API key varsa OpenAI, yoksa Ollama
    none   : LLM tamamen kapalı
    """
    openai = "openai"
    ollama = "ollama"
    auto   = "auto"
    none   = "none"


class RiskLevel(str, Enum):
    """
    Risk seviyeleri.
    """
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


# ─────────────────────────────────────────
# ANALİZ REQUEST — Faz 1-7
# ─────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """
    /analyze endpointine gelen isteğin modeli.
    """

    # Girdi tipi
    input_type: InputType = Field(
        default=InputType.code,
        description="Girdi tipi: 'code' veya 'github_repo'",
    )

    # Direkt kod analizi için
    code: Optional[str] = Field(
        default=None,
        description="Analiz edilecek Python kodu",
    )

    # GitHub repo analizi için — Faz 7
    github_url: Optional[str] = Field(
        default=None,
        description="GitHub repo URL'i. Örnek: https://github.com/user/repo",
    )
    max_files: Optional[int] = Field(
        default=25,
        ge=1,
        le=100,
        description="Repo analizinde taranacak maksimum dosya sayısı",
    )
    file_extensions: Optional[list[str]] = Field(
        default=[".py"],
        description="Taranacak dosya uzantıları",
    )

    # Analiz ayarları
    analysis_mode: AnalysisMode = Field(
        default=AnalysisMode.static,
        description="Analiz modu: 'static', 'llm', 'hybrid'",
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.none,
        description="LLM sağlayıcı: 'openai', 'ollama', 'auto', 'none'",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "input_type": "code",
                    "code": "def foo(x):\n    if x > 0:\n        return eval(x)\n    return x",
                    "analysis_mode": "static",
                    "llm_provider": "none",
                }
            ]
        }
    }


# ─────────────────────────────────────────
# SOHBET REQUEST — Faz 8
# ─────────────────────────────────────────

class ChatRequest(BaseModel):
    """
    /chat endpointine gelen isteğin modeli.

    Kullanıcı daha önce yapılmış bir analizin ID'siyle
    soru gönderir. Sistem analiz bağlamını bilerek cevap üretir.
    """

    analysis_id: str = Field(
        description="Daha önce yapılmış analizin ID'si",
    )
    message: str = Field(
        description="Kullanıcının sorusu",
        min_length=1,
        max_length=2000,
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.auto,
        description="Sohbet için kullanılacak LLM sağlayıcı",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "analysis_id": "abc-123",
                    "message": "Bu kod neden riskli?",
                    "llm_provider": "auto",
                }
            ]
        }
    }


# ─────────────────────────────────────────
# RESPONSE MODELLERİ — Faz 9
# ─────────────────────────────────────────

class RiskBreakdown(BaseModel):
    complexity_risk:      float
    maintainability_risk: float
    security_risk:        float
    ruff_risk:            float
    bandit_risk:          float


class RiskAnalysis(BaseModel):
    final_risk_score: float
    risk_breakdown:   RiskBreakdown
    risk_level:       RiskLevel


class AnalysisRecord(BaseModel):
    """
    Memory store ve PostgreSQL'de tutulan analiz kaydı.
    /history endpointinin döndürdüğü model.
    """

    id:            str
    created_at:    datetime
    input_type:    InputType
    analysis_mode: AnalysisMode
    llm_provider:  LLMProvider
    risk_analysis: RiskAnalysis
    code_preview:  Optional[str] = Field(
        default=None,
        description="Kodun ilk 200 karakteri — önizleme için",
    )