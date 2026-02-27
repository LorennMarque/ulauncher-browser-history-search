import json
import os
import subprocess
import sys
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

ICON = "images/icon.png"
EXT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_LOADER = os.path.join(EXT_DIR, "cache_loader.py")
ACTION_LOAD_HISTORY = "run_cache_loader"


def load_cache(path):
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("items", [])
    except (json.JSONDecodeError, OSError):
        return []


def parse_blacklist(raw: str) -> list[str]:
    """List of strings to match in URL (one per line, no blanks)."""
    if not raw or not raw.strip():
        return []
    return [line.strip().lower() for line in raw.strip().splitlines() if line.strip()]


def is_blacklisted(url: str, blacklist: list[str]) -> bool:
    if not blacklist or not url:
        return False
    url_lower = url.lower()
    return any(entry in url_lower for entry in blacklist)


def get_max_results(pref: str, default: int = 12) -> int:
    try:
        n = int((pref or "").strip())
        return max(1, min(n, 50)) if n else default
    except (ValueError, TypeError):
        return default


class HistoryExt(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        cache_path = os.path.expanduser((extension.preferences.get("cache_path") or "").strip())
        chrome_history = extension.preferences.get("chrome_history", "~/.config/google-chrome/Default/History")
        query = (event.get_argument() or "").lower().strip()
        blacklist = parse_blacklist(extension.preferences.get("blacklist", "") or "")
        max_results = get_max_results(extension.preferences.get("max_results", "12") or "12")
        items = load_cache(cache_path)

        # "load" or "refresh" command: show item to run cache loader
        if query in ("load", "refresh", "reload"):
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=ICON,
                    name="Reload history",
                    description="Rebuild cache from Chrome history",
                    on_enter=ExtensionCustomAction(
                        {"action": ACTION_LOAD_HISTORY},
                        keep_app_open=False,
                    ),
                )
            ])

        results = []
        for it in items:
            title = (it.get("title") or "").lower()
            url_str = it.get("url") or ""
            if not url_str:
                continue
            if is_blacklisted(url_str, blacklist):
                continue
            url_lower = url_str.lower()
            if query and query not in title and query not in url_lower:
                continue

            results.append(
                ExtensionResultItem(
                    icon=ICON,
                    name=it.get("title") or url_str,
                    description=url_str,
                    on_enter=OpenUrlAction(url_str),
                )
            )
            if len(results) >= max_results:
                break

        if not results:
            results.append(
                ExtensionResultItem(
                    icon=ICON,
                    name="Reload history",
                    description="No matches. Rebuild cache from Chrome (run Load first if you haven't).",
                    on_enter=ExtensionCustomAction(
                        {"action": ACTION_LOAD_HISTORY},
                        keep_app_open=False,
                    ),
                )
            )

        return RenderResultListAction(results)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data() or {}
        if data.get("action") == ACTION_LOAD_HISTORY:
            cache_path = os.path.expanduser(extension.preferences.get("cache_path", "").strip())
            chrome_history = os.path.expanduser(extension.preferences.get("chrome_history", "").strip() or "~/.config/google-chrome/Default/History")
            try:
                out = subprocess.run(
                    [sys.executable, CACHE_LOADER, chrome_history, cache_path],
                    cwd=EXT_DIR,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if out.returncode == 0:
                    msg = "Cache updated"
                else:
                    msg = (out.stderr or out.stdout or "Error").strip() or "Error loading history"
            except subprocess.TimeoutExpired:
                msg = "Timeout (60 s)"
            except Exception as e:
                msg = str(e)
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=ICON,
                    name=msg,
                    description=cache_path,
                    on_enter=HideWindowAction(),
                )
            ])
        return RenderResultListAction([])


if __name__ == "__main__":
    HistoryExt().run()