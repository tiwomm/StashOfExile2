"""No window work from a background thread (2.117.0). Tk isn't thread-safe: a widget touched from another thread can
close the app with no message. Every threading.Thread(target=...) in soe2/ is followed - its function, and the
self.methods it calls two levels down - and any Tk call there is listed (config, insert, after, destroy, a
variable's set ...). A worker hands its result back with self.on_ui(fn, ...) / self.run_bg(work, done) or
self.ui_q.put(...); a function passed to those runs on the window's thread and isn't checked.

  py tools/check_threads.py        exit 1 if any

A name the check can't follow (another module's function) is skipped - keep those free of Tk."""
import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TK = {"config", "configure", "insert", "delete", "after", "after_idle", "after_cancel", "destroy", "pack", "grid",
      "place", "see", "selection_set", "item", "heading", "itemconfig", "itemconfigure", "title", "geometry",
      "update", "update_idletasks", "deiconify", "withdraw", "lift", "focus_set", "bell", "clipboard_clear",
      "clipboard_append", "clipboard_get", "_say", "update_status", "winfo_exists", "winfo_viewable", "winfo_width",
      "winfo_height", "event_generate", "coords", "tag_configure", "yview", "xview", "attributes",
      "overrideredirect", "iconify", "grab_set", "wait_window"}
QUEUED = {"put", "on_ui", "run_bg"}          # what's passed to these runs on the window's thread
DEPTH = 2


def load():
    trees, methods = {}, {}
    for p in sorted(glob.glob(os.path.join(ROOT, "soe2", "*.py"))):
        t = ast.parse(open(p, encoding="utf-8").read())
        trees[p] = t
        for n in ast.walk(t):
            if isinstance(n, ast.FunctionDef):
                methods.setdefault(n.name, []).append(n)
    return trees, methods


def tk_calls(fn, methods, depth=0, seen=None):
    """[(line, text)] - Tk calls in fn's body that aren't handed to the queue."""
    seen = set() if seen is None else seen
    out = []

    def visit(n, queued):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if not queued and name in TK:
                out.append((n.lineno, ast.unparse(n)[:100]))
            if (not queued and depth < DEPTH and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                    and f.value.id == "self" and name not in TK and name not in QUEUED and name not in seen):
                seen.add(name)
                for m in methods.get(name, []):
                    out.extend((n.lineno, f"self.{name}() -> line {ln}: {s}")
                               for ln, s in tk_calls(m, methods, depth + 1, seen))
            visit(f, queued)
            for a in n.args + [k.value for k in n.keywords]:
                visit(a, queued or name in QUEUED)
            return
        if isinstance(n, (ast.Lambda, ast.FunctionDef)) and queued:
            return
        for c in ast.iter_child_nodes(n):
            visit(c, queued)

    for st in (fn.body if isinstance(fn.body, list) else [fn.body]):
        visit(st, False)
    return out


def threads(tree):
    """(local functions by name, the Thread call) for every threading.Thread(...) - local = defined in the same
    function (so each `def work()` is the right one)."""
    for outer in ast.walk(tree):
        if not isinstance(outer, (ast.FunctionDef, ast.Module)):
            continue
        local, calls = {}, []

        def own(node):
            for c in ast.iter_child_nodes(node):
                if isinstance(c, ast.FunctionDef):
                    local[c.name] = c
                    continue
                if isinstance(c, ast.Call) and ast.unparse(c.func).endswith("Thread"):
                    calls.append(c)
                own(c)
        own(outer)
        for c in calls:
            yield local, c


def main():
    trees, methods = load()
    found = []
    for p, t in trees.items():
        for local, call in threads(t):
            tgt = next((k.value for k in call.keywords if k.arg == "target"), None)
            fn = None
            if isinstance(tgt, ast.Lambda):
                fn = tgt
            elif isinstance(tgt, ast.Name):
                fn = local.get(tgt.id)
            elif isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                fn = (methods.get(tgt.attr) or [None])[0]
            if fn is None:
                continue
            for ln, s in tk_calls(fn, methods):
                found.append(f"{os.path.relpath(p, ROOT)}:{call.lineno} (thread) line {ln}: {s}")
    for f in found:
        print(f)
    if found:
        print(f"\n{len(found)} Tk call(s) from a background thread - hand them back with self.on_ui / run_bg.")
        return 1
    print("OK - no window work from a background thread")
    return 0


if __name__ == "__main__":
    sys.exit(main())
