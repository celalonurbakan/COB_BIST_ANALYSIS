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
    "SDTTR.IS","ALTNY.IS","KLYPV.IS","ALVES.IS","BINHO.IS",
    "AKFYE.IS","IZENR.IS","GWIND.IS","CWENE.IS","KAPLM.IS",
    "KTMRK.IS","PAPIL.IS","TCKRC.IS","ASELS.IS","THYAO.IS",
    "EREGL.IS","TCELL.IS","EKGYO.IS","MGROS.IS","ULKER.IS",
    "SOKM.IS","AEFES.IS","SAHOL.IS","TOASO.IS","FROTO.IS",
    "PETKM.IS","KOZAL.IS","SISE.IS","AKBNK.IS","GARAN.IS",
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
            fiyat     = meta.get("regularMarketP
