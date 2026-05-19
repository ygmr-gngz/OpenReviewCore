import uuid
from datetime import datetime
from typing import Optional


class MemoryStore:
    """
    Geçici analiz saklama sistemi.

    Veriler uygulama çalıştığı sürece bellekte tutulur.
    Uygulama yeniden başlatılırsa veriler silinir.

    Faz 9'da bu sınıf PostgreSQL implementasyonuyla değiştirilecek.
    Aynı arayüz (save, get, list, clear) korunacak —
    main.py ve diğer servisler değişmeyecek.
    """

    def __init__(self):
        # id → analiz kaydı
        self._store: dict[str, dict] = {}

    def save(self, result: dict) -> str:
        """
        Analiz sonucunu saklar ve benzersiz ID döndürür.

        ID otomatik üretilir ve result'a eklenir.
        Oluşturulma zamanı da otomatik eklenir.
        """

        analysis_id = str(uuid.uuid4())

        record = {
            "id":         analysis_id,
            "created_at": datetime.utcnow().isoformat(),
            **result,
        }

        self._store[analysis_id] = record

        return analysis_id

    def get(self, analysis_id: str) -> Optional[dict]:
        """
        ID ile analiz kaydını getirir.
        Bulunamazsa None döner.
        """

        return self._store.get(analysis_id)

    def list(self, limit: int = 10) -> list[dict]:
        """
        Son yapılan analizleri döndürür.
        En yeni önce gelir.
        """

        records = list(self._store.values())

        # En yeni analiz başta olsun
        records.sort(key=lambda r: r["created_at"], reverse=True)

        return records[:limit]

    def delete(self, analysis_id: str) -> bool:
        """
        Belirli bir analizi siler.
        Başarılıysa True, bulunamazsa False döner.
        """

        if analysis_id not in self._store:
            return False

        del self._store[analysis_id]
        return True

    def clear(self) -> None:
        """
        Tüm kayıtları temizler.
        Uygulama kapanışında lifespan tarafından çağrılır.
        """

        self._store.clear()

    def count(self) -> int:
        """
        Toplam kayıt sayısını döndürür.
        """

        return len(self._store)