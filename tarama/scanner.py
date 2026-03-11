"""
BIST Multibagger Tarama Sistemi v2
Güvenilir API kaynaklarını kullanır:
- Yahoo Finance API (hisse fiyat/hacim verileri)
- KAP RSS Feed (özel durum açıklamaları)
- IsYatirim JSON API (takas verileri)
"""

import os
import smtplib
import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

HEDEF_MAIL = os.environ.get("HEDEF_MAIL", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

# ─────────────────────────────────────────────
# KAYNAK 1: KAP RSS — Özel Durum Açıklamaları
# ─────────────────────────────────────────────
def kap_rss_tara():
    """KAP RSS feed üzerinden bugünkü önemli açıklamaları çeker."""
    bulunanlar = []
    anahtar_kelimeler = [
        "sözleşme", "ihale", "ihracat", "sipariş", "ortaklık",
        "kapasite", "yatırım", "proje", "anlaşma", "kazandı",
        "contract", "agreement", "export", "investment"
    ]

    rss_urls = [
        "https://www.kap.org.tr/tr/rss/ozel-durum",
        "https://www.kap.org.tr/tr/rss/finansal-rapor",
    ]

    for url in rss_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue

            root = ET.fromstring(r.content)
            bugun = datetime.now().strftime("%Y-%m-%d")

            for item in root.iter("item"):
                baslik = item.findtext("title", "").lower()
                aciklama = item.findtext("description", "").lower()
                tarih = item.findtext("pubDate", "")
                link = item.findtext("link", "")

                metin = baslik + " " + aciklama

                for kelime in anahtar_kelimeler:
                    if kelime in metin:
                        # Sembolü başlıktan çıkar
                        sembol = ""
                        baslik_orijinal = item.findtext("title", "")
                        parcalar = baslik_orijinal.split()
                        if parcalar:
                            sembol = parcalar[0].upper()

                        bulunanlar.append({
                            "sembol": sembol,
                            "baslik": baslik_orijinal[:120],
                            "tarih": tarih[:25] if tarih else "",
                            "link": link,
                            "kaynak": "KAP RSS",
                            "tip": f"'{kelime}' içeriyor"
                        })
                        break

        except Exception as e:
            print(f"KAP RSS hatası ({url}): {e}")

    # Tekrar eden sembolleri temizle
    gorulen = set()
    temiz = []
    for item in bulunanlar:
        if item["sembol"] not in gorulen:
            gorulen.add(item["sembol"])
            temiz.append(item)

    return temiz[:12]


# ─────────────────────────────────────────────
# KAYNAK 2: İş Yatırım — Yabancı Takas Raporu
# ─────────────────────────────────────────────
def isyatirim_takas_tara():
    """İş Yatırım'ın günlük yabancı takas raporunu çeker."""
    bulunanlar = []

    try:
        # İş Yatırım günlük yabancı işlem raporu
        url = "https://www.isyatirim.com.tr/analizler/hisse/yabanci-islemler"
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")

            # Tablo satırlarını ara
            tablolar = soup.find_all("table")
            for tablo in tablolar[:3]:
                satirlar = tablo.find_all("tr")[1:11]
                for satir in satirlar:
                    kolonlar = satir.find_all("td")
                    if len(kolonlar) >= 2:
                        sembol = kolonlar[0].get_text(strip=True)
                        deger = kolonlar[1].get_text(strip=True) if len(kolonlar) > 1 else ""

                        if sembol and len(sembol) <= 8 and sembol.isupper():
                            bulunanlar.append({
                                "sembol": sembol,
                                "deger": deger,
                                "kaynak": "İş Yatırım",
                                "tip": "Yabancı net alım"
                            })

    except Exception as e:
        print(f"İş Yatırım hatası: {e}")

    return bulunanlar[:8]


# ─────────────────────────────────────────────
# KAYNAK 3: Yahoo Finance — Hacim Anomalisi
# ─────────────────────────────────────────────
def yahoo_hacim_anomali():
    """Yahoo Finance üzerinden BIST hisselerinde hacim patlaması tespit eder."""
    bulunanlar = []

    # İzlenecek BIST hisseleri (spekülatif potansiyelli küçük/orta ölçekliler)
    izleme_listesi = [
        "SDTTR.IS", "ALTNY.IS", "KLYPV.IS", "TCKRC.IS", "ALVES.IS",
        "BINHO.IS", "AKFYE.IS", "IZENR.IS", "GWIND.IS", "CWENE.IS",
        "EREGL.IS", "ASELS.IS", "EKGYO.IS", "THYAO.IS", "TCELL.IS",
        "KAPLM.IS", "KTMRK.IS", "PAPIL.IS", "MGROS.IS", "ULKER.IS",
    ]

    for sembol in izleme_listesi:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sembol}?interval=1d&range=30d"
            r = requests.get(url, headers=HEADERS, timeout=10)

            if r.status_code != 200:
                continue

            data = r.json()
            meta = data.get("chart", {}).get("result", [{}])[0]
            indicators = meta.get("indicators", {}).get("quote", [{}])[0]

            hacimler = indicators.get("volume", [])
            kapanis = indicators.get("close", [])

            if len(hacimler) < 10:
                continue

            # Son geçerli değerleri al
            gecerli_hacimler = [h for h in hacimler if h is not None]
            gecerli_kapanis = [k for k in kapanis if k is not None]

            if len(gecerli_hacimler) < 5:
                continue

            son_hacim = gecerli_hacimler[-1]
            ort_hacim = sum(gecerli_hacimler[-20:-1]) / len(gecerli_hacimler[-20:-1])
            son_fiyat = gecerli_kapanis[-1] if gecerli_kapanis else 0
            onceki_fiyat = gecerli_kapanis[-6] if len(gecerli_kapanis) >= 6 else son_fiyat
            fiyat_degisim = ((son_fiyat - onceki_fiyat) / onceki_fiyat * 100) if onceki_fiyat else 0

            hacim_carpani = son_hacim / ort_hacim if ort_hacim > 0 else 0

            # Kriter: Hacim 2x üzeri VE fiyat yatay/hafif pozitif (sessiz toplama)
            if hacim_carpani >= 2.0 and -5 <= fiyat_degisim <= 15:
                bist_sembol = sembol.replace(".IS", "")
                bulunanlar.append({
                    "sembol": bist_sembol,
                    "hacim_carpani": round(hacim_carpani, 1),
                    "fiyat": round(son_fiyat, 2),
                    "fiyat_degisim": round(fiyat_degisim, 1),
                    "kaynak": "Yahoo Finance",
                    "tip": f"Hacim {round(hacim_carpani,1)}x — Fiyat {'+' if fiyat_degisim>=0 else ''}{round(fiyat_degisim,1)}%"
                })

        except Exception as e:
            print(f"Yahoo {sembol} hatası: {e}")
            continue

    bulunanlar.sort(key=lambda x: x["hacim_carpani"], reverse=True)
    return bulunanlar[:8]


# ─────────────────────────────────────────────
# KAYNAK 4: Yahoo Finance — Düşük Değerleme
# ─────────────────────────────────────────────
def yahoo_dusuk_deger():
    """PD/DD < 1 olan BIST hisselerini tespit eder."""
    bulunanlar = []

    izleme_listesi = [
        "EKGYO.IS", "THYAO.IS", "SAHOL.IS", "EREGL.IS", "TCELL.IS",
        "AKBNK.IS", "GARAN.IS", "ISCTR.IS", "KCHOL.IS", "TOASO.IS",
        "FROTO.IS", "PETKM.IS", "TUPRS.IS", "SISE.IS", "KOZAL.IS",
    ]

    for sembol in izleme_listesi:
        try:
            url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sembol}?modules=defaultKeyStatistics,financialData,summaryDetail"
            r = requests.get(url, headers=HEADERS, timeout=10)

            if r.status_code != 200:
                continue

            data = r.json()
            result = data.get("quoteSummary", {}).get("result", [{}])[0]

            key_stats = result.get("defaultKeyStatistics", {})
            summary = result.get("summaryDetail", {})

            pb = key_stats.get("priceToBook", {}).get("raw", None)
            pe = summary.get("trailingPE", {}).get("raw", None)
            fiyat = summary.get("previousClose", {}).get("raw", 0)

            if pb and pb < 1.0:
                bist_sembol = sembol.replace(".IS", "")
                bulunanlar.append({
                    "sembol": bist_sembol,
                    "pd_dd": round(pb, 2),
                    "fk": round(pe, 1) if pe else "—",
                    "fiyat": round(fiyat, 2),
                    "kaynak": "Yahoo Finance",
                    "tip": f"PD/DD: {round(pb,2)} | F/K: {round(pe,1) if pe else '—'}"
                })

        except Exception as e:
            print(f"Yahoo değerleme {sembol} hatası: {e}")
            continue

    bulunanlar.sort(key=lambda x: x["pd_dd"])
    return bulunanlar[:6]


# ─────────────────────────────────────────────
# ÇAKIŞMA — En Güçlü Sinyaller
# ─────────────────────────────────────────────
def guclu_sinyaller_bul(kap, takas, hacim, deger):
    tum = {}
    for kaynak in [kap, takas, hacim, deger]:
        for item in kaynak:
            s = item["sembol"].upper().strip()
            if not s or len(s) > 8:
                continue
            if s not in tum:
                tum[s] = {"sembol": s, "sinyaller": [], "puan": 0}
            tum[s]["sinyaller"].append(f"✅ {item['kaynak']}: {item['tip']}")
            tum[s]["puan"] += 1

    guclu = [v for v in tum.values() if v["puan"] >= 2]
    guclu.sort(key=lambda x: x["puan"], reverse=True)
    return guclu


# ─────────────────────────────────────────────
# MAİL OLUŞTURUCU
# ─────────────────────────────────────────────
def mail_olustur(kap, takas, hacim, deger, guclu):
    tarih = datetime.now().strftime("%d %B %Y")

    def satir_olustur(items, kolonlar):
        html = ""
        for item in items:
            degerler = "".join(f"<td style='padding:8px;font-size:13px;color:#444'>{item.get(k,'')}</td>" for k in kolonlar)
            sembol = item.get("sembol", "")
            html += f"<tr><td style='padding:8px;font-weight:bold;color:#1e40af'>{sembol}</td>{degerler}</tr>"
        return html or "<tr><td colspan='4' style='padding:12px;color:#888;text-align:center'>Veri alınamadı</td></tr>"

    guclu_html = ""
    for h in guclu:
        sinyaller = "<br>".join(h["sinyaller"])
        guclu_html += f"""
        <tr style='background:#f0fdf4'>
            <td style='padding:10px;font-weight:bold;font-size:15px;color:#166534'>🔥 {h['sembol']}</td>
            <td style='padding:10px;font-size:13px'>{sinyaller}</td>
            <td style='padding:10px;text-align:center'>
                <span style='background:#16a34a;color:white;padding:3px 10px;border-radius:10px;font-weight:bold'>{h['puan']}/4</span>
            </td>
        </tr>"""
    if not guclu_html:
        guclu_html = "<tr><td colspan='3' style='padding:15px;color:#666;text-align:center'>Bugün çakışan sinyal bulunamadı — ayrı listeler aşağıda.</td></tr>"

    kap_html = satir_olustur(kap[:8], ["baslik", "tarih"])
    hacim_html = satir_olustur(hacim[:8], ["fiyat", "tip"])
    deger_html = satir_olustur(deger[:6], ["fiyat", "tip"])

    html = f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'></head>
<body style='font-family:Arial,sans-serif;max-width:720px;margin:0 auto;background:#f8fafc;padding:20px'>

<div style='background:linear-gradient(135deg,#1e3a5f,#1d4ed8);color:white;padding:28px;border-radius:14px;margin-bottom:20px'>
    <h1 style='margin:0;font-size:22px'>📊 BIST Günlük Tarama Raporu</h1>
    <p style='margin:8px 0 0;opacity:.8;font-size:14px'>{tarih} • 4 Katman: KAP + Takas + Hacim + Değerleme</p>
</div>

<!-- GÜÇLÜ SİNYALLER -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #16a34a'>
    <h2 style='margin:0 0 6px;color:#166534;font-size:16px'>🔥 GÜÇLÜ SİNYALLER — Birden Fazla Kaynakta Çakışan</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>Hem KAP haberi hem de hacim/takas anomalisi olan hisseler — en güçlü kombinasyon.</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#dcfce7;font-size:12px;color:#166534'>
            <th style='padding:8px;text-align:left'>Sembol</th>
            <th style='padding:8px;text-align:left'>Sinyaller</th>
            <th style='padding:8px;text-align:center'>Güç</th>
        </tr>
        {guclu_html}
    </table>
</div>

<!-- KAP -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #f59e0b'>
    <h2 style='margin:0 0 6px;color:#92400e;font-size:16px'>📋 KAP — Bugünkü Özel Durum Açıklamaları</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>Sözleşme, ihale, sipariş, ihracat, yatırım içeren açıklamalar.</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#fef3c7;font-size:12px;color:#92400e'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left'>Başlık</th>
            <th style='padding:8px;text-align:left;width:20%'>Tarih</th>
        </tr>
        {kap_html}
    </table>
</div>

<!-- HACİM ANOMALİSİ -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #6366f1'>
    <h2 style='margin:0 0 6px;color:#3730a3;font-size:16px'>📈 HACİM ANOMALİSİ — Sessiz Toplama Sinyali</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>Ortalama hacmin 2x+ üzerinde işlem gören, fiyatı yatay seyreden hisseler.</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#e0e7ff;font-size:12px;color:#3730a3'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left;width:20%'>Fiyat (TL)</th>
            <th style='padding:8px;text-align:left'>Sinyal</th>
        </tr>
        {hacim_html}
    </table>
</div>

<!-- DÜŞÜK DEĞERLEME -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #ec4899'>
    <h2 style='margin:0 0 6px;color:#9d174d;font-size:16px'>💎 DÜŞÜK DEĞERLEME — PD/DD &lt; 1</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>Defter değerinin altında işlem gören hisseler — faiz indirimi ile canlanabilir.</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#fce7f3;font-size:12px;color:#9d174d'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left;width:20%'>Fiyat (TL)</th>
            <th style='padding:8px;text-align:left'>Değerleme</th>
        </tr>
        {deger_html}
    </table>
</div>

<!-- KONTROL LİSTESİ -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px'>
    <h2 style='margin:0 0 12px;color:#374151;font-size:16px'>✅ Bugün Yapman Gerekenler</h2>
    <ol style='margin:0;padding-left:20px;line-height:2.2;color:#4b5563;font-size:14px'>
        <li>Güçlü sinyal listesini <b>TradingView</b>'de aç, grafiğe bak</li>
        <li>Hacim anomalisindeki hisselerde <b>Fintables → takas geçmişi</b> kontrol et</li>
        <li>KAP açıklamalarının tam metnini oku (<b>kap.org.tr</b>)</li>
        <li>Piyasa değeri <b>2 milyar TL altında</b> mı doğrula</li>
        <li>Giriş düşündüğün hissede <b>kademeli pozisyon</b> al (%10 kural)</li>
    </ol>
</div>

<div style='background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px;margin-bottom:10px'>
    <p style='margin:0;font-size:12px;color:#991b1b'>⚠️ <b>Yatırım tavsiyesi değildir.</b> Otomatik veri taramasıdır. Spekülatif hisseler yüksek risk içerir.</p>
</div>

<p style='text-align:center;color:#9ca3af;font-size:11px;margin:0'>
    BIST Tarama v2 • Yahoo Finance + KAP RSS • {tarih}
</p>

</body></html>"""
    return html


# ─────────────────────────────────────────────
# MAİL GÖNDER
# ─────────────────────────────────────────────
def mail_gonder(html):
    if not all([GMAIL_USER, GMAIL_PASS, HEDEF_MAIL]):
        print("❌ Mail bilgileri eksik.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        tarih_kisa = datetime.now().strftime("%d.%m.%Y")
        msg["Subject"] = f"📊 BIST Tarama — {tarih_kisa}"
        msg["From"] = GMAIL_USER
        msg["To"] = HEDEF_MAIL
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, HEDEF_MAIL, msg.as_string())
        print(f"✅ Mail gönderildi → {HEDEF_MAIL}")
        return True
    except Exception as e:
        print(f"❌ Mail hatası: {e}")
        return False


# ─────────────────────────────────────────────
# ANA AKIŞ
# ─────────────────────────────────────────────
def main():
    print(f"🔍 BIST Tarama v2 başlıyor — {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    print("  → KAP RSS açıklamaları...")
    kap = kap_rss_tara()
    print(f"     {len(kap)} açıklama")

    print("  → İş Yatırım takas...")
    takas = isyatirim_takas_tara()
    print(f"     {len(takas)} hisse")

    print("  → Yahoo Finance hacim anomalisi...")
    hacim = yahoo_hacim_anomali()
    print(f"     {len(hacim)} hisse")

    print("  → Yahoo Finance değerleme...")
    deger = yahoo_dusuk_deger()
    print(f"     {len(deger)} hisse")

    print("  → Güçlü sinyaller...")
    guclu = guclu_sinyaller_bul(kap, takas, hacim, deger)
    print(f"     {len(guclu)} çakışan sinyal")

    if guclu:
        print("\n  🔥 Bugünün güçlü sinyalleri:")
        for h in guclu:
            print(f"     {h['sembol']} — {h['puan']}/4 puan")

    print("\n  → Mail gönderiliyor...")
    html = mail_olustur(kap, takas, hacim, deger, guclu)
    mail_gonder(html)
    print("✅ Tamamlandı.")


if __name__ == "__main__":
    main()
