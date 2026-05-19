"""
Bu dosya OpenReviewCore'un tespit edebileceği
riskli kod örüntülerini içerir.

Amaç:
- API'yi manuel test etmek
- Analizin doğru çalıştığını görmek
- Yeni katkıda bulunanlara örnek sunmak
"""

# ─────────────────────────────────────────
# YÜKSEK CYCLOMATİC COMPLEXİTY
# ─────────────────────────────────────────

def karmasik_fonksiyon(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            elif z == 0:
                return x + y
            else:
                return x
        elif y == 0:
            if z > 0:
                return z
            else:
                return 0
        else:
            return -1
    elif x == 0:
        if y > 0:
            return y
        else:
            return 0
    else:
        return -999


# ─────────────────────────────────────────
# GÜVENLİK RİSKLERİ
# ─────────────────────────────────────────

def guvenlik_riskleri(kullanici_girdisi):
    # eval kullanımı — kod enjeksiyonu riski
    sonuc = eval(kullanici_girdisi)

    # exec kullanımı — kod çalıştırma riski
    exec("print('merhaba')")

    # os.system kullanımı — shell komut riski
    import os
    os.system("ls -la")

    # subprocess riski
    import subprocess
    subprocess.run(["ls", "-la"])

    return sonuc


# ─────────────────────────────────────────
# HARDCODED SECRET'LAR
# ─────────────────────────────────────────

def veritabani_baglan():
    password = "super_secret_123"
    api_key = "sk-abc123xyz456"
    secret = "gizli_anahtar"

    return {
        "password": password,
        "api_key": api_key,
        "secret": secret,
    }


# ─────────────────────────────────────────
# BAKIMI ZOR KOD
# ─────────────────────────────────────────

def cok_uzun_fonksiyon(a,b,c,d,e,f,g,h):
    r1=a+b
    r2=c+d
    r3=e+f
    r4=g+h
    t1=r1*r2
    t2=r3*r4
    if t1>t2:
        if r1>r2:
            if a>b:
                return a
            else:
                return b
        else:
            return r1
    else:
        if t2>100:
            return t2
        else:
            return 0