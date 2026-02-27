# Browser History Search (synced)

Search your actual browser history directly from ULauncher—find visited websites, most visited pages, and more. Results are synced with your actual browser history, so you get the same sites you’d see when searching in the browser.

**Currently works with Chrome.**

## How it works

The extension reads Chrome’s history database (a local SQLite file). Because Chrome locks that file while it’s running, the **load** command copies it, builds a JSON cache of your visits (URL, title, visit count, last visit), and saves it. When you search from ULauncher, it filters that cache by your query. URLs are cleaned (tracking parameters stripped) and results are ordered by how often and how recently you visited. So the list is a snapshot: run **load** again to refresh it after more browsing.

## Setup

1. **Cache your history** — Use the extension’s **load** command to build the cache. Run it whenever you want to refresh the list (e.g. after browsing).
2. **Customize** — In the extension preferences you can set how many websites to suggest (max results).

## Contributing

Feel free to contribute.
