# --- START OF FILE launcher.py ---
# MultiAgent BrainEngine 2 — launcher.
# Opens the setup window. Press Continue and your settings are saved to
# engine/config.json, then the server starts in this same console window.
# Press Cancel (or close the window) and nothing starts.

import json
import os
import ssl
import sys
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = HERE  # the launcher lives inside engine/ alongside the server
CONFIG_FILE = os.path.join(ENGINE, "config.json")
PORT = 8001
SERVER_URL = f"http://127.0.0.1:{PORT}/v1"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            pass
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def test_provider(base_url, api_key):
    """Ask the provider for its model list. True = it answered."""
    url = base_url.rstrip("/")
    if not url.endswith("/models"):
        url += "/models"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8001",
        "X-Title": "BrainEngine2",
    })
    with urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context()) as r:
        return r.status == 200


# =========================================================
# SETUP WINDOW
# =========================================================
import tkinter as tk
from tkinter import messagebox

BG     = "#101613"
CARD   = "#18211c"
BORDER = "#2a3830"
INK    = "#e6e2d6"
MUTED  = "#8a9a8f"
AMBER  = "#e8c47a"
SAGE   = "#9db4a6"
ROSE   = "#d99a8f"
FONT   = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_S = ("Segoe UI", 8, "bold")
FONT_T = ("Segoe UI", 16, "bold")
FONT_D = ("Georgia", 15, "bold")     # guide display headings
FONT_H = ("Georgia", 12, "bold")
FONT_N = ("Georgia", 19, "bold")     # step numbers
FONT_M = ("Consolas", 10)            # the address, in code style
WARN_BG = "#251d13"
WARN_BD = "#5c4522"


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MultiAgent BrainEngine 2 — Setup")
        self.geometry("600x720")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.result = None

        cfg = load_config()
        main = cfg.get("main") or {}
        logic = cfg.get("logic") or {}

        tk.Label(self, text="MultiAgent BrainEngine 2", bg=BG, fg=AMBER,
                 font=FONT_T, anchor="w").pack(fill="x", padx=24, pady=(20, 2))
        tk.Label(self, text="Check your API settings, then press Continue to start the server.",
                 bg=BG, fg=MUTED, font=FONT, anchor="w").pack(fill="x", padx=24, pady=(0, 14))

        main_card = self._card("MAIN PROVIDER  ·  used for the Director and the Writer  ·  required")
        self.main_key   = self._field(main_card, "API key", main.get("api_key", ""), secret=True)
        self.main_model = self._field(main_card, "Model name", main.get("model", ""))
        self.main_url   = self._field(main_card, "Base URL", main.get("base_url", ""))
        self.main_status = self._test_row(main_card, lambda: self._run_test(
            self.main_url.get(), self.main_key.get(), self.main_status))

        opt_card = self._card("BACKGROUND PROVIDER  ·  cheaper model for the hidden thinking  ·  optional")
        self.logic_on = tk.BooleanVar(
            value=bool(logic.get("api_key") or logic.get("model") or logic.get("base_url")))
        tk.Checkbutton(opt_card, text="Use a separate (cheaper) model for the background agents",
                       variable=self.logic_on, bg=CARD, fg=INK, selectcolor=BG,
                       activebackground=CARD, activeforeground=INK, font=FONT,
                       command=self._toggle_logic).pack(anchor="w", padx=14, pady=(4, 6))
        self.logic_key   = self._field(opt_card, "API key", logic.get("api_key", ""), secret=True)
        self.logic_model = self._field(opt_card, "Model name", logic.get("model", ""))
        self.logic_url   = self._field(opt_card, "Base URL", logic.get("base_url", ""))
        self.logic_status = self._test_row(opt_card, lambda: self._run_test(
            self.logic_url.get(), self.logic_key.get(), self.logic_status))
        self._toggle_logic()

        tk.Label(self, text="Settings are saved on this computer only, in engine\\config.json.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=26, pady=(10, 0))

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=24, pady=(14, 20))
        tk.Button(footer, text="Cancel", bg=CARD, fg=MUTED, activebackground=BORDER,
                  activeforeground=INK, relief="flat", font=FONT_B, padx=20, pady=8,
                  cursor="hand2", command=self._cancel).pack(side="right")
        tk.Button(footer, text="Continue  →", bg=AMBER, fg="#20241c", activebackground="#f2d492",
                  relief="flat", font=FONT_B, padx=26, pady=8, cursor="hand2",
                  command=self._continue).pack(side="right", padx=(0, 12))
        tk.Button(footer, text="SillyTavern setup guide", bg=BG, fg=SAGE, activebackground=BG,
                  activeforeground=AMBER, relief="flat", font=("Segoe UI", 9, "underline"),
                  cursor="hand2", command=self.open_guide).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # first run ever: open the guide on top of the settings automatically
        if not os.path.exists(CONFIG_FILE):
            self.after(350, self.open_guide)

    # ---------- widget helpers ----------
    def _card(self, title):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="x", padx=24, pady=7)
        tk.Label(wrap, text=title, bg=BG, fg=SAGE, font=FONT_S, anchor="w").pack(fill="x", pady=(0, 3))
        card = tk.Frame(wrap, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x")
        return card

    def _field(self, parent, label, value, secret=False):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=14, pady=5)
        tk.Label(row, text=label, bg=CARD, fg=MUTED, font=FONT, width=11,
                 anchor="w").pack(side="left")
        entry = tk.Entry(row, bg=BG, fg=INK, insertbackground=INK, relief="flat",
                         font=FONT, show="●" if secret else "")
        entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(6, 0))
        if secret:
            def toggle(v=[False]):
                v[0] = not v[0]
                entry.config(show="" if v[0] else "●")
                btn.config(text="hide" if v[0] else "show")
            btn = tk.Button(row, text="show", bg=CARD, fg=SAGE, activebackground=CARD,
                            relief="flat", font=("Segoe UI", 8), cursor="hand2", command=toggle)
            btn.pack(side="left", padx=(6, 0))
        return entry

    def _test_row(self, parent, command):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=14, pady=(2, 10))
        tk.Button(row, text="Test connection", bg=CARD, fg=SAGE, activebackground=CARD,
                  relief="flat", font=FONT_S, cursor="hand2", command=command).pack(side="left", padx=(88, 8))
        status = tk.Label(row, text="", bg=CARD, font=("Segoe UI", 9))
        status.pack(side="left")
        return status

    def _toggle_logic(self):
        state = "normal" if self.logic_on.get() else "disabled"
        for entry in (self.logic_key, self.logic_model, self.logic_url):
            entry.config(state=state)

    def _run_test(self, url, key, status_label):
        url, key = url.strip(), key.strip()
        if not url or not key:
            status_label.config(text="enter the URL and key first", fg=ROSE)
            return
        status_label.config(text="testing…", fg=MUTED)
        def work():
            try:
                ok = test_provider(url, key)
                msg, col = ("connection OK ✓", SAGE) if ok else ("unexpected answer from provider", ROSE)
            except Exception as e:
                msg, col = (f"failed: {str(e)[:70]}", ROSE)
            self.after(0, lambda: status_label.config(text=msg, fg=col))
        threading.Thread(target=work, daemon=True).start()

    # ---------- buttons ----------
    def _continue(self):
        key   = self.main_key.get().strip()
        model = self.main_model.get().strip()
        url   = self.main_url.get().strip()
        if not (key and model and url):
            messagebox.showwarning("Missing settings",
                "The main provider needs all three fields:\nAPI key, model name and base URL.")
            return
        cfg = {"main": {"api_key": key, "model": model, "base_url": url}}
        if self.logic_on.get():
            lkey   = self.logic_key.get().strip()
            lmodel = self.logic_model.get().strip()
            lurl   = self.logic_url.get().strip()
            if not (lkey and lmodel and lurl):
                messagebox.showwarning("Missing settings",
                    "The background provider is enabled but incomplete.\n\n"
                    "Fill its three fields — or untick the box to use the\nmain provider for everything.")
                return
            cfg["logic"] = {"api_key": lkey, "model": lmodel, "base_url": lurl}
        save_config(cfg)
        self.result = "continue"
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def open_guide(self):
        if getattr(self, "_guide", None) and self._guide.winfo_exists():
            self._guide.focus_set()
            return
        self._guide = GuideWindow(self)


# =========================================================
# SILLYTAVERN SETUP GUIDE
# =========================================================
class GuideWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Connecting SillyTavern — Guide")
        self.geometry("660x720")
        self.configure(bg=BG)
        self.transient(parent)

        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        bar = tk.Scrollbar(self, orient="vertical", command=canvas.yview,
                           bg=CARD, troughcolor=BG, width=10)
        self.page = tk.Frame(canvas, bg=BG)
        self.page.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.page, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._build()

    # ---------- content ----------
    def _build(self):
        p = self.page

        tk.Label(p, text="Connecting SillyTavern", bg=BG, fg=AMBER,
                 font=FONT_D, anchor="w").pack(fill="x", padx=28, pady=(24, 4))
        tk.Label(p, text="Two quick steps, about a minute. You only do this once.",
                 bg=BG, fg=MUTED, font=FONT, anchor="w").pack(fill="x", padx=28, pady=(0, 18))

        # ---- step 1 ----
        self._step(p, "1", "Point SillyTavern at the server")
        self._bullet(p, "Open SillyTavern.")
        self._bullet(p, "Click the API Connections tab — the plug icon at the top.")
        self._bullet(p, "Select  Chat Completion  →  Custom (OpenAI-compatible).")
        self._bullet(p, "Paste this into the Base URL field:")
        self._url_row(p)
        self._bullet(p, "Hit Connect.")

        # ---- step 2 (critical) ----
        self._step(p, "2", "Turn on reasoning", required=True)
        warn = tk.Frame(p, bg=WARN_BG, highlightbackground=WARN_BD, highlightthickness=1)
        warn.pack(fill="x", padx=28, pady=(0, 10))
        self._bullet(warn, "Click the Advanced Formatting tab — the “A” icon on the top menu bar.", bg=WARN_BG)
        self._bullet(warn, "Find the Reasoning section.", bg=WARN_BG)
        self._bullet(warn, "Turn on  “Add to prompt”.", bg=WARN_BG)
        self._bullet(warn, "Set  “Max number of thinking blocks to add”  to a high number (e.g. 100).", bg=WARN_BG)
        why = tk.Frame(warn, bg=WARN_BG)
        why.pack(fill="x", padx=16, pady=(4, 14))
        tk.Label(why, text="Why this matters", bg=WARN_BG, fg=AMBER,
                 font=FONT_S, anchor="w").pack(fill="x")
        tk.Label(why, bg=WARN_BG, fg=INK, font=("Segoe UI", 9), anchor="w", justify="left",
                 text="After every reply, SillyTavern tucks the character's hidden thoughts away.\n"
                      "This setting hands them back to the engine on the next turn — that's how\n"
                      "the character keeps the thread of its inner voice from message to message.\n"
                      "Without it the engine still runs, but that short-term emotional continuity\n"
                      "is lost.").pack(fill="x", pady=(3, 0))

        # ---- closing note ----
        note = tk.Frame(p, bg=BG)
        note.pack(fill="x", padx=28, pady=(14, 26))
        tk.Label(note, text="That's it — streaming can stay on or off, both work.\n"
                            "Close this guide whenever you're ready.",
                 bg=BG, fg=SAGE, font=("Segoe UI", 9), anchor="w",
                 justify="left").pack(fill="x")

    # ---------- pieces ----------
    def _step(self, parent, number, title, required=False):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=28, pady=(10, 6))
        tk.Label(row, text=number, bg=BG, fg=AMBER, font=FONT_N).pack(side="left")
        tk.Label(row, text=title, bg=BG, fg=INK, font=FONT_H,
                 anchor="w").pack(side="left", padx=(14, 0), pady=(6, 0))
        if required:
            tk.Label(row, text="REQUIRED", bg=AMBER, fg="#20241c", font=("Segoe UI", 7, "bold"),
                     padx=7, pady=2).pack(side="left", padx=(12, 0), pady=(8, 0))

    def _bullet(self, parent, text, bg=BG):
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", padx=16 if bg != BG else 28, pady=2)
        tk.Label(row, text="·", bg=bg, fg=SAGE, font=FONT_B).pack(side="left", padx=(26, 8))
        tk.Label(row, text=text, bg=bg, fg=INK, font=FONT, anchor="w").pack(side="left")

    def _url_row(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=28, pady=(6, 4))
        box = tk.Frame(row, bg="#0b100d", highlightbackground=BORDER, highlightthickness=1)
        box.pack(side="left", padx=(34, 10))
        tk.Label(box, text=SERVER_URL, bg="#0b100d", fg=AMBER, font=FONT_M,
                 padx=12, pady=6).pack()
        btn = tk.Button(row, text="copy", bg=CARD, fg=SAGE, activebackground=BORDER,
                        activeforeground=INK, relief="flat", font=FONT_S, padx=14, pady=5,
                        cursor="hand2")
        btn.config(command=lambda: self._copy(btn))
        btn.pack(side="left")

    def _copy(self, btn):
        self.clipboard_clear()
        self.clipboard_append(SERVER_URL)
        btn.config(text="copied ✓", fg=AMBER)
        self.after(1800, lambda: btn.config(text="copy", fg=SAGE) if btn.winfo_exists() else None)


# =========================================================
# START
# =========================================================
def main():
    app = Launcher()
    app.mainloop()
    if app.result != "continue":
        return

    os.chdir(ENGINE)
    sys.path.insert(0, ENGINE)
    print()
    print("=" * 62)
    print("  MultiAgent BrainEngine 2")
    print(f"  SillyTavern address : http://127.0.0.1:{PORT}/v1")
    print(f"  Diary               : http://127.0.0.1:{PORT}/diary")
    print("  Stop the server with Ctrl+C")
    print("=" * 62)
    try:
        import uvicorn
        uvicorn.run("server:app", host="127.0.0.1", port=PORT)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        input("Press Enter to close...")


if __name__ == "__main__":
    main()
