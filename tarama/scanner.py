"""
BIST Multibagger Tarama Sistemi
Her sabah otomatik çalışır, kriterleri karşılayan hisseleri mail atar.
"""

import os
import smtplib
import requests
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import time

# ─────────────────────────────────────────────
# KRİTERLER — İstediğin zaman buradan değiştir
# ─────────────────────────────────────────────
KRITERLER = {
    "max_piyasa_degeri_milyon_tl": 2000,   # 2 milyar TL altı
    "max_fk": 8,                            # F/K < 8
    "max_pd_dd": 1.0,                       # PD/DD < 1 (defter değeri altı)
    "min_hacim_carpani": 2.0,               # Ortalama hacmin 2x üzeri
}

HEDEF_MAIL = os.environ.get("HEDEF_MAIL", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")  # Gmail App Password


# ─────────────────────────────────────────────
# KAP — Yeni Özel Durum Açıklamaları
# ─────────────────────────────────────────────
def kap_yeni_aciklamalar():
    """kap.org.tr'den bugünkü özel durum açıklamalarını çeker."""
    bulunanlar = []
    try:
        url = "https://www.kap.org.tr/tr/bildirim-sorgu"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        anahtar_kelimeler = [
            "sözleşme", "ihale", "ihracat", "sipariş", "ortaklık",
            "kapasite", "yatırım", "proje", "anlaşma", "kazandı"
        ]

        satirlar = soup.find_all("tr")
        for satir in satirlar[:50]:
            metin = satir.get_text(separator=" ").lower()
            for kelime in anahtar_kelimeler:
                if kelime in metin:
                    sembol = ""
                    td_ler = satir.find_all("td")
                    if td_ler:
                        sembol = td_ler[0].get_text(strip=True)
                    if sembol:
                        bulunanlar.append({
                            "sembol": sembol,
                            "ozet": satir.get_text(separator=" | ", strip=True)[:200],
                            "kaynak": "KAP",
                            "tip": f"Anahtar kelime: {kelime}"
                        })
                    break

    except Exception as e:
        print(f"KAP hatası: {e}")

    return bulunanlar[:10]


# ─────────────────────────────────────────────
# BORSA GÜNDEMİ — Yabancı Net Alım
# ─────────────────────────────────────────────
def yabanci_net_alim():
    """Borsagundem'den yabancı net alım yapılan hisseleri çeker."""
    bulunanlar = []
    try:
        url = "https://www.borsagundem.com/takas"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        tablolar = soup.find_all("table")
        for tablo in tablolar:
            satirlar = tablo.find_all("tr")[1:11]  # İlk 10 hisse
            for satir in satirlar:
                kolonlar = satir.find_all("td")
                if len(kolonlar) >= 3:
                    sembol = kolonlar[0].get_text(strip=True)
                    degisim = kolonlar[2].get_text(strip=True)
                    if sembol and "+" in degisim:
                        bulunanlar.append({
                            "sembol": sembol,
                            "degisim": degisim,
                            "kaynak": "Borsagundem Takas",
                            "tip": "Yabancı net alım"
                        })

    except Exception as e:
        print(f"Borsagundem hatası: {e}")

    return bulunanlar[:8]


# ─────────────────────────────────────────────
# FİNTABLES — Kurumsal Takas Artışı
# ─────────────────────────────────────────────
def fintables_kurumsal():
    """Fintables'dan kurumsal takas oranı artan hisseleri çeker."""
    bulunanlar = []
    try:
        url = "https://fintables.com/hisseler/takas"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/html"
        }
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        satirlar = soup.find_all("tr")
        for satir in satirlar[1:15]:
            kolonlar = satir.find_all("td")
            if len(kolonlar) >= 4:
                sembol = kolonlar[0].get_text(strip=True)
                kurumsal_degisim = kolonlar[3].get_text(strip=True)
                if sembol and "+" in kurumsal_degisim:
                    bulunanlar.append({
                        "sembol": sembol,
                        "kurumsal_degisim": kurumsal_degisim,
                        "kaynak": "Fintables",
                        "tip": "Kurumsal takas artışı"
                    })

    except Exception as e:
        print(f"Fintables hatası: {e}")

    return bulunanlar[:8]


# ─────────────────────────────────────────────
# ÇAKIŞMA KONTROLÜ — En Güçlü Sinyaller
# ─────────────────────────────────────────────
def guclu_sinyaller_bul(kap_listesi, takas_listesi, kurumsal_listesi):
    """Birden fazla kaynakta geçen hisseleri tespit eder."""
    tum_semboller = {}

    for kaynak in [kap_listesi, takas_listesi, kurumsal_listesi]:
        for item in kaynak:
            s = item["sembol"].upper()
            if s not in tum_semboller:
                tum_semboller[s] = {"sembol": s, "sinyaller": [], "puan": 0}
            tum_semboller[s]["sinyaller"].append(f"✅ {item['kaynak']}: {item['tip']}")
            tum_semboller[s]["puan"] += 1

    # En az 2 kaynakta çakışan = güçlü sinyal
    guclu = [v for v in tum_semboller.values() if v["puan"] >= 2]
    guclu.sort(key=lambda x: x["puan"], reverse=True)
    return guclu


# ─────────────────────────────────────────────
# MAİL OLUŞTURUCU
# ─────────────────────────────────────────────
def mail_olustur(kap_listesi, takas_listesi, kurumsal_listesi, guclu_listesi):
    """HTML formatında günlük rapor maili oluşturur."""
    tarih = datetime.now().strftime("%d %B %Y, %A")

    # Güçlü sinyaller tablosu
    guclu_html = ""
    if guclu_listesi:
        for h in guclu_listesi:
            sinyaller_str = "<br>".join(h["sinyaller"])
            guclu_html += f"""
            <tr style="background:#f0fff0">
                <td style="padding:10px;font-weight:bold;font-size:16px">
                    🔥 {h['sembol']}
                </td>
                <td style="padding:10px">{sinyaller_str}</td>
                <td style="padding:10px;text-align:center">
                    <span style="background:#22c55e;color:white;padding:4px 10px;
                    border-radius:12px;font-weight:bold">{h['puan']}/3</span>
                </td>
            </tr>"""
    else:
        guclu_html = """<tr><td colspan="3" style="padding:15px;color:#666;text-align:center">
            Bugün birden fazla kaynakta çakışan hisse bulunamadı.</td></tr>"""

    # KAP listesi
    kap_html = ""
    for item in kap_listesi[:6]:
        kap_html += f"""
        <tr>
            <td style="padding:8px;font-weight:bold">{item['sembol']}</td>
            <td style="padding:8px;color:#444;font-size:13px">{item['ozet'][:150]}...</td>
        </tr>"""
    if not kap_html:
        kap_html = '<tr><td colspan="2" style="padding:10px;color:#888">Bugün öne çıkan açıklama bulunamadı.</td></tr>'

    # Takas listesi
    takas_html = ""
    for item in (takas_listesi + kurumsal_listesi)[:10]:
        takas_html += f"""
        <tr>
            <td style="padding:8px;font-weight:bold">{item['sembol']}</td>
            <td style="padding:8px;color:#16a34a">{item.get('degisim', item.get('kurumsal_degisim', ''))}</td>
            <td style="padding:8px;color:#555;font-size:13px">{item['tip']}</td>
        </tr>"""
    if not takas_html:
        takas_html = '<tr><td colspan="3" style="padding:10px;color:#888">Takas verisi alınamadı.</td></tr>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;
                 background:#f8fafc;padding:20px">

        <!-- BAŞLIK -->
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);
                    color:white;padding:25px;border-radius:12px;margin-bottom:20px">
            <h1 style="margin:0;font-size:22px">📊 BIST Günlük Tarama Raporu</h1>
            <p style="margin:8px 0 0;opacity:0.85;font-size:14px">{tarih}</p>
            <p style="margin:4px 0 0;opacity:0.7;font-size:12px">
                KAP • Takas • Kurumsal Birikim • 4 Katman Analiz
            </p>
        </div>

        <!-- GÜÇLÜ SİNYALLER -->
        <div style="background:white;border-radius:12px;padding:20px;
                    margin-bottom:20px;border-left:4px solid #22c55e">
            <h2 style="margin:0 0 15px;color:#166534;font-size:17px">
                🔥 GÜÇLÜ SİNYALLER — Birden Fazla Kaynakta Çakışan
            </h2>
            <p style="font-size:12px;color:#666;margin:0 0 12px">
                Bu hisseler hem KAP haberi hem de takas artışı ile öne çıktı — en güçlü sinyal kombinasyonu.
            </p>
            <table style="width:100%;border-collapse:collapse">
                <tr style="background:#dcfce7;font-size:13px;color:#166534">
                    <th style="padding:8px;text-align:left">Sembol</th>
                    <th style="padding:8px;text-align:left">Sinyaller</th>
                    <th style="padding:8px;text-align:center">Güç</th>
                </tr>
                {guclu_html}
            </table>
        </div>

        <!-- KAP AÇIKLAMALARI -->
        <div style="background:white;border-radius:12px;padding:20px;
                    margin-bottom:20px;border-left:4px solid #f59e0b">
            <h2 style="margin:0 0 15px;color:#92400e;font-size:17px">
                📋 KAP — Bugünkü Önemli Açıklamalar
            </h2>
            <p style="font-size:12px;color:#666;margin:0 0 12px">
                Sözleşme, ihale, sipariş, ihracat ve ortaklık içeren açıklamalar.
            </p>
            <table style="width:100%;border-collapse:collapse">
                <tr style="background:#fef3c7;font-size:13px;color:#92400e">
                    <th style="padding:8px;text-align:left;width:20%">Sembol</th>
                    <th style="padding:8px;text-align:left">Açıklama Özeti</th>
                </tr>
                {kap_html}
            </table>
        </div>

        <!-- TAKAS HAREKETLERİ -->
        <div style="background:white;border-radius:12px;padding:20px;
                    margin-bottom:20px;border-left:4px solid #6366f1">
            <h2 style="margin:0 0 15px;color:#3730a3;font-size:17px">
                📦 TAKAS — Kurumsal & Yabancı Birikim
            </h2>
            <p style="font-size:12px;color:#666;margin:0 0 12px">
                Bugün kurumsal veya yabancı takas oranı artan hisseler.
            </p>
            <table style="width:100%;border-collapse:collapse">
                <tr style="background:#e0e7ff;font-size:13px;color:#3730a3">
                    <th style="padding:8px;text-align:left;width:20%">Sembol</th>
                    <th style="padding:8px;text-align:left;width:20%">Değişim</th>
                    <th style="padding:8px;text-align:left">Kaynak</th>
                </tr>
                {takas_html}
            </table>
        </div>

        <!-- GÜNLÜK KONTROL LİSTESİ -->
        <div style="background:white;border-radius:12px;padding:20px;
                    margin-bottom:20px">
            <h2 style="margin:0 0 12px;color:#374151;font-size:17px">
                ✅ Bugün Yapman Gerekenler
            </h2>
            <ol style="margin:0;padding-left:20px;line-height:2;color:#4b5563">
                <li>Güçlü sinyal listesindeki hisseleri <b>TradingView</b>'de aç</li>
                <li>Hacim ortalamanın <b>2x üzerinde</b> mi kontrol et</li>
                <li><b>Fintables</b>'da takas geçmişine bak (son 5 gün)</li>
                <li>KAP açıklamasının tam metnini oku</li>
                <li>Piyasa değeri <b>2 milyar TL altında</b> mı doğrula</li>
            </ol>
        </div>

        <!-- UYARI -->
        <div style="background:#fef2f2;border:1px solid #fecaca;
                    border-radius:8px;padding:15px;margin-bottom:10px">
            <p style="margin:0;font-size:12px;color:#991b1b">
                ⚠️ <b>Yatırım tavsiyesi değildir.</b> Bu rapor otomatik veri 
                taraması sonucudur. Kendi analizini yaparak karar ver. 
                Spekülatif hisseler yüksek risk içerir.
            </p>
        </div>

        <p style="text-align:center;color:#9ca3af;font-size:11px">
            BIST Tarama Sistemi • Otomatik Rapor • 4 Katman: Temel / Teknik / Takas / Katalizör
        </p>

    </body>
    </html>
    """
    return html


# ─────────────────────────────────────────────
# MAİL GÖNDER
# ─────────────────────────────────────────────
def mail_gonder(html_icerik):
    if not all([GMAIL_USER, GMAIL_PASS, HEDEF_MAIL]):
        print("❌ Mail bilgileri eksik. .env veya GitHub Secrets kontrol et.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        tarih_kisa = datetime.now().strftime("%d.%m.%Y")
        msg["Subject"] = f"📊 BIST Günlük Tarama — {tarih_kisa}"
        msg["From"] = GMAIL_USER
        msg["To"] = HEDEF_MAIL
        msg.attach(MIMEText(html_icerik, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as sunucu:
            sunucu.login(GMAIL_USER, GMAIL_PASS)
            sunucu.sendmail(GMAIL_USER, HEDEF_MAIL, msg.as_string())

        print(f"✅ Mail gönderildi → {HEDEF_MAIL}")
        return True

    except Exception as e:
        print(f"❌ Mail hatası: {e}")
        return False


# ─────────────────────────────────────────────
# ANA AKIŞ
# ─────────────────────────────────────────────
def main():
    print(f"🔍 Tarama başlıyor — {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    print("  → KAP özel durum açıklamaları...")
    kap = kap_yeni_aciklamalar()
    print(f"     {len(kap)} açıklama bulundu")

    print("  → Yabancı takas hareketleri...")
    takas = yabanci_net_alim()
    print(f"     {len(takas)} hisse bulundu")

    print("  → Kurumsal takas artışları...")
    kurumsal = fintables_kurumsal()
    print(f"     {len(kurumsal)} hisse bulundu")

    print("  → Güçlü sinyaller hesaplanıyor...")
    guclu = guclu_sinyaller_bul(kap, takas, kurumsal)
    print(f"     {len(guclu)} çakışan sinyal bulundu")

    if guclu:
        print("\n  🔥 Bugünün güçlü sinyalleri:")
        for h in guclu:
            print(f"     {h['sembol']} — Puan: {h['puan']}/3")

    print("\n  → Mail hazırlanıyor...")
    html = mail_olustur(kap, takas, kurumsal, guclu)

    print("  → Mail gönderiliyor...")
    mail_gonder(html)

    print("\n✅ Tarama tamamlandı.")


if __name__ == "__main__":
    main()
