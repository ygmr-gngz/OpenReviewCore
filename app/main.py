from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, get_status
from app.schemas import AnalyzeRequest, ChatRequest
from app.services.analyzer import analyze_code, analyze_repo
from app.storage.memory_store import MemoryStore
from app.services.chat_service import chat_with_analysis


# ─────────────────────────────────────────
# UYGULAMA YAŞAM DÖNGÜSÜ
# ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama başlarken ve kapanırken çalışır.

    Başlangıçta:
    - MemoryStore başlatılır
    - Bağlantı durumları kontrol edilir

    Kapanışta:
    - Açık bağlantılar temizlenir
    """

    app.state.store = MemoryStore()
    app.state.status = get_status(settings)

    yield

    app.state.store.clear()


# ─────────────────────────────────────────
# UYGULAMA
# ─────────────────────────────────────────

app = FastAPI(
    title="OpenReviewCore",
    description="Yapay zeka destekli kod risk analiz platformu",
    version="0.1.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────
# CORS — Faz 11 React frontend için
# ─────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Production'da spesifik origin verilecek
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# TEMEL ENDPOINTler
# ─────────────────────────────────────────

@app.get("/", tags=["Genel"])
def root():
    """
    API'nin çalışıp çalışmadığını hızlıca kontrol eder.
    """
    return {
        "message": "OpenReviewCore API is running",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Genel"])
def health_check():
    """
    Tüm servis bağlantılarının durumunu döndürür.

    Kontrol edilenler:
    - OpenAI API key varlığı
    - Ollama servis erişilebilirliği
    - Aktif LLM provider
    - Debug modu
    """
    return {
        "status": "ok",
        "services": get_status(settings),
    }


# ─────────────────────────────────────────
# ANALİZ ENDPOINTİ — Faz 1-7
# ─────────────────────────────────────────

@app.post("/analyze", tags=["Analiz"])
def analyze(request: AnalyzeRequest):
    """
    Python kodunu veya GitHub reposunu analiz eder, risk raporu döndürür.

    Desteklenen modlar:
    - static : Sadece statik analiz (Radon, Ruff, Bandit)
    - llm    : Sadece LLM reasoning
    - hybrid : Statik analiz + LLM reasoning

    Desteklenen girdi tipleri:
    - code        : Direkt kod metni
    - github_repo : GitHub repo URL'i
    """

    # ── GitHub repo analizi ──────────────────
    if request.input_type == "github_repo":
        if not request.github_url:
            raise HTTPException(
                status_code=400,
                detail="input_type 'github_repo' seçildiğinde github_url zorunludur.",
            )

        result = analyze_repo(
            github_url      = request.github_url,
            max_files       = request.max_files or 25,
            file_extensions = request.file_extensions or [".py"],
            analysis_mode   = request.analysis_mode,
            llm_provider    = request.llm_provider,
        )

        app.state.store.save(result)

        return {
            "message":       "Repo analizi tamamlandı.",
            "input_type":    request.input_type,
            "analysis_mode": request.analysis_mode,
            "llm_provider":  request.llm_provider,
            "result":        result,
        }

    # ── Direkt kod analizi ───────────────────
    if not request.code or not request.code.strip():
        raise HTTPException(
            status_code=400,
            detail="input_type 'code' seçildiğinde code alanı zorunludur.",
        )

    if len(request.code) > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"Kod boyutu limiti aşıldı. Maksimum: {settings.max_file_size} karakter.",
        )

    result = analyze_code(
        code          = request.code,
        analysis_mode = request.analysis_mode,
        llm_provider  = request.llm_provider,
    )

    app.state.store.save(result)

    return {
        "message":       "Kod analizi tamamlandı.",
        "input_type":    request.input_type,
        "analysis_mode": request.analysis_mode,
        "llm_provider":  request.llm_provider,
        "result":        result,
    }


# ─────────────────────────────────────────
# SOHBET ENDPOINTİ — Faz 8
# ─────────────────────────────────────────

@app.post("/chat", tags=["Sohbet"])
def chat(request: ChatRequest):
    """
    Analiz sonrası kullanıcıyla konuşma katmanı.

    Kullanıcı analiz ID'si ile birlikte soru gönderir.
    Sistem analiz bağlamını bilerek cevap üretir.

    Örnek:
    - "Bu kod neden riskli?"
    - "eval kullanımı nasıl düzeltilir?"
    """

    analysis = app.state.store.get(request.analysis_id)

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Analiz bulunamadı: {request.analysis_id}",
        )

    response = chat_with_analysis(
        message       = request.message,
        analysis      = analysis,
        llm_provider  = request.llm_provider,
    )

    return {
        "analysis_id": request.analysis_id,
        "message":     request.message,
        "response":    response,
    }


# ─────────────────────────────────────────
# GEÇMİŞ ENDPOINTİ — Faz 9
# ─────────────────────────────────────────

@app.get("/history", tags=["Geçmiş"])
def get_history(limit: int = 10):
    """
    Son yapılan analizlerin listesini döndürür.

    Şu an memory store kullanıyor.
    Faz 9'da PostgreSQL'e taşınacak.
    """

    history = app.state.store.list(limit=limit)

    return {
        "count":    len(history),
        "analyses": history,
    }


@app.get("/history/{analysis_id}", tags=["Geçmiş"])
def get_analysis(analysis_id: str):
    """
    Belirli bir analizin detaylarını döndürür.
    """

    analysis = app.state.store.get(analysis_id)

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Analiz bulunamadı: {analysis_id}",
        )

    return analysis