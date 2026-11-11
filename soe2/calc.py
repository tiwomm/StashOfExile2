"""A small calculator (2.0 beta 21; 2.74.0: over the game, from the overlay's bar): type a sum, press Enter. Only arithmetic is understood (nothing is run as code).
Writing "k" after a number means thousands (12k = 12000), handy for gold."""
import ast
import math
import operator
import re
import tkinter as tk

from .style import C, MONO

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "round": round, "abs": abs, "min": min, "max": max, "floor": math.floor,
          "ceil": math.ceil}


def evaluate(text, last=None):
    """'12k / 3 + 5%' -> a number. Raises ValueError with a short reason for anything that isn't a sum."""
    t = (text or "").strip().replace(",", "").replace("×", "*").replace("÷", "/").replace("^", "**")
    if not t:
        raise ValueError("type a sum")
    t = re.sub(r"(\d+(?:\.\d+)?)\s*[kK]\b", r"(\1*1000)", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*[mM]\b", r"(\1*1000000)", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", t)
    if last is not None:
        t = re.sub(r"\bans\b", repr(last), t, flags=re.I)
        if re.match(r"^\s*[*/+]", t):                  # "* 2" carries on from the last answer
            t = repr(last) + t
    try:
        tree = ast.parse(t, mode="eval")
    except SyntaxError:
        raise ValueError("that isn't a sum")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100:
                raise ValueError("power too big")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        if isinstance(n, ast.Name) and n.id == "pi":
            return math.pi
        raise ValueError("only numbers and + - * / ( ) are understood")
    try:
        return ev(tree)
    except ZeroDivisionError:
        raise ValueError("can't divide by zero")


def fmt(v):
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        v = int(v)
    if isinstance(v, int):
        return f"{v:,}"
    return f"{v:,.6f}".rstrip("0").rstrip(".")


class CalcOverlay:
    """Mixed into App (2.74.0): the calculator over the game - a small window of a fixed size, like Notes: dragged
    where you want it, held by the overlay's one lock, in the overlay's look. Opened from Calc on the overlay's bar
    (Overlay › Options: its own switch, and whether it's on the bar). Feedback: "move the calculator ... into the
    overlay ... dragged around the screen and locked / unlocked. Keep this at a fixed size."
    GGG ToS: a window of the app's own - you type into it, nothing is sent to the game."""

    W = 248                                              # the window's fixed width (its height follows its keys)
    KEYS = (("7", "8", "9", "÷", "C"), ("4", "5", "6", "×", "("), ("1", "2", "3", "-", ")"),
            ("0", ".", "k", "+", "="))

    def calc_cfg(self):
        from .config import SETTINGS
        c = SETTINGS.setdefault("calc_ov", {})
        c.setdefault("on", True)
        c.setdefault("shown", False)
        c.setdefault("x", None)
        c.setdefault("y", None)
        return c

    def calc_save(self):
        from .config import SETTINGS, save_json
        save_json("settings.json", SETTINGS)

    def calc_on_bar(self):
        return bool(self.calc_cfg()["on"]) and bool(self.bar_cfg().get("calc", True))

    def calc_ov_shown(self):
        w = getattr(self, "calc_win", None)
        return w is not None and w.winfo_exists() and getattr(w, "wanted", False)

    def calc_ov_toggle(self, show=None):
        """Show / hide it (show None: flip). -> shown."""
        show = (not self.calc_ov_shown()) if show is None else bool(show)
        if show and not self.calc_cfg()["on"]:
            self._say("The calculator is switched off: Overlay › Overlay Settings › On the bar › Calc.", 8)
            return False
        if show:
            if not self.calc_ov_shown():
                self.calc_ov_build()
                self.calc_win.show()
            try:
                self.calc_entry.focus_set()
            except tk.TclError:
                pass
        else:
            self.calc_ov_close(remember=False)
        self.calc_cfg()["shown"] = show
        self.calc_save()
        if getattr(self, "mg_win", None) is not None:
            self.merged_build()                          # (Calc ▾ / ▴ on the bar)
        return show

    def calc_ov_restore(self):
        c = self.calc_cfg()
        if c["on"] and c["shown"] and self.ov_enabled():          # 2.92.2: not while the overlay is disabled
            try:
                self.calc_ov_toggle(True)
            except Exception:
                self.log_error("showing the calculator")

    def calc_ov_close(self, remember=True):
        w, self.calc_win = getattr(self, "calc_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
        if remember:
            self.calc_cfg()["shown"] = False
            self.calc_save()
            if getattr(self, "mg_win", None) is not None:
                self.merged_build()

    def calc_ov_restyle(self):
        """The overlay's lock or the theme changed: built again, where it was."""
        if self.calc_ov_shown():
            self.calc_ov_close(remember=False)
            self.calc_ov_build()
            self.calc_win.show()

    def _calc_spot(self):
        c = self.calc_cfg()
        if c["x"] is not None and c["y"] is not None:
            return int(c["x"]), int(c["y"])
        from .alerts_page import game_rect                # first time: right of the screen's middle, above the bar
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        return r[0] + int(r[2] * 0.70), r[1] + int(r[3] * 0.45)

    def calc_ov_build(self):
        from .overlaywin import OverlayWindow, pal
        P = pal()
        bg, txt, mut = P["bg"], P["text"], P["muted"]
        locked = bool(self.tracker_cfg().get("mlocked"))

        def moved(x, y, _w, _h):
            self.calc_cfg().update(x=int(x), y=int(y))
            self.calc_save()
        x, y = self._calc_spot()
        w = OverlayWindow(self.root, "Calculator", "🧮", (x, y, None, None), palette=P, locked=locked,
                          on_lock=self.overlay_lock, on_close=lambda: self.calc_ov_close(), on_moved=moved,
                          follow_game=True, resizable=False)
        w.withdraw()
        body = tk.Frame(w.body, bg=bg, padx=8, pady=8)
        body.pack(fill="both", expand=True)
        self.calc_last = getattr(self, "calc_last", None)
        self.calc_var = tk.StringVar()
        ent = tk.Entry(body, textvariable=self.calc_var, bg=P["field"] if P.get("field") else P["cell_bg"], fg=txt,
                       insertbackground=txt, relief="flat", highlightthickness=1, highlightbackground=P["line"],
                       highlightcolor=P["head"], font=(MONO, self.ov_font(12)), justify="right", width=1)
        ent.pack(fill="x", ipady=4)
        ent.bind("<Return>", lambda e: self.calc_go())
        ent.bind("<KP_Enter>", lambda e: self.calc_go())
        ent.bind("<Escape>", lambda e: (self.calc_var.set(""), "break")[1])
        self.calc_entry = ent
        self.calc_out = tk.Label(body, text=fmt(self.calc_last) if self.calc_last is not None else "", bg=bg,   # (2.114.0: blank, not "0")
                                 fg=P["head"], font=(MONO, self.ov_font(16), "bold"), anchor="e")
        self.calc_out.pack(fill="x", pady=(4, 0))
        self.calc_msg = tk.Label(body, text="12k = 12,000  ·  ans = last", bg=bg, fg=mut, font=(P["font"], self.ov_font(8)),
                                 anchor="e")
        self.calc_msg.pack(fill="x")
        keys = tk.Frame(body, bg=bg)
        keys.pack(fill="x", pady=(4, 0))
        self.calc_keys = {}
        for r, row in enumerate(self.KEYS):
            for c, k in enumerate(row):
                keys.columnconfigure(c, weight=1, uniform="k")
                eq = k == "="
                b = tk.Label(keys, text=k, bg=P["on_bg"] if eq and P.get("on_bg") else P["cell_bg"],
                             fg=P["head"] if eq else txt, font=(P["font"], self.ov_font(10), "bold"), pady=4, cursor="hand2",
                             highlightthickness=1, highlightbackground=P["on_line"] if eq and P.get("on_line")
                             else P.get("cell_line") or P["line"])
                b.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                b.bind("<Button-1>", lambda e, kk=k: self.calc_key(kk))
                self.calc_keys[k] = b
        tk.Label(body, text="RECENT  ·  click one to use it", bg=bg, fg=P["head"], font=(P["hfont"] or P["font"], self.ov_font(8), "bold"),
                 anchor="w").pack(fill="x", pady=(8, 0))
        self.calc_hist = tk.Listbox(body, bg=bg, fg=mut, relief="flat", highlightthickness=0, height=3,
                                    font=(P["font"], self.ov_font(10)), selectbackground=P["cell_bg"], selectforeground=txt,
                                    activestyle="none", width=1)
        self.calc_hist.pack(fill="x")
        for line in getattr(self, "_calc_lines", [])[:3]:
            self.calc_hist.insert("end", line)
        if not self.calc_hist.size():
            self.calc_hist.insert("end", "nothing yet")
        self.calc_hist.bind("<<ListboxSelect>>", lambda e: self.calc_reuse())
        w.update_idletasks()
        w.geometry(f"{self.ov_px(self.W)}x{w.winfo_reqheight()}")      # 2.78.3: the game's size      # a fixed size: as wide as W, as tall as its keys
        self.calc_win = w
        return w

    def calc_key(self, k):
        if k == "C":
            self.calc_var.set("")
        elif k == "=":
            self.calc_go()
        else:
            self.calc_entry.insert("end", {"÷": "/", "×": "*"}.get(k, k))
        self.calc_entry.focus_set()

    def calc_go(self):
        text = self.calc_var.get()
        try:
            v = evaluate(text, self.calc_last)
        except (ValueError, TypeError, OverflowError) as e:
            self.calc_msg.config(text=str(e).capitalize() + ".", fg=C["red"])
            return "break"
        from .overlaywin import pal
        self.calc_last = v
        self.calc_out.config(text=fmt(v))
        self.calc_msg.config(text=f"{text} =", fg=pal()["muted"])
        line = f"{text} = {fmt(v)}"
        self._calc_lines = [line] + getattr(self, "_calc_lines", [])[:49]
        if not getattr(self, "_calc_lines", [])[1:]:
            self.calc_hist.delete(0, "end")                  # (the "nothing yet" line)
        self.calc_hist.insert(0, line)
        if self.calc_hist.size() > 3:
            self.calc_hist.delete(3, "end")
        self.calc_var.set("")
        return "break"

    def calc_reuse(self):
        sel = self.calc_hist.curselection()
        if sel and " = " in self.calc_hist.get(sel[0]):
            line = self.calc_hist.get(sel[0])
            self.calc_var.set(line.rsplit(" = ", 1)[1].replace(",", ""))
            self.calc_entry.icursor("end")
            self.calc_entry.focus_set()
