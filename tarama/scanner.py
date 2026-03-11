"""
BIST Multibagger Tarama Sistemi v3
- Yahoo Finance v7 API (BIST hisseleri için çalışan endpoint)
- KAP RSS (doğru URL ile)
- Detaylı hata loglama
"""

import os, smtplib, requests, json, time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

HEDEF_MAIL = os.environ.get("HEDEF_MAIL", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*;q=0.9",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})

# ─────────────────────────────────────────────
# KAYNAK 1: Yahoo Finance v7 — Hisse Verileri
# ─────────────────────────────────────────────

BIST_HISSELER = [
    # Küçük/orta ölçekli spekülatif potansiyelli
    "SDTTR.IS", "ALTNY.IS", "KLYPV.IS", "ALVES.IS", "BINHO.IS",
    "AKFYE.IS", "IZENR.IS", "GWIND.IS", "CWENE.IS", "KAPLM.IS",
    "KTMRK.IS", "PAPIL.IS", "TCKRC.IS",
    # Orta büyüklük
    "ASELS.IS", "THYAO.IS", "EREGL.IS", "TCELL.IS", "EKGYO.IS",
    "MGROS.IS", "ULKER.IS", "SOKM.IS", "AEFES.IS", "SAHOL.IS",
    "TOASO.IS", "FROTO.IS", "PETKM.IS", "KOZAL.IS", "SISE.IS",
]

def yahoo_hisse_verisi(sembol):
    """Tek bir hisse için Yahoo Finance v7 API'den veri çeker."""
    try:
        # Önce v7 dene
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={sembol}"
        r = SESSION.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            sonuc = data.get("quoteResponse", {}).get("result", [])
            if sonuc:
                return sonuc[0]

        # v7 olmadıysa v8 chart dene
        url2 = f"https://query2.finance.yahoo.com/v8/finance/chart/{sembol}?interval=1d&range=30d"
        r2 = SESSION.get(url2, timeout=12)
        if r2.status_code == 200:
            data2 = r2.json()
            meta = data2.get("chart", {}).get("result", [{}])[0].get("meta", {})
            inds = data2.get("chart", {}).get("result", [{}])[0].get("indicators", {}).get("quote", [{}])[0]
            hacimler = [h for h in inds.get("volume", []) if h]
            kapanis = [k for k in inds.get("close", []) if k]
            if meta and hacimler:
                return {
                    "symbol": sembol,
                    "regularMarketPrice": meta.get("regularMarketPrice", 0),
                    "regularMarketVolume": hacimler[-1] if hacimler else 0,
                    "averageDailyVolume3Month": sum(hacimler[-20:]) / len(hacimler[-20:]) if len(hacimler) >= 5 else 0,
                    "priceToBook": meta.get("priceToBook"),
                    "trailingPE": meta.get("trailingPE"),
                    "_kapanis_listesi": kapanis,
                    "_hacim_listesi": hacimler,
                }
    except Exception as e:
        print(f"    Yahoo {sembol} hata: {e}")
    return None


def yahoo_tarama():
    """Tüm hisseleri tarar, hacim anomalisi ve düşük değerleme tespit eder."""
    hacim_anomali = []
    dusuk_deger = []
    basarili = 0

    print(f"  → {len(BIST_HISSELER)} hisse taranıyor...")

    for i, sembol in enumerate(BIST_HISSELER):
        veri = yahoo_hisse_verisi(sembol)
        if not veri:
            continue
        basarili += 1

        bist = sembol.replace(".IS", "")
        fiyat = veri.get("regularMarketPrice", 0) or 0
        hacim = veri.get("regularMarketVolume", 0) or 0
        ort_hacim = veri.get("averageDailyVolume3Month", 0) or 0
        pb = veri.get("priceToBook")
        pe = veri.get("trailingPE")

        # Hacim anomalisi: günlük hacim ortalamanın 2x+ üzerinde
        if ort_hacim and ort_hacim > 0:
            carpan = hacim / ort_hacim
            if carpan >= 1.8:
                # Fiyat değişimi hesapla
                kapanis = veri.get("_kapanis_listesi", [])
                degisim = 0
                if len(kapanis) >= 6:
                    degisim = (kapanis[-1] - kapanis[-6]) / kapanis[-6] * 100 if kapanis[-6] else 0

                if -8 <= degisim <= 20:  # Fiyat sakin = sessiz toplama
                    hacim_anomali.append({
                        "sembol": bist,
                        "fiyat": round(fiyat, 2),
                        "tip": f"Hacim {round(carpan,1)}x | Fiyat {'+' if degisim>=0 else ''}{round(degisim,1)}%",
                        "carpan": round(carpan, 1),
                        "kaynak": "Yahoo Finance",
                    })

        # Düşük değerleme: PD/DD < 1
        if pb and 0 < pb < 1.2:
            dusuk_deger.append({
                "sembol": bist,
                "fiyat": round(fiyat, 2),
                "tip": f"PD/DD: {round(pb,2)} | F/K: {round(pe,1) if pe else '—'}",
                "pd_dd": round(pb, 2),
                "kaynak": "Yahoo Finance",
            })

        # Rate limit için küçük bekleme
        if i % 5 == 4:
            time.sleep(0.5)

    print(f"     {basarili} hisse başarıyla çekildi")
    hacim_anomali.sort(key=lambda x: x["carpan"], reverse=True)
    dusuk_deger.sort(key=lambda x: x["pd_dd"])
    return hacim_anomali[:8], dusuk_deger[:6]


# ─────────────────────────────────────────────
# KAYNAK 2: KAP RSS
# ─────────────────────────────────────────────

KAP_RSS_URLS = [
    "https://www.kap.org.tr/rss/ozel-durum",
    "https://www.kap.org.tr/tr/rss/ozel-durum",
    "https://www.kap.org.tr/rss/bildirim",
]

ANAHTAR = [
    "sözleşme", "ihale", "ihracat", "sipariş", "ortaklık",
    "kapasite", "yatırım", "proje", "anlaşma", "kazandı",
    "contract", "agreement", "award", "investment",
]

def kap_rss_tara():
    bulunanlar = []
    for url in KAP_RSS_URLS:
        try:
            r = SESSION.get(url, timeout=15)
            print(f"     KAP {url}: {r.status_code} ({len(r.text)} byte)")
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                baslik_orijinal = item.findtext("title", "")
                baslik = baslik_orijinal.lower()
                aciklama = item.findtext("description", "").lower()
                metin = baslik + " " + aciklama
                for kelime in ANAHTAR:
                    if kelime in metin:
                        parcalar = baslik_orijinal.split()
                        sembol = parcalar[0].upper() if parcalar else "—"
                        bulunanlar.append({
                            "sembol": sembol,
                            "baslik": baslik_orijinal[:100],
                            "tarih": item.findtext("pubDate", "")[:16],
                            "kaynak": "KAP RSS",
                            "tip": f"'{kelime}'",
                        })
                        break
            if bulunanlar:
                break  # Çalışan URL bulundu
        except Exception as e:
            print(f"     KAP RSS {url} hata: {e}")

    # Tekrarları temizle
    gorulen, temiz = set(), []
    for item in bulunanlar:
        if item["sembol"] not in gorulen:
            gorulen.add(item["sembol"])
            temiz.append(item)
    return temiz[:10]


# ─────────────────────────────────────────────
# ÇAKIŞMA
# ─────────────────────────────────────────────

def guclu_sinyaller(kap, hacim, deger):
    tum = {}
    for kaynak_list in [kap, hacim, deger]:
        for item in kaynak_list:
            s = item["sembol"].upper().strip()
            if not s or len(s) > 8:
                continue
            if s not in tum:
                tum[s] = {"sembol": s, "sinyaller": [], "puan": 0}
            tum[s]["sinyaller"].append(f"✅ {item['kaynak']}: {item['tip']}")
            tum[s]["puan"] += 1
    sonuc = [v for v in tum.values() if v["puan"] >= 2]
    sonuc.sort(key=lambda x: x["puan"], reverse=True)
    return sonuc


# ─────────────────────────────────────────────
# MAİL
# ─────────────────────────────────────────────

def mail_olustur(kap, hacim, deger, guclu):
    tarih = datetime.now().strftime("%d %B %Y")

    def tablo_satirlari(items, alanlar):
        if not items:
            return "<tr><td colspan='3' style='padding:12px;color:#888;text-align:center'>Bugün veri bulunamadı</td></tr>"
        html = ""
        for item in items:
            degerler = "".join(
                f"<td style='padding:8px;font-size:13px;color:#444'>{item.get(a, '')}</td>"
                for a in alanlar
            )
            html += f"<tr><td style='padding:8px;font-weight:bold;color:#1e40af'>{item['sembol']}</td>{degerler}</tr>"
        return html

    guclu_html = ""
    for h in guclu:
        sinyaller = "<br>".join(h["sinyaller"])
        guclu_html += f"""
        <tr style='background:#f0fdf4'>
            <td style='padding:10px;font-weight:bold;font-size:15px;color:#166534'>🔥 {h['sembol']}</td>
            <td style='padding:10px;font-size:13px'>{sinyaller}</td>
            <td style='padding:10px;text-align:center'>
                <span style='background:#16a34a;color:white;padding:3px 10px;
                border-radius:10px;font-weight:bold'>{h['puan']}/3</span>
            </td>
        </tr>"""
    if not guclu_html:
        guclu_html = "<tr><td colspan='3' style='padding:15px;color:#666;text-align:center'>Bugün çakışan sinyal yok — ayrı listeler aşağıda.</td></tr>"

    kap_html    = tablo_satirlari(kap[:8],   ["baslik", "tarih"])
    hacim_html  = tablo_satirlari(hacim[:8], ["fiyat",  "tip"])
    deger_html  = tablo_satirlari(deger[:6], ["fiyat",  "tip"])

    return f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'></head>
<body style='font-family:Arial,sans-serif;max-width:720px;margin:0 auto;background:#f8fafc;padding:20px'>

<div style='background:linear-gradient(135deg,#1e3a5f,#1d4ed8);color:white;
            padding:28px;border-radius:14px;margin-bottom:20px'>
    <h1 style='margin:0;font-size:22px'>📊 BIST Günlük Tarama — v3</h1>
    <p style='margin:8px 0 0;opacity:.8;font-size:14px'>{tarih} &nbsp;•&nbsp; KAP + Yahoo Finance</p>
</div>

<!-- GÜÇLÜ SİNYALLER -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #16a34a'>
    <h2 style='margin:0 0 6px;color:#166534;font-size:16px'>🔥 GÜÇLÜ SİNYALLER</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>Birden fazla kaynakta çakışan hisseler.</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#dcfce7;font-size:12px;color:#166534'>
            <th style='padding:8px;text-align:left'>Sembol</th>
            <th style='padding:8px;text-align:left'>Sinyaller</th>
            <th style='padding:8px;text-align:center'>Güç</th>
        </tr>{guclu_html}
    </table>
</div>

<!-- KAP -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #f59e0b'>
    <h2 style='margin:0 0 6px;color:#92400e;font-size:16px'>📋 KAP — Özel Durum Açıklamaları</h2>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#fef3c7;font-size:12px;color:#92400e'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left'>Başlık</th>
            <th style='padding:8px;text-align:left;width:18%'>Tarih</th>
        </tr>{kap_html}
    </table>
</div>

<!-- HACİM -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #6366f1'>
    <h2 style='margin:0 0 6px;color:#3730a3;font-size:16px'>📈 HACİM ANOMALİSİ — Sessiz Toplama</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>Ortalama hacmin 2x+ üzerinde, fiyatı sakin hisseler.</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#e0e7ff;font-size:12px;color:#3730a3'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left;width:20%'>Fiyat (TL)</th>
            <th style='padding:8px;text-align:left'>Sinyal</th>
        </tr>{hacim_html}
    </table>
</div>

<!-- DEĞERLEME -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #ec4899'>
    <h2 style='margin:0 0 6px;color:#9d174d;font-size:16px'>💎 DÜŞÜK DEĞERLEME — PD/DD &lt; 1.2</h2>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#fce7f3;font-size:12px;color:#9d174d'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left;width:20%'>Fiyat (TL)</th>
            <th style='padding:8px;text-align:left'>Değerleme</th>
        </tr>{deger_html}
    </table>
</div>

<!-- KONTROL -->
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px'>
    <h2 style='margin:0 0 12px;color:#374151;font-size:16px'>✅ Bugün Yapman Gerekenler</h2>
    <ol style='margin:0;padding-left:20px;line-height:2.2;color:#4b5563;font-size:14px'>
        <li>Güçlü sinyal listesini <b>TradingView</b>'de aç</li>
        <li>Hacim anomalisinde <b>Fintables → takas geçmişi</b> kontrol et</li>
        <li>KAP açıklamalarının tam metnini oku (<b>kap.org.tr</b>)</li>
        <li>Piyasa değeri <b>2 milyar TL altında</b> mı doğrula</li>
        <li>Giriş düşündüğünde <b>kademeli pozisyon</b> al (%10 kural)</li>
    </ol>
</div>

<div style='background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px;margin-bottom:10px'>
    <p style='margin:0;font-size:12px;color:#991b1b'>
    ⚠️ <b>Yatırım tavsiyesi değildir.</b> Otomatik veri taramasıdır. Spekülatif hisseler yüksek risk içerir.
    </p>
</div>
<p style='text-align:center;color:#9ca3af;font-size:11px'>BIST Tarama v3 • {tarih}</p>
</body></html>"""


def mail_gonder(html):
    if not all([GMAIL_USER, GMAIL_PASS, HEDEF_MAIL]):
        print("❌ Mail bilgileri eksik.")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📊 BIST Tarama — {datetime.now().strftime('%d.%m.%Y')}"
        msg["From"]    = GMAIL_USER
        msg["To"]      = HEDEF_MAIL
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, HEDEF_MAIL, msg.as_string())
        print(f"✅ Mail gönderildi → {HEDEF_MAIL}")
    except Exception as e:
        print(f"❌ Mail hatası: {e}")


# ─────────────────────────────────────────────
# ANA AKIŞ
# ─────────────────────────────────────────────

def main():
    print(f"🔍 BIST Tarama v3 — {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    print("  → KAP RSS...")
    kap = kap_rss_tara()
    print(f"     {len(kap)} açıklama bulundu")

    print("  → Yahoo Finance tarama...")
    hacim, deger = yahoo_tarama()
    print(f"     Hacim anomalisi: {len(hacim)} | Düşük değerleme: {len(deger)}")

    print("  → Güçlü sinyaller...")
    guclu = guclu_sinyaller(kap, hacim, deger)
    print(f"     {len(guclu)} çakışan sinyal")

    if hacim:
        print("\n  📈 Hacim anomalisi bulunanlar:")
        for h in hacim:
            print(f"     {h['sembol']} — {h['tip']}")

    if deger:
        print("\n  💎 Düşük değerleme bulunanlar:")
        for d in deger:
            print(f"     {d['sembol']} — {d['tip']}")

    html = mail_olustur(kap, hacim, deger, guclu)
    mail_gonder(html)
    print("\n✅ Tamamlandı.")


if __name__ == "__main__":
    main()
