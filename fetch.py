#!/usr/bin/env python3
import json, datetime, feedparser
from deep_translator import GoogleTranslator

FEEDS = [
    "https://www.tomshardware.com/feeds/all", "https://semiengineering.com/feed/",
    "https://www.eetimes.com/feed/", "https://www.theregister.com/Tag/hardware/headlines.atom",
    "https://wccftech.com/feed/", "https://www.servethehome.com/feed/",
    "https://riscv.org/feed/", "https://blocksandfiles.com/feed/", "https://www.techpowerup.com/rss/news",
    "https://investors.micron.com/rss/news-releases.xml",
    "https://seekingalpha.com/api/v3/symbols/MU/press-releases.xml",
    "https://news.google.com/rss/search?q=Micron+Technology"
]

MICRON_KW = ["micron", "mu", "memory", "storage"]
HBM_KW = ["hbm", "hbm3", "hbm4", "high bandwidth memory"]
MEM_KW = ["dram", "nand", "ddr5", "hynix", "samsung", "cxl"]
CMP_KW = ["gpu", "cpu", "tpu", "amd", "intel", "nvidia", "accelerator"]
RISCV_KW = ["risc-v", "riscv"]

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
                ts = e.get("published_parsed") or e.get("updated_parsed")
                iso = datetime.datetime(*ts[:6]).isoformat() if ts else ""
                items.append({"title": title, "link": e.get("link",""), "src": src, "date": iso})
        except Exception: pass
    return items

def bucket(items, kws):
    res = [it for it in items if any(k in it["title"].lower() for k in kws)]
    res.sort(key=lambda x: x["date"], reverse=True)
    return res[:10]

def translate_top(items, n=4):
    try: tr = GoogleTranslator(source="auto", target="zh-CN")
    except: tr = None
    for it in items[:n]:
        it["zh"] = it["title"]
        if tr:
            try: it["zh"] = tr.translate(it["title"])[:140]
            except: pass
    return items

def main():
    news = get_news()
    data = {
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "stocks": [],
        "micron": translate_top(bucket(news, MICRON_KW), 4),
        "hbm": translate_top(bucket(news, HBM_KW), 4),
        "memory": translate_top(bucket(news, MEM_KW), 4),
        "compute": translate_top(bucket(news, CMP_KW), 4),
        "riscv": translate_top(bucket(news, RISCV_KW), 4),
    }
    with open("data.json","w",encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    print("Done.")

if __name__ == "__main__": main()
