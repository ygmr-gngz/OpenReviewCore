# Python image
FROM python:3.11-slim

# Container içindeki çalışma klasörü
WORKDIR /app

# Requirements dosyasını container'a kopyala
COPY requirements.txt .

# Paketleri kur
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını container'a kopyala
COPY . .

# Root olmayan kullanıcı oluştur ve geç
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# FastAPI portu
EXPOSE 8000

# Uygulamayı çalıştır
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]