import os, re, json, math, shutil, sqlite3, time
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

CHROME_EPOCH_OFFSET = 11644473600  # seconds between 1601-01-01 and 1970-01-01

def chrome_time_to_unix_seconds(chrome_microseconds: int) -> float:
    # chrome time: microseconds since 1601-01-01
    return chrome_microseconds / 1_000_000 - CHROME_EPOCH_OFFSET

TRACK_PARAMS_PREFIXES = ("utm_",)
TRACK_PARAMS_EXACT = {"gclid", "fbclid", "msclkid"}

def clean_url(u: str) -> str:
    try:
        p = urlparse(u)
        # remove fragment
        fragment = ""
        # remove tracking query params
        q = []
        for k, v in parse_qsl(p.query, keep_blank_values=True):
            lk = k.lower()
            if lk in TRACK_PARAMS_EXACT or any(lk.startswith(pref) for pref in TRACK_PARAMS_PREFIXES):
                continue
            q.append((k, v))
        query = urlencode(q, doseq=True)
        # optionally: drop full query for simplicity (uncomment)
        # query = ""
        return urlunparse((p.scheme, p.netloc, p.path, p.params, query, fragment))
    except Exception:
        return u

def score_item(visit_count: int, last_visit_unix: float) -> float:
    # frequency term
    freq = math.log(visit_count + 1)
    # recency term (half-life ~14 days)
    age_days = max(0.0, (time.time() - last_visit_unix) / 86400.0)
    rec = math.exp(-age_days / 14.0)
    return freq + 2.0 * rec

def build_cache(history_path: str, out_path: str, limit: int = 800):
    tmp_copy = out_path + ".history_copy"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # copy History to avoid lock issues
    shutil.copy2(history_path, tmp_copy)

    con = sqlite3.connect(tmp_copy)
    cur = con.cursor()

    cur.execute("""
        SELECT url, title, visit_count, typed_count, last_visit_time
        FROM urls
        WHERE url LIKE 'http%'
          AND hidden = 0
          AND visit_count > 0
    """)
    rows = cur.fetchall()
    con.close()
    os.remove(tmp_copy)

    items = {}
    for url, title, visit_count, typed_count, last_visit_time in rows:
        url2 = clean_url(url)
        last_unix = chrome_time_to_unix_seconds(last_visit_time or 0)
        s = score_item(int(visit_count or 0), last_unix)

        key = url2  # dedupe by cleaned url
        if key not in items or s > items[key]["score"]:
            items[key] = {
                "url": url2,
                "title": (title or urlparse(url2).netloc),
                "visit_count": int(visit_count or 0),
                "typed_count": int(typed_count or 0),
                "last_visit": last_unix,
                "score": s,
            }

    ranked = sorted(items.values(), key=lambda x: x["score"], reverse=True)[:limit]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.time(), "items": ranked}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import sys
    history = os.path.expanduser("~/.config/google-chrome/Default/History")
    out = os.path.expanduser("~/.cache/ulauncher-history-shortcuts/cache.json")
    if len(sys.argv) >= 3:
        history = os.path.expanduser(sys.argv[1])
        out = os.path.expanduser(sys.argv[2])
    elif len(sys.argv) == 2:
        out = os.path.expanduser(sys.argv[1])
    build_cache(history, out)
    print("OK:", out)