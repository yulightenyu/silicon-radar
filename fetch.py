#!/usr/bin/env python3
"""Silicon Radar v3 — Micron section + HBM 标题+摘要匹配"""
import json, datetime, traceback, re
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

def get_stocks():
    out = []
    for s in STOCKS:
        item = {"name": s["name"], "tick": s["tick"], "ccy": s["ccy"], "price": None, "chg": None}
        try:
            h = yf.Ticker(s["tick"]).history(period="5d")
            if len(h) >= 2:
                last = float(h["Close"].iloc[-1]); prev = float(h["Close"].iloc[-2])
                item["price"] = round(last, 2); item["chg"] = round((last-prev)/prev*100, 2)
            elif len(h) == 1:
                item["price"] = round(float(h["Close"].iloc[-1]), 2)
        except Exception:
            pass
        out.append(item)
    return out

def get_news():
    seen, items = set(), []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            src = (f.feed.get("title","") or "").split("|")[0].strip()[:24]
            for e in f.entries[:40]:
                title = " ".join((e.get("title") or "").split())
                key = title.lower()
                if not title or key in seen: continue
                seen.add(key)
                summ = e.get("summary","") or e.get("description","") or ""
                summ = " ".join(re.sub("<[^>]+>", " ", summ).split())[:500]
                ts = e.get("published_parsed") or e.get("updated_parsed")
                iso = datetime.datetime(*ts[:6]).isoformat() if ts else ""
                items.append({"title": title, "link": e.get("link",""),
                              "src": src, "date": iso, "summary": summ})
        except Exception:
            pass
    return items

def bucket(items, kws, use_summary=False):
    out = []
    for it in items:
        hay = " " + it["title"].lower() + " "
        if use_summary:
            hay += it.get("summary","").lower() + " "
        if any(k in hay for k in kws):
            out.append(it)
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:10]

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
    hbm    = bucket(news, HBM_KW,    use_summary=True)
    mem    = bucket(news, MEM_KW)
    cmp_   = bucket(news, CMP_KW)
    rv     = bucket(news, RISCV_KW)
    for b in (micron, hbm, mem, cmp_, rv):
        translate_top(b, 4)
        for it in b:
            it.pop("summary", None)
    data = {
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "stocks": get_stocks(),
        "micron": micron, "hbm": hbm, "memory": mem, "compute": cmp_, "riscv": rv,
    }
    with open("data.json","w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("done | micron=%d hbm=%d mem=%d cmp=%d riscv=%d" %
          (len(micron), len(hbm), len(mem), len(cmp_), len(rv)))

if __name__ == "__main__":
    main()
