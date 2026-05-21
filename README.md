# OpenReviewCore

> Yapay zeka destekli kod risk analiz platformu — statik analiz, matematiksel metrikler ve LLM akıl yürütme tek bir pipeline'da.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![Testler](https://img.shields.io/badge/Testler-Geçiyor-brightgreen)
![Lisans](https://img.shields.io/badge/Lisans-MIT-green)
![Durum](https://img.shields.io/badge/Durum-Aktif%20Geliştirme-orange)

---

## Ne Yapar?

OpenReviewCore, Python kodunu analiz eder ve ölçülebilir bir risk skoru üretir.

Tek bir API çağrısıyla şunları öğrenirsin:

- Kodun ne kadar karmaşık olduğunu
- Bakımının ne kadar zor olduğunu
- Güvenlik açığı içerip içermediğini
- Lint sorunları olup olmadığını
- Genel risk seviyesini: `düşük`, `orta`, `yüksek`, `kritik`

Amaç sadece bir LLM'e kod gönderip cevap almak değil — **mühendislik odaklı, açıklanabilir ve ölçülebilir** bir kod inceleme sistemi kurmak.

---

## Özellikler

- Cyclomatic Complexity, Maintainability Index, Halstead ve Raw Metrics (Radon)
- Lint ve kod kalitesi analizi (Ruff)
- Statik güvenlik açığı tespiti (Bandit)
- Güvenlik örüntüsü taraması (`eval`, `exec`, hardcoded secret vb.)
- Ağırlıklı risk skorlama sistemi — 0 ile 100 arası
- Modüler servis mimarisi — genişletmesi kolay
- FastAPI backend — otomatik Swagger dokümantasyonu
- Docker desteği
- Hybrid mod desteği: statik analiz + LLM reasoning (yakında)

---

## Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- pip

### Kurulum

```bash
# Repoyu klonla
git clone https://github.com/kullaniciadin/openreviewcore.git
cd openreviewcore

# Sanal ortam oluştur
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# API'yi başlat
uvicorn app.main:app --reload
```

API adresi: `http://127.0.0.1:8000`
Swagger dokümantasyonu: `http://127.0.0.1:8000/docs`

### Docker ile Çalıştır

```bash
docker build -t openreviewcore .
docker run -p 8000:8000 openreviewcore
```

---

## Kullanım

### Kod Analizi

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def foo(x):\n    if x > 0:\n        return eval(x)\n    return x",
    "analysis_mode": "static",
    "llm_provider": "none"
  }'
```

### Örnek Yanıt

```json
{
  "message": "Kod analizi tamamlandı.",
  "input_type": "code",
  "analysis_mode": "static",
  "llm_provider": "none",
  "result": {
    "static_result": {
      "metrics": {
        "radon": {
          "cyclomatic_complexity": 2.0,
          "maintainability_index": 74.31,
          "halstead": {
            "volume": 45.2,
            "difficulty": 4.5,
            "bugs_delivered": 0.015
          },
          "raw": {
            "loc": 4,
            "sloc": 4,
            "comments": 0
          }
        },
        "security_patterns": {
          "detected_patterns": ["eval_usage"],
          "security_issue_count": 1
        },
        "bandit": {
          "issue_count": 1,
          "issues": [
            {
              "test_id": "B307",
              "severity": "MEDIUM",
              "confidence": "HIGH",
              "line": 3
            }
          ]
        }
      },
      "risk_analysis": {
        "final_risk_score": 42.5,
        "risk_breakdown": {
          "complexity_risk": 10.0,
          "maintainability_risk": 25.69,
          "security_risk": 25.0,
          "ruff_risk": 0.0,
          "bandit_risk": 20.0
        },
        "risk_level": "medium"
      }
    }
  }
}
```

---

## Risk Skorlama

Risk skoru beş kaynağın ağırlıklı toplamıdır:

| Kaynak | Ağırlık |
|---|---|
| Cyclomatic Complexity | %25 |
| Maintainability Index | %25 |
| Güvenlik Örüntüleri | %30 |
| Ruff Lint | %10 |
| Bandit Güvenlik | %10 |

| Skor | Seviye |
|---|---|
| 0 – 39 | `düşük` |
| 40 – 74 | `orta` |
| 75 – 89 | `yüksek` |
| 90 – 100 | `kritik` |

---

## Proje Yapısı

```
openreviewcore/
│
├── app/
│   ├── main.py              # FastAPI uygulaması ve endpointler
│   ├── schemas.py           # Request / response modelleri
│   ├── config.py            # Ortam değişkenleri ve ayarlar
│   │
│   ├── services/
│   │   ├── analyzer.py      # Orkestrasyon — tüm servisleri yönetir
│   │   ├── metrics.py       # Radon, Ruff, Bandit, güvenlik örüntüleri
│   │   ├── risk_engine.py   # Ağırlıklı risk skoru hesaplama
│   │   ├── llm_service.py   # LLM entegrasyonu (yakında aktif)
│   │   └── chat_service.py  # Analiz sonrası sohbet katmanı (yakında)
        └── github_service.py# GitHub repo dosya çekme servisi
│   │
│   ├── storage/
│   │   └── memory_store.py  # Geçici analiz saklama (Faz 9'da PostgreSQL)
│   │
│   └── utils/
│       └── code_cleaner.py  # Kod temizleme yardımcıları
│
├── tests/
│   ├── test_health.py
│   └── test_analyze.py
│
├── examples/
│   └── risky_code.py        # Yüksek riskli örnek kod
│
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## Ortam Değişkenleri

`.env.example` dosyasını `.env` olarak kopyala ve doldur:

```bash
cp .env.example .env
```

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `API_HOST` | Sunucu adresi | `0.0.0.0` |
| `API_PORT` | Sunucu portu | `8000` |
| `DEBUG` | Debug modu | `false` |
| `OPENAI_API_KEY` | OpenAI API anahtarı | — |
| `OPENAI_MODEL` | OpenAI model adı | `gpt-4o-mini` |
| `OLLAMA_BASE_URL` | Ollama servis adresi | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model adı | `llama3` |
| `MAX_FILE_SIZE` | Maksimum kod boyutu (karakter) | `50000` |

---

## Testleri Çalıştır

```bash
pytest tests/ -v
```

---

## Yol Haritası

## Yol Haritası

- [x] FastAPI backend — modüler servis mimarisi
- [x] Cyclomatic Complexity ve Maintainability Index (Radon)
- [x] Halstead Metrikleri ve Raw Metrics
- [x] Güvenlik örüntüsü tespiti
- [x] Ruff lint entegrasyonu
- [x] Bandit güvenlik entegrasyonu
- [x] Ağırlıklı risk skorlama motoru (4 seviye)
- [x] Swagger dokümantasyonu
- [x] Docker desteği
- [x] Otomatik testler
- [x] LLM akıl yürütme katmanı (OpenAI + Ollama)
- [x] Hybrid analiz modu (statik + LLM)
- [x] Analiz sonrası sohbet katmanı (TR/EN dil desteği)
- [x] GitHub repo analizi (recursive dosya tarama, repo risk skoru)
- [x] GitHub Actions CI/CD
- [x] Railway deployment (canlı API)
- [x] Streamlit UI (kod analizi, repo analizi, sohbet)
- [ ] PostgreSQL depolama
- [ ] Agent mimarisi — otonom kod inceleme

---

## Katkıda Bulunma

Katkılar memnuniyetle karşılanır.

1. Repoyu fork'la
2. Özellik dalı oluştur: `git checkout -b ozellik/ozellik-adin`
3. Açık ve yorumlu kod yaz
4. Testleri çalıştır: `pytest tests/ -v`
5. Pull request aç — değişikliği açıkla

**Kod stili:** `ruff check .` komutunu PR öncesi çalıştır.

---

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
