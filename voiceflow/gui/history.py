"""gui/history.py — Transcription history viewer.

A Toplevel window with:
  - Search bar and date-range / favourites filter
  - Treeview listing the 500 most recent entries (newest first)
  - Detail pane showing the full text of a selected entry
  - Export to .txt or .md, toggle favourites, clear history

Search and filter changes are debounced (250 ms) to avoid freezing the
UI when the user types quickly.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, ttk

import history as history_store

from .ui import get as get_ui


def _entries_to_txt(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        body = e.get("refined") or e.get("text", "")
        fav = " \u2605" if e.get("fav") else ""
        lines.append(f"[{e.get('ts', '')}{fav}]")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _entries_to_md(entries: list[dict]) -> str:
    lines = ["# Voice Flow transcripts", ""]
    for e in entries:
        ts = e.get("ts", "")
        fav = " \u2605" if e.get("fav") else ""
        body = e.get("refined") or e.get("text", "")
        lines.append(f"## {ts}{fav}")
        lines.append("")
        lines.append(body)
        if e.get("refined") and e.get("text") and e["refined"] != e["text"]:
            lines.append("")
            lines.append(f"<sub>raw: {e['text']}</sub>")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _parse_ts(ts_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def open_history() -> None:
    def _build(root: tk.Tk) -> None:
        win = tk.Toplevel(root)
        win.title("Voice Flow \u2014 History")
        win.geometry("780x520")

        frm = ttk.Frame(win, padding=8)
        frm.pack(fill="both", expand=True)

        # --- search / filter bar ---
        bar = ttk.Frame(frm)
        bar.pack(side="top", fill="x", pady=(0, 6))

        ttk.Label(bar, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(bar, textvariable=search_var, width=28)
        search_entry.pack(side="left", padx=(4, 12))

        ttk.Label(bar, text="Range:").pack(side="left")
        range_var = tk.StringVar(value="All")
        range_cb = ttk.Combobox(
            bar, textvariable=range_var,
            values=("All", "Today", "Last 7 days", "Last 30 days", "Favorites"),
            state="readonly", width=14,
        )
        range_cb.pack(side="left", padx=(4, 0))

        # --- tree view ---
        cols = ("fav", "ts", "text")
        tree = ttk.Treeview(frm, columns=cols, show="headings", height=12, selectmode="extended")
        tree.heading("fav", text="\u2605")
        tree.heading("ts", text="When")
        tree.heading("text", text="Transcript")
        tree.column("fav", width=30, stretch=False, anchor="center")
        tree.column("ts", width=160, stretch=False)
        tree.column("text", width=560, stretch=True)
        tree.pack(side="top", fill="both", expand=True)

        detail = tk.Text(frm, height=6, wrap="word")
        detail.pack(side="top", fill="x", pady=(8, 0))

        entries: list[dict] = []  # newest-first

        def _apply_filters(raw: list[dict]) -> list[dict]:
            # date range
            rng = range_var.get()
            now = datetime.now()
            if rng == "Today":
                cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
                raw = [e for e in raw if (ts := _parse_ts(e.get("ts", ""))) is not None and ts >= cutoff]
            elif rng == "Last 7 days":
                cutoff = now - timedelta(days=7)
                raw = [e for e in raw if (ts := _parse_ts(e.get("ts", ""))) is not None and ts >= cutoff]
            elif rng == "Last 30 days":
                cutoff = now - timedelta(days=30)
                raw = [e for e in raw if (ts := _parse_ts(e.get("ts", ""))) is not None and ts >= cutoff]
            elif rng == "Favorites":
                raw = [e for e in raw if e.get("fav")]
            # text search
            q = search_var.get().strip().lower()
            if q:
                raw = [
                    e for e in raw
                    if q in (e.get("text") or "").lower() or q in (e.get("refined") or "").lower()
                ]
            return raw

        def refresh() -> None:
            tree.delete(*tree.get_children())
            entries.clear()
            all_entries = list(reversed(history_store.load(limit=500)))
            entries.extend(_apply_filters(all_entries))
            for i, e in enumerate(entries):
                shown = e.get("refined") or e.get("text", "")
                fav_mark = "\u2605" if e.get("fav") else ""
                tree.insert("", "end", iid=str(i), values=(fav_mark, e.get("ts", ""), shown[:140]))

        def on_select(_evt) -> None:
            sel = tree.selection()
            if not sel:
                return
            entry = entries[int(sel[0])]
            detail.delete("1.0", "end")
            detail.insert("1.0", entry.get("refined") or entry.get("text", ""))

        tree.bind("<<TreeviewSelect>>", on_select)

        _debounce_id: list[str | None] = [None]  # mutable container for after() id

        def on_filter_change(*_args) -> None:
            # Cancel previous pending refresh, schedule a new one 250ms out
            try:
                if _debounce_id[0] is not None:
                    win.after_cancel(_debounce_id[0])
                _debounce_id[0] = win.after(250, refresh)
            except tk.TclError:
                pass  # window already closed

        search_var.trace_add("write", on_filter_change)
        range_var.trace_add("write", on_filter_change)

        def toggle_fav() -> None:
            sel = tree.selection()
            if not sel:
                return
            for s in sel:
                entry = entries[int(s)]
                ts = entry.get("ts", "")
                if ts:
                    history_store.toggle_favorite(ts)
            refresh()

        def selected_or_all() -> list[dict]:
            sel = tree.selection()
            if not sel:
                return entries
            return [entries[int(i)] for i in sel]

        def export(extension: str) -> None:
            picked = selected_or_all()
            if not picked:
                return
            default_name = f"voiceflow_history.{extension}"
            ftype = ("Markdown", "*.md") if extension == "md" else ("Text", "*.txt")
            path = filedialog.asksaveasfilename(
                parent=win,
                defaultextension=f".{extension}",
                initialfile=default_name,
                filetypes=[ftype, ("All files", "*.*")],
            )
            if not path:
                return
            content = _entries_to_md(picked) if extension == "md" else _entries_to_txt(picked)
            Path(path).write_text(content, encoding="utf-8")
            print(f"[history] exported {len(picked)} entries -> {path}")

        def do_clear() -> None:
            history_store.clear()
            refresh()
            detail.delete("1.0", "end")

        btns = ttk.Frame(frm)
        btns.pack(side="top", fill="x", pady=(8, 0))
        ttk.Button(btns, text="Refresh", command=refresh).pack(side="left")
        ttk.Button(btns, text="\u2605 Toggle fav", command=toggle_fav).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Export .txt", command=lambda: export("txt")).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Export .md", command=lambda: export("md")).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Clear all", command=do_clear).pack(side="left", padx=(16, 0))
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

        refresh()

    get_ui().submit(_build)
