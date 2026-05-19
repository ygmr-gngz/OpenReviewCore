import requests
from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Uygulama ayarları.

    Öncelik sırası:
    1. Sistem ortam değişkenleri (production, Docker)
    2. .env dosyası (local development)
    3. Buradaki default değerler
    """

    # ─────────────────────────────────────────
    # API
    # ─────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    debug: bool   = Field(default=False)

    # ─────────────────────────────────────────
    # OpenAI
    # ─────────────────────────────────────────
    openai_api_key: str = Field(default="")
    openai_model: str   = Field(default="gpt-4o-mini")

    # ─────────────────────────────────────────
    # Ollama
    # ─────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str    = Field(default="llama3")

    # ─────────────────────────────────────────
    # GitHub (Faz 7)
    # ─────────────────────────────────────────
    github_token: str = Field(default="")

    # ─────────────────────────────────────────
    # Analiz Limitleri
    # ─────────────────────────────────────────
    max_file_size: int  = Field(default=50000)
    max_repo_files: int = Field(default=25)

    # ─────────────────────────────────────────
    # Varsayılan Analiz Ayarları
    # ─────────────────────────────────────────
    default_analysis_mode: str  = Field(default="static")
    default_llm_provider: str   = Field(default="none")

    # ─────────────────────────────────────────
    # Storage (Faz 9)
    # ─────────────────────────────────────────
    database_url: str        = Field(default="")
    enable_memory_store: bool = Field(default=True)

    model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
)

# ─────────────────────────────────────────
# BAĞLANTI DOĞRULAMA
# ─────────────────────────────────────────

def check_openai(settings: Settings) -> dict:
    """
    OpenAI API key'in varlığını kontrol eder.
    Gerçek bir API çağrısı yapmaz, sadece key dolumu kontrol eder.
    """

    has_key = bool(settings.openai_api_key)

    return {
        "available": has_key,
        "model": settings.openai_model if has_key else None,
        "message": "API key mevcut." if has_key else "OPENAI_API_KEY tanımlı değil.",
    }


def check_ollama(settings: Settings) -> dict:
    """
    Ollama servisine gerçek bir HTTP isteği gönderir.
    Servis ayaktaysa available: True döner.
    """

    try:
        response = requests.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=3,
        )

        if response.status_code == 200:
            return {
                "available": True,
                "model": settings.ollama_model,
                "message": "Ollama servisi çalışıyor.",
            }

        return {
            "available": False,
            "model": None,
            "message": f"Ollama beklenmedik yanıt döndürdü: {response.status_code}",
        }

    except requests.exceptions.ConnectionError:
        return {
            "available": False,
            "model": None,
            "message": f"Ollama'ya bağlanılamadı: {settings.ollama_base_url}",
        }

    except requests.exceptions.Timeout:
        return {
            "available": False,
            "model": None,
            "message": "Ollama bağlantısı zaman aşımına uğradı.",
        }


def resolve_llm_provider(settings: Settings) -> str:
    """
    LLM provider 'auto' seçildiğinde hangisinin kullanılacağına karar verir.

    Öncelik:
    1. OpenAI key varsa → openai
    2. Ollama çalışıyorsa → ollama
    3. İkisi de yoksa → none
    """

    if settings.default_llm_provider != "auto":
        return settings.default_llm_provider

    openai_check = check_openai(settings)
    if openai_check["available"]:
        return "openai"

    ollama_check = check_ollama(settings)
    if ollama_check["available"]:
        return "ollama"

    return "none"


def get_status(settings: Settings) -> dict:
    """
    Tüm bağlantı durumlarını tek seferde döndürür.
    /health endpointinde kullanılabilir.
    """

    return {
        "openai": check_openai(settings),
        "ollama": check_ollama(settings),
        "resolved_llm_provider": resolve_llm_provider(settings),
        "analysis_mode": settings.default_analysis_mode,
        "debug": settings.debug,
    }


# Projenin her yerinden erişim:
# from app.config import settings
settings = Settings()