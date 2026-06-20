#!/usr/bin/env python3
import json, datetime, traceback
import yfinance as yf
import feedparser

STOCKS = [
    {"name": "Micron",       "tick": "MU",        "ccy": "USD"},
    {"name": "Samsung",      "tick": "005930.KS", "ccy": "KRW"},
    {"name": "SK hynix",     "tick": "000660.KS", "ccy": "KRW"},
    {"name": "Ingenic 君正", "tick": "300223.SZ", "ccy": "CNY"},
]

FEEDS = [
    "https://www.tomshardware.com/feeds/all",
    "https://semiengineering.com/feed/",
    "https://www.eetimes.com/feed/",
    "https://www.theregister.com/Tag/hardware/headlines.atom",
    "https://wccftech.com/feed/",
    "https://www.servethehome.com/feed/",
    "https://riscv.org/feed/",
]

MEM_KW   = ["dram","nand","hbm"," memory","ddr5","ddr4","gddr","flash storage",
            "micron","hynix","sk hynix","samsung memory","yangtze","cxl"]
CMP_KW   = [" gpu"," cpu"," tpu"," npu","amd","intel","nvidia","accelerator",
            "processor"," arm ","xeon","ryzen","epyc","instinct","blackwell",
            "data center","datacenter","ai chip","tensor"]
RISCV_KW = ["risc-v","riscv"]

def get_stocks():
    out = []
    for s in STOCKS:
        item = {"name": s["name"], "tick": s["tick"], "ccy": s["ccy"],
                "price": None, "chg": None}
        try:
            h = yf.Ticker(s["tick"]).history(period="5d")
            if len(h) >= 2:
                last = float(h["Close"].iloc[-1]); prev = float(h["Close"].iloc[-2])
                item["price"] = round(last, 2)
                item["chg"]   = round((last - prev) / prev * 100, 2)
            elif len(h) == 1:
                item["price"] = round(float(h["Close"].iloc[-1]), 2)
        except Exception:
            traceback.print_exc()
        out.append(item)
    return out

def get_news():
    seen, items = set(), []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            src = (f.feed.get("title", "") or "").split("|")[0].strip()[:24]
            for e in f.entries[:40]:
                title = " ".join((e.get("title") or "").split())
                key = title.lower()
                if not title or key in seen:
                    continue
                seen.add(key)
                ts = e.get("published_parsed") or e.get("updated_parsed")
                iso = datetime.datetime(*ts[:6]).isoformat() if ts else ""
                items.append({"title": title, "link": e.get("link", ""),
                              "src": src, "date": iso})
        except Exception:
            traceback.print_exc()
    return items

def bucket(items, kws):
    res = [it for it in items if any(k in (" " + it["title"].lower() + " ") for k in kws)]
    res.sort(key=lambda x: x["date"], reverse=True)
    return res[:12]

def main():
    news = get_news()
    data = {
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "stocks":  get_stocks(),
        "memory":  bucket(news, MEM_KW),
        "compute": bucket(news, CMP_KW),
        "riscv":   bucket(news, RISCV_KW),
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("wrote data.json | mem=%d cmp=%d riscv=%d stocks=%d/4" % (
        len(data["memory"]), len(data["compute"]), len(data["riscv"]),
        sum(1 for s in data["stocks"] if s["price"])))

if __name__ == "__main__":
    main()
