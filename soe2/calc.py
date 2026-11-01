"""A small calculator (2.0 beta 21): type a sum, press Enter. Only arithmetic is understood (nothing is run as code).
Writing "k" after a number means thousands (12k = 12000), handy for gold."""
import ast
import math
import operator
import re
import tkinter as tk
from tkinter import ttk

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


class CalcPage:
    """Mixed into App: the Calculator window."""

    def build_calc_window(self, body):
        P1, P2 = C["panel"], C["panel2"]
        self.calc_last = None
        wrap = tk.Frame(body, bg=P1, padx=12, pady=8)
        wrap.pack(fill="both", expand=True)
        self.calc_var = tk.StringVar()
        ent = tk.Entry(wrap, textvariable=self.calc_var, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                       relief="flat", highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["accent"],
                       font=(MONO, 16), justify="right")
        ent.pack(fill="x", ipady=8)
        ent.bind("<Return>", lambda e: self.calc_go())
        ent.bind("<KP_Enter>", lambda e: self.calc_go())
        ent.bind("<Escape>", lambda e: (self.calc_var.set(""), "break")[1])
        self.calc_entry = ent
        self.calc_out = tk.Label(wrap, text="0", bg=P1, fg=C["good"], font=(MONO, 20, "bold"), anchor="e")
        self.calc_out.pack(fill="x", pady=(8, 2))
        self.calc_msg = tk.Label(wrap, text="Type a sum and press Enter.  12k = 12,000   5% = 0.05   ans = last answer",
                                 bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="e")
        self.calc_msg.pack(fill="x")
        keys = tk.Frame(wrap, bg=P1)
        keys.pack(fill="x", pady=(8, 8))
        rows = (("7", "8", "9", "÷", "C"), ("4", "5", "6", "×", "("), ("1", "2", "3", "-", ")"),
                ("0", ".", "k", "+", "="))
        for r, row in enumerate(rows):
            keys.rowconfigure(r, weight=1)
            for c, k in enumerate(row):
                keys.columnconfigure(c, weight=1, uniform="k")
                accent = k == "="
                b = tk.Label(keys, text=k, bg=C["accent"] if accent else "#22345a", fg="#ffffff",
                             font=("Segoe UI", 12, "bold"), pady=8, cursor="hand2", highlightthickness=1,
                             highlightbackground="#5b77ad")
                b.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                b.bind("<Button-1>", lambda e, kk=k: self.calc_key(kk))
        hist = tk.Frame(wrap, bg=P2, highlightthickness=1, highlightbackground=C["line"])
        hist.pack(fill="both", expand=True)
        top = tk.Frame(hist, bg=P2)
        top.pack(fill="x")
        tk.Label(top, text="HISTORY (click one to use it again)", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                 padx=8, pady=4).pack(side="left")
        self.calc_hist = tk.Listbox(hist, bg=P2, fg=C["text"], relief="flat", highlightthickness=0, height=5,
                                    font=(MONO, 10), selectbackground="#2c4a84", activestyle="none")
        self.calc_hist.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.calc_hist.bind("<<ListboxSelect>>", lambda e: self.calc_reuse())

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
        self.calc_last = v
        self.calc_out.config(text=fmt(v))
        self.calc_msg.config(text=f"{text} =", fg=C["muted"])
        self.calc_hist.insert(0, f"{text} = {fmt(v)}")
        if self.calc_hist.size() > 50:
            self.calc_hist.delete(50, "end")
        self.calc_var.set("")
        return "break"

    def calc_reuse(self):
        sel = self.calc_hist.curselection()
        if sel:
            line = self.calc_hist.get(sel[0])
            self.calc_var.set(line.rsplit(" = ", 1)[1].replace(",", ""))
            self.calc_entry.icursor("end")
            self.calc_entry.focus_set()

