"""
BIST Multibagger Tarama Sistemi v3.1
"""
import os, smtplib, requests, json, time, re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

HEDEF_MAIL = os.environ.get("HEDEF_MAIL", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
})

BIST_HISSELER = [
    # BIST 30
    "AKBNK.IS","ARCLK.IS","ASELS.IS","BIMAS.IS","DOHOL.IS",
    "EKGYO.IS","ENJSA.IS","EREGL.IS","FROTO.IS","GARAN.IS",
    "GUBRF.IS","HALKB.IS","ISCTR.IS","KCHOL.IS","KOZAL.IS",
    "KRDMD.IS","PETKM.IS","PGSUS.IS","SAHOL.IS","SASA.IS",
    "SISE.IS","SOKM.IS","TAVHL.IS","TCELL.IS","THYAO.IS",
    "TKFEN.IS","TOASO.IS","TTKOM.IS","TUPRS.IS","VAKBN.IS",
    # BIST 50 ek
    "AEFES.IS","AGESA.IS","AKFEN.IS","AKFYE.IS","ALARK.IS",
    "ANACM.IS","ANHYT.IS","ANSGR.IS","ASUZU.IS","AYDEM.IS",
    "BERA.IS","BRISA.IS","CIMSA.IS","CLEBI.IS","CVKMD.IS",
    "DYOBY.IS","EGEEN.IS","ENKAI.IS","ERBOS.IS","EREGL.IS",
    "FENER.IS","GENIL.IS","GOLTS.IS","GSDHO.IS","GWENV.IS",
    "HEKTS.IS","IPEKE.IS","IZENR.IS","KAPLM.IS","KARSN.IS",
    "KAYSE.IS","KENT.IS","KORDS.IS","KOTON.IS","KTMRK.IS",
    "LOGO.IS","MAVI.IS","MGROS.IS","MPARK.IS","NETAS.IS",
    "ODAS.IS","OTKAR.IS","OYAKC.IS","PAPIL.IS","PARSN.IS",
    "PEKMT.IS","QUAGR.IS","REEDR.IS","RGYAS.IS","RTALB.IS",
    # BIST 100 ek
    "ADEL.IS","ADESE.IS","AGHOL.IS","AGROT.IS","AHGAZ.IS",
    "AKENR.IS","AKGRT.IS","AKPAZ.IS","AKSGY.IS","AKSEN.IS",
    "ALTNY.IS","ALVES.IS","ALYAG.IS","ARSAN.IS","ATAGY.IS",
    "ATAKP.IS","ATATP.IS","AVGYO.IS","AVHOL.IS","AYCES.IS",
    "BAGFS.IS","BAKAB.IS","BANVT.IS","BFREN.IS","BINHO.IS",
    "BIOEN.IS","BIZIM.IS","BJKAS.IS","BMELK.IS","BOSSA.IS",
    "BRYAT.IS","BSOKE.IS","BTCIM.IS","BUCIM.IS","BURCE.IS",
    "CWENE.IS","DAPGM.IS","DERAS.IS","DERIM.IS","DESA.IS",
    "DEVA.IS","DGATE.IS","DGKLB.IS","DGNMO.IS","DITAS.IS",
    "DMRGD.IS","DMSAS.IS","DNISI.IS","DOAS.IS","DOBUR.IS",
    "DOGUB.IS","DURDO.IS","EGPRO.IS","EKIZ.IS","ELITE.IS",
    "EMKEL.IS","EMNIS.IS","ENDAE.IS","EPLAS.IS","ERBOS.IS",
    "ERGRD.IS","ERSU.IS","ESCOM.IS","ESEN.IS","ETILR.IS",
    "ETYAT.IS","EUHOL.IS","EUPWR.IS","EUREN.IS","EUYO.IS",
    "FENER.IS","FLAP.IS","FMIZP.IS","FONET.IS","FORMT.IS",
    "FORTE.IS","FRIGO.IS","FZLGY.IS","GARFA.IS","GEDZA.IS",
    "GENTS.IS","GEREL.IS","GESAN.IS","GLBMD.IS","GLCVY.IS",
    "GLRYH.IS","GLYHO.IS","GMTAS.IS","GOKNR.IS","GOLTS.IS",
    "GRSEL.IS","GSDDE.IS","GSDHO.IS","GSRAY.IS","GTKES.IS",
    "GWIND.IS","HDFGS.IS","HEDEF.IS","HKTM.IS","HLGYO.IS",
    "HTTBT.IS","HUNER.IS","IEYHO.IS","IHEVA.IS","IHGZT.IS",
    "IHLAS.IS","IHLGM.IS","IMASM.IS","INFO.IS","INGRM.IS",
    "INTEM.IS","INVEO.IS","IPMAT.IS","ISATR.IS","ISDMR.IS",
    "ISFIN.IS","ISGSY.IS","ISGYO.IS","ISKPL.IS","ISKUR.IS",
    "ISYAT.IS","ITTFH.IS","IZFAS.IS","JANTS.IS","KAPLM.IS",
    "KARTN.IS","KATMR.IS","KAYSE.IS","KBORU.IS","KCAER.IS",
    "KERVT.IS","KFEIN.IS","KIMMR.IS","KLGYO.IS","KLKIM.IS",
    "KLNMA.IS","KLSER.IS","KLYPV.IS","KNFRT.IS","KOFAZ.IS",
    "KONTR.IS","KOPOL.IS","KRGYO.IS","KRPLS.IS","KRSTL.IS",
    "KRTEK.IS","KTLEV.IS","KUTPO.IS","LIDER.IS","LIDFA.IS",
    "LKMNH.IS","LRSHO.IS","LUKSK.IS","MAALT.IS","MACKO.IS",
    "MAGEN.IS","MAKIM.IS","MAKTK.IS","MANAS.IS","MARBL.IS",
    "MARTI.IS","MAVIS.IS","MEDTR.IS","MEGAP.IS","MEPET.IS",
    "MERCN.IS","MERIT.IS","MERKO.IS","METRO.IS","METUR.IS",
    "MGROS.IS","MHRGY.IS","MIPAZ.IS","MMCAS.IS","MNDRS.IS",
    "MNDTR.IS","MOBTL.IS","MOGAN.IS","MPARK.IS","MRGYO.IS",
    "MRSHL.IS","MSGYO.IS","MTRKS.IS","MZHLD.IS","NATEN.IS",
    "NETAS.IS","NIBAS.IS","NTGAZ.IS","NTHOL.IS","NUGYO.IS",
    "NUHCM.IS","OBASE.IS","ODAS.IS","ONCSM.IS","ORCAY.IS",
    "ORGE.IS","ORMA.IS","OSTIM.IS","OTKAR.IS","OYLUM.IS",
    "OZGYO.IS","OZKGY.IS","OZRDN.IS","OZSUB.IS","PAGYO.IS",
    "PAMEL.IS","PNLSN.IS","POLHO.IS","POLTK.IS","PRDGS.IS",
    "PRZMA.IS","PSDTC.IS","PSGYO.IS","QUAGR.IS","RALYH.IS",
    "RAYSG.IS","REEDR.IS","RODRG.IS","ROYAL.IS","RTALB.IS",
    "RUBNS.IS","RYGYO.IS","SAMAT.IS","SARAS.IS","SARKY.IS",
    "SDTTR.IS","SEGYO.IS","SEKFK.IS","SEKUR.IS","SELEC.IS",
    "SELMR.IS","SEYKM.IS","SILVR.IS","SNGYO.IS","SNKRN.IS",
    "SONME.IS","SRVGY.IS","SUMAS.IS","SUNTK.IS","SURGY.IS",
    "SUWEN.IS","TARKM.IS","TBORG.IS","TCKRC.IS","TDGYO.IS",
    "TEKTU.IS","텔STA.IS","TETMT.IS","TEZOL.IS","TGSAS.IS",
    "TKFEN.IS","TKNSA.IS","TLMAN.IS","TMPOL.IS","TNZTP.IS",
    "TOASO.IS","TRCAS.IS","TRGYO.IS","TRILC.IS","TSGYO.IS",
    "TSPOR.IS","TTRAK.IS","TUCLK.IS","TUGVA.IS","TÜMÖS.IS",
    "TUREX.IS","TURGG.IS","TURSG.IS","ULUUN.IS","ULKER.IS",
    "UMPAS.IS","UNLU.IS","USAK.IS","UZERB.IS","VAKFN.IS",
    "VKFYO.IS","VKGYO.IS","WATRO.IS","WGETR.IS","YATAS.IS",
    "YAYLA.IS","YGGYO.IS","YGYO.IS","YKSLN.IS","YUNSA.IS",
    "ZOREN.IS","ZRGYO.IS",
]
def yahoo_tarama():
    hacim_anomali, dusuk_deger = [], []
    basarili = 0
    print(f"  → {len(BIST_HISSELER)} hisse taranıyor...")
    for i, sembol in enumerate(BIST_HISSELER):
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{sembol}?interval=1d&range=30d"
            r = SESSION.get(url, timeout=12)
            if r.status_code != 200:
                continue
            data = r.json()
            result = data.get("chart", {}).get("result", [])
            if not result:
                continue
            meta = result[0].get("meta", {})
            inds = result[0].get("indicators", {}).get("quote", [{}])[0]
            hacimler = [h for h in inds.get("volume", []) if h]
            kapanis  = [k for k in inds.get("close",  []) if k]
            if len(hacimler) < 5:
                continue
            basarili += 1
            fiyat     = meta.get("regularMarketPrice", 0) or 0
            son_hacim = hacimler[-1]
            ort_hacim = sum(hacimler[-20:-1]) / max(len(hacimler[-20:-1]), 1)
            carpan    = son_hacim / ort_hacim if ort_hacim else 0
            degisim   = 0
            if len(kapanis) >= 6 and kapanis[-6]:
                degisim = (kapanis[-1] - kapanis[-6]) / kapanis[-6] * 100
            bist = sembol.replace(".IS","")
            if carpan >= 1.5 and -8 <= degisim <= 20:
                hacim_anomali.append({
                    "sembol": bist, "fiyat": round(fiyat,2),
                    "tip": f"Hacim {round(carpan,1)}x | Fiyat {'+' if degisim>=0 else ''}{round(degisim,1)}%",
                    "carpan": round(carpan,1), "kaynak": "Yahoo Finance",
                })
            pb = meta.get("priceToBook")
            pe = meta.get("trailingPE")
            if pb and 0 < pb < 2.0:
                dusuk_deger.append({
                    "sembol": bist, "fiyat": round(fiyat,2),
                    "tip": f"PD/DD: {round(pb,2)} | F/K: {round(pe,1) if pe else '—'}",
                    "pd_dd": round(pb,2), "kaynak": "Yahoo Finance",
                })
        except Exception as e:
            print(f"    {sembol} hata: {e}")
        if i % 5 == 4:
            time.sleep(0.3)
    print(f"     {basarili} hisse çekildi | Hacim: {len(hacim_anomali)} | Değerleme: {len(dusuk_deger)}")
    hacim_anomali.sort(key=lambda x: x["carpan"], reverse=True)
    dusuk_deger.sort(key=lambda x: x["pd_dd"])
    return hacim_anomali[:8], dusuk_deger[:6]

def kap_tara():
    bulunanlar = []
    anahtar = ["sözleşme","ihale","ihracat","sipariş","ortaklık","yatırım","proje","anlaşma","kazandı"]
    urls = [
        "https://bigpara.hurriyet.com.tr/haberler/kap-haberleri/",
        "https://www.bloomberght.com/haberler",
    ]
    for url in urls:
        try:
            r = SESSION.get(url, timeout=15)
            print(f"     Haber {url}: {r.status_code}")
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup.find_all(["h2","h3","a","li"], limit=80):
                metin = tag.get_text(strip=True)
                if len(metin) < 10:
                    continue
                for kelime in anahtar:
                    if kelime in metin.lower():
                        semboller = re.findall(r'\b[A-Z]{3,6}\b', metin)
                        sembol = semboller[0] if semboller else "HABER"
                        bulunanlar.append({
                            "sembol": sembol,
                            "baslik": metin[:100],
                            "tarih": datetime.now().strftime("%d.%m.%Y"),
                            "kaynak": "Haberler", "tip": f"'{kelime}'",
                        })
                        break
            if bulunanlar:
                break
        except Exception as e:
            print(f"     Haber hata: {e}")
    gorulen, temiz = set(), []
    for item in bulunanlar:
        if item["sembol"] not in gorulen and item["sembol"] != "HABER":
            gorulen.add(item["sembol"])
            temiz.append(item)
    print(f"     {len(temiz)} haber bulundu")
    return temiz[:10]

def guclu_sinyaller(kap, hacim, deger):
    tum = {}
    for lst in [kap, hacim, deger]:
        for item in lst:
            s = item["sembol"].upper().strip()
            if not s or len(s) > 7:
                continue
            if s not in tum:
                tum[s] = {"sembol": s, "sinyaller": [], "puan": 0}
            tum[s]["sinyaller"].append(f"✅ {item['kaynak']}: {item['tip']}")
            tum[s]["puan"] += 1
    sonuc = sorted(tum.values(), key=lambda x: x["puan"], reverse=True)
    return sonuc[:12]

def mail_olustur(kap, hacim, deger, guclu):
    tarih = datetime.now().strftime("%d %B %Y")

    def satirlar(items, alanlar):
        if not items:
            return "<tr><td colspan='3' style='padding:12px;color:#888;text-align:center'>Bugün veri bulunamadı</td></tr>"
        html = ""
        for item in items:
            degerler = "".join(f"<td style='padding:8px;font-size:13px;color:#444'>{item.get(a,'')}</td>" for a in alanlar)
            html += f"<tr><td style='padding:8px;font-weight:bold;color:#1e40af'>{item['sembol']}</td>{degerler}</tr>"
        return html

    guclu_html = ""
    for h in guclu:
        puan_renk = "#16a34a" if h["puan"] >= 2 else "#ca8a04"
        sinyaller = "<br>".join(h["sinyaller"])
        guclu_html += f"""
        <tr style='background:#f0fdf4'>
            <td style='padding:10px;font-weight:bold;font-size:15px;color:#166534'>
                {"🔥" if h["puan"]>=2 else "📌"} {h['sembol']}
            </td>
            <td style='padding:10px;font-size:13px'>{sinyaller}</td>
            <td style='padding:10px;text-align:center'>
                <span style='background:{puan_renk};color:white;padding:3px 10px;
                border-radius:10px;font-weight:bold'>{h["puan"]}/3</span>
            </td>
        </tr>"""
    if not guclu_html:
        guclu_html = "<tr><td colspan='3' style='padding:15px;color:#666;text-align:center'>Bugün sinyal bulunamadı</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'></head>
<body style='font-family:Arial,sans-serif;max-width:720px;margin:0 auto;background:#f8fafc;padding:20px'>
<div style='background:linear-gradient(135deg,#1e3a5f,#1d4ed8);color:white;padding:28px;border-radius:14px;margin-bottom:20px'>
    <h1 style='margin:0;font-size:22px'>📊 BIST Günlük Tarama</h1>
    <p style='margin:8px 0 0;opacity:.8;font-size:14px'>{tarih} • Yahoo Finance + KAP Haberleri</p>
</div>
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #16a34a'>
    <h2 style='margin:0 0 6px;color:#166534;font-size:16px'>🔥 TÜM SİNYALLER</h2>
    <p style='margin:0 0 14px;font-size:12px;color:#666'>🔥 = Birden fazla kaynakta çakışan &nbsp;|&nbsp; 📌 = Tek kaynaktan gelen</p>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#dcfce7;font-size:12px;color:#166534'>
            <th style='padding:8px;text-align:left'>Sembol</th>
            <th style='padding:8px;text-align:left'>Sinyaller</th>
            <th style='padding:8px;text-align:center'>Güç</th>
        </tr>{guclu_html}
    </table>
</div>
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #6366f1'>
    <h2 style='margin:0 0 6px;color:#3730a3;font-size:16px'>📈 HACİM ANOMALİSİ — Sessiz Toplama</h2>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#e0e7ff;font-size:12px;color:#3730a3'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left;width:20%'>Fiyat (TL)</th>
            <th style='padding:8px;text-align:left'>Sinyal</th>
        </tr>{satirlar(hacim, ["fiyat","tip"])}
    </table>
</div>
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #ec4899'>
    <h2 style='margin:0 0 6px;color:#9d174d;font-size:16px'>💎 DÜŞÜK DEĞERLEME — PD/DD &lt; 2</h2>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#fce7f3;font-size:12px;color:#9d174d'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left;width:20%'>Fiyat (TL)</th>
            <th style='padding:8px;text-align:left'>Değerleme</th>
        </tr>{satirlar(deger, ["fiyat","tip"])}
    </table>
</div>
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px;border-left:4px solid #f59e0b'>
    <h2 style='margin:0 0 6px;color:#92400e;font-size:16px'>📋 KAP HABERLERİ</h2>
    <table style='width:100%;border-collapse:collapse'>
        <tr style='background:#fef3c7;font-size:12px;color:#92400e'>
            <th style='padding:8px;text-align:left;width:15%'>Sembol</th>
            <th style='padding:8px;text-align:left'>Başlık</th>
            <th style='padding:8px;text-align:left;width:18%'>Tarih</th>
        </tr>{satirlar(kap, ["baslik","tarih"])}
    </table>
</div>
<div style='background:white;border-radius:12px;padding:20px;margin-bottom:18px'>
    <h2 style='margin:0 0 12px;color:#374151;font-size:16px'>✅ Bugün Yapman Gerekenler</h2>
    <ol style='margin:0;padding-left:20px;line-height:2.2;color:#4b5563;font-size:14px'>
        <li>Sinyal listesindeki hisseleri <b>TradingView</b>'de aç</li>
        <li>Hacim anomalisinde <b>Fintables → takas geçmişi</b> kontrol et</li>
        <li>Giriş düşündüğünde <b>kademeli pozisyon</b> al (%10 kural)</li>
    </ol>
</div>
<div style='background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px'>
    <p style='margin:0;font-size:12px;color:#991b1b'>⚠️ <b>Yatırım tavsiyesi değildir.</b> Otomatik veri taramasıdır.</p>
</div>
</body></html>"""

def mail_gonder(html):
    if not all([GMAIL_USER, GMAIL_PASS, HEDEF_MAIL]):
        print("❌ Mail bilgileri eksik.")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📊 BIST Tarama — {datetime.now().strftime('%d.%m.%Y')}"
        msg["From"] = GMAIL_USER
        msg["To"]   = HEDEF_MAIL
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, HEDEF_MAIL, msg.as_string())
        print(f"✅ Mail gönderildi → {HEDEF_MAIL}")
    except Exception as e:
        print(f"❌ Mail hatası: {e}")

def main():
    print(f"🔍 BIST Tarama v3.1 — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("  → Yahoo Finance tarama...")
    hacim, deger = yahoo_tarama()
    print("  → KAP/Haber tarama...")
    kap = kap_tara()
    print("  → Sinyaller hesaplanıyor...")
    guclu = guclu_sinyaller(kap, hacim, deger)
    print(f"     {len(guclu)} sinyal")
    if hacim:
        print("\n  📈 Hacim anomalisi:")
        for h in hacim:
            print(f"     {h['sembol']} — {h['tip']}")
    if deger:
        print("\n  💎 Düşük değerleme:")
        for d in deger:
            print(f"     {d['sembol']} — {d['tip']}")
    html = mail_olustur(kap, hacim, deger, guclu)
    mail_gonder(html)
    print("\n✅ Tamamlandı.")

if __name__ == "__main__":
    main()
