#!/usr/bin/env python3
"""Silicon Radar v3.1 — 来源域名 + 52周高低(三重兜底) + 跨栏去重 + 今日计数"""
import json, datetime, traceback, re
from urllib.parse import urlparse
import yfinance as yf
import feedparser
from deep_translator import GoogleTranslator

STOCKS = [
    {"name": "Micron",       "tick": "MU",        "ccy": "USD"},
    {"name": "Samsung",      "tick": "005930.KS", "ccy": "KRW"},
    {"name": "SK hynix",     "tick": "000660.KS", "ccy": "KRW"},
    {"name": "Ingenic 君正", "tick": "300223.SZ", "ccy": "CNY"},
]
FEEDS = [
    "https://www.tomshardware.com/feeds/all", "https://semiengineering.com/feed/",
    "https://www.eetimes.com/feed/", "https://www.theregister.com/Tag/hardware/headlines.atom",
    "https://wccftech.com/feed/", "https://www.servethehome.com/feed/",
    "https://riscv.org/feed/", "https://blocksandfiles.com/feed/", "https://www.techpowerup.com/rss/news",
    "https://investors.micron.com/rss/news-releases.xml",
    "https://seekingalpha.com/api/v3/symbols/MU/press-releases.xml",
    "https://news.google.com/rss/search?q=Micron+Technology",
]

MICRON_KW = ["micron"]
HBM_KW = ["hbm", "hbm3", "hbm3e", "hbm4", "hbm4e", "high bandwidth memory",
          "high-bandwidth memory", "stacked dram"]
MEM_KW = ["dram", "nand", "ddr5", "hynix", "samsung", "cxl"]
CMP_KW = ["gpu", "cpu", "tpu", "amd", "intel", "nvidia", "accelerator"]
RISCV_KW = ["risc-v", "riscv"]

def _hl_from_fast(t):
    try:
        fi = t.fast_info
        g = fi.get if hasattr(fi, "get") else (lambda k, d=None: getattr(fi, k, d))
        hi, lo = g("year_high"), g("year_low")
        if hi and lo: return float(hi), float(lo)
    except Exception:
        pass
    return None, None

def _hl_from_info(t):
    try:
        info = t.info or {}
        hi = info.get("fiftyTwoWeekHigh"); lo = info.get("fiftyTwoWeekLow")
        if hi and lo: return float(hi), float(lo)
    except Exception:
        pass
    return None, None

def _hl_from_hist(t):
    try:
        h = t.history(period="1y")
        if len(h):
            return float(h["High"].max()), float(h["Low"].min())
    except Exception:
        pass
    return None, None

def get_stocks():
    out = []
    for s in STOCKS:
        item = {"name": s["name"], "tick": s["tick"], "ccy": s["ccy"],
                "price": None, "chg": None, "high52": None, "low52": None, "from_high": None}
        try:
            t = yf.Ticker(s["tick"])
            h = t.history(period="5d")
            if len(h) >= 2:
                last = float(h["Close"].iloc[-1]); prev = float(h["Close"].iloc[-2])
                item["price"] = round(last, 2); item["chg"] = round((last-prev)/prev*100, 2)
            elif len(h) == 1:
                item["price"] = round(float(h["Close"].iloc[-1]), 2)
            hi, lo = _hl_from_fast(t)
            if hi is None: hi, lo = _hl_from_info(t)
            if hi is None: hi, lo = _hl_from_hist(t)
            if hi: item["high52"] = round(hi, 2)
            if lo: item["low52"]  = round(lo, 2)
            if hi and item["price"]:
                item["from_high"] = round((item["price"]-hi)/hi*100, 1)
        except Exception:
            traceback.print_exc()
        out.append(item)
    return out

def domain_of(link):
    try:
        netloc = urlparse(link).netloc.lower()
        if netloc.startswith("www."): netloc = netloc[4:]
        return netloc or ""
    except Exception:
        return ""

def split_pub(title):
    m = re.match(r"^(.*?)\s+[-–—]\s+([^-–—]{2,30})$", title)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title, ""

def get_news():
    seen, items = set(), []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            src = (f.feed.get("title","") or "").split("|")[0].strip()[:24]
            for e in f.entries[:40]:
                raw = " ".join((e.get("title") or "").split())
                key = raw.lower()
                if not raw or key in seen: continue
                seen.add(key)
                title, pub = split_pub(raw)
                summ = e.get("summary","") or e.get("description","") or ""
                summ = " ".join(re.sub("<[^>]+>", " ", summ).split())[:500]
                ts = e.get("published_parsed") or e.get("updated_parsed")
                iso = datetime.datetime(*ts[:6]).isoformat() if ts else ""
                link = e.get("link","")
                source = pub or domain_of(link) or src
                items.append({"title": title, "link": link, "src": source,
                              "date": iso, "summary": summ})
        except Exception:
            pass
    return items

def bucket(items, kws, use_summary=False, exclude=None):
    exclude = exclude or set()
    out = []
    for it in items:
        if it["title"].lower() in exclude:
            continue
        hay = " " + it["title"].lower() + " "
        if use_summary:
            hay += it.get("summary","").lower() + " "
        if any(k in hay for k in kws):
            out.append(it)
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:10]

def count_today(items):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    n = 0
    for it in items:
        try:
            if it["date"] and datetime.datetime.fromisoformat(it["date"]) >= cutoff:
                n += 1
        except Exception:
            pass
    return n

def translate_top(items, n=4):
    try:
        tr = GoogleTranslator(source="auto", target="zh-CN")
    except Exception:
        tr = None
    for it in items[:n]:
        it["zh"] = it["title"]
        if tr:
            try:
                it["zh"] = tr.translate(it["title"])[:140]
            except Exception:
                pass
    return items

def main():
    news = get_news()
    micron = bucket(news, MICRON_KW, use_summary=True)
    seen_micron = {it["title"].lower() for it in micron}
    hbm    = bucket(news, HBM_KW, use_summary=True, exclude=seen_micron)
    mem    = bucket(news, MEM_KW, exclude=seen_micron)
    cmp_   = bucket(news, CMP_KW, exclude=seen_micron)
    rv     = bucket(news, RISCV_KW, exclude=seen_micron)

    today = {
        "micron": count_today(micron), "hbm": count_today(hbm),
        "memory": count_today(mem), "compute": count_today(cmp_), "riscv": count_today(rv),
    }
    for b in (micron, hbm, mem, cmp_, rv):
        translate_top(b, 4)
        for it in b:
            it.pop("summary", None)

    data = {
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "stocks": get_stocks(),
        "today": today,
        "micron": micron, "hbm": hbm, "memory": mem, "compute": cmp_, "riscv": rv,
    }
    with open("data.json","w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("done | micron=%d(今%d) hbm=%d(今%d) mem=%d cmp=%d riscv=%d" %
          (len(micron), today["micron"], len(hbm), today["hbm"],
           len(mem), len(cmp_), len(rv)))

if __name__ == "__main__":
    main()
