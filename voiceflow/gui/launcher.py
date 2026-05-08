"""gui/launcher.py — Task chooser shown on startup.

Displays a dark-themed card grid of available task profiles (General,
Email, Coding, Creative, Meeting, Dictation).  The user picks one and
clicks Start, or double-clicks a card.  The chosen profile configures
the LLM mode and enables/disables refinement for the session.

Runs on its own temporary Tk instance (before the main UI thread is
started) and blocks the caller until a choice is made.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from modes import TASK_PROFILES, get_task_profile

# Colour palette for the dark launcher UI
BG = "#0f1117"
CARD_BG = "#1a1d27"
CARD_HOVER = "#252936"
CARD_SELECTED = "#2a3a5c"
ACCENT = "#7fb1ff"
TEXT = "#e7eaf3"
SUB_TEXT = "#8b90a0"
BORDER = "#2c3040"


def show_launcher(on_chosen: Callable[[str, bool], None]) -> None:
    """Show a task-chooser window.  Blocks until the user picks a task or
    closes the window (in which case 'general' is used as the default)."""
    result: list[str] = []  # mutable container so the inner fn can write
    closed = threading.Event()

    def _build() -> None:
        root = tk.Tk()
        root.title("Voice Flow \u2014 Choose Your Task")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Centre on screen
        w, h = 520, 530
        sx = root.winfo_screenwidth()
        sy = root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sx - w) // 2}+{(sy - h) // 2}")
        root.attributes("-topmost", True)

        # Header
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill="x", padx=28, pady=(24, 4))
        tk.Label(
            hdr, text="\U0001f399\ufe0f  Voice Flow", bg=BG, fg=ACCENT,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            hdr, text="What are you working on?", bg=BG, fg=SUB_TEXT,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 0))

        # Scrollable card area
        container = tk.Frame(root, bg=BG)
        container.pack(fill="both", expand=True, padx=20, pady=(12, 0))

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        cards_frame = tk.Frame(canvas, bg=BG)

        cards_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=cards_frame, anchor="nw", width=470)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        selected_var = tk.StringVar(value="")

        card_widgets: dict[str, tk.Frame] = {}

        def select(task_id: str) -> None:
            prev = selected_var.get()
            if prev and prev in card_widgets:
                card_widgets[prev].configure(bg=CARD_BG)
                for child in card_widgets[prev].winfo_children():
                    try:
                        child.configure(bg=CARD_BG)
                    except tk.TclError:
                        pass
            selected_var.set(task_id)
            if task_id in card_widgets:
                card_widgets[task_id].configure(bg=CARD_SELECTED)
                for child in card_widgets[task_id].winfo_children():
                    try:
                        child.configure(bg=CARD_SELECTED)
                    except tk.TclError:
                        pass

        def on_enter(task_id: str) -> None:
            if selected_var.get() == task_id:
                return
            card_widgets[task_id].configure(bg=CARD_HOVER)
            for child in card_widgets[task_id].winfo_children():
                try:
                    child.configure(bg=CARD_HOVER)
                except tk.TclError:
                    pass

        def on_leave(task_id: str) -> None:
            if selected_var.get() == task_id:
                return
            card_widgets[task_id].configure(bg=CARD_BG)
            for child in card_widgets[task_id].winfo_children():
                try:
                    child.configure(bg=CARD_BG)
                except tk.TclError:
                    pass

        for profile in TASK_PROFILES:
            tid = profile["id"]
            card = tk.Frame(
                cards_frame, bg=CARD_BG, padx=14, pady=10,
                highlightbackground=BORDER, highlightthickness=1,
            )
            card.pack(fill="x", pady=4)
            card_widgets[tid] = card

            title_text = f"{profile.get('icon', '')}  {profile['name']}"
            tk.Label(
                card, text=title_text, bg=CARD_BG, fg=TEXT,
                font=("Segoe UI", 11, "bold"), anchor="w",
            ).pack(fill="x")

            desc = profile.get("description", "")
            llm_tag = "  \u2022  LLM on" if profile.get("llm_enabled") else "  \u2022  LLM off (raw transcription)"
            tk.Label(
                card, text=desc + llm_tag, bg=CARD_BG, fg=SUB_TEXT,
                font=("Segoe UI", 9), anchor="w", wraplength=430, justify="left",
            ).pack(fill="x", pady=(2, 0))

            card.bind("<Button-1>", lambda e, t=tid: select(t))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, t=tid: select(t))
            card.bind("<Enter>", lambda e, t=tid: on_enter(t))
            card.bind("<Leave>", lambda e, t=tid: on_leave(t))

        # Bottom buttons
        bottom = tk.Frame(root, bg=BG)
        bottom.pack(fill="x", padx=28, pady=(12, 20))

        skip_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bottom, text="Don\u2019t show this again (use last task)",
            variable=skip_var, bg=BG, fg=SUB_TEXT,
            selectcolor=BG, activebackground=BG, activeforeground=SUB_TEXT,
            font=("Segoe UI", 9),
        ).pack(side="left")

        def do_start() -> None:
            chosen = selected_var.get() or "general"
            result.append(chosen)
            if skip_var.get():
                result.append("skip_launcher")
            root.destroy()

        start_btn = tk.Button(
            bottom, text="Start  \u2192", bg=ACCENT, fg="#0f1117",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=18, pady=4,
            activebackground="#5a9aee", cursor="hand2", command=do_start,
        )
        start_btn.pack(side="right")

        # Double-click a card = instant start
        def on_double(task_id: str) -> None:
            selected_var.set(task_id)
            do_start()

        for profile in TASK_PROFILES:
            tid = profile["id"]
            card_widgets[tid].bind("<Double-Button-1>", lambda e, t=tid: on_double(t))
            for child in card_widgets[tid].winfo_children():
                child.bind("<Double-Button-1>", lambda e, t=tid: on_double(t))

        # Close window = use general
        root.protocol("WM_DELETE_WINDOW", do_start)
        root.mainloop()
        closed.set()

    # Run the launcher on the current thread (avoids macOS crash)
    _build()

    chosen_id = result[0] if result else "general"
    skip = "skip_launcher" in result
    on_chosen(chosen_id, skip)




