"""Small number / time formatting helpers with no dependencies.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""




def mmss(sec):
    sec = int(max(0, sec))
    return f"{sec // 60}:{sec % 60:02d}" if sec < 3600 else f"{sec // 3600}h {sec % 3600 // 60}m"


def _num(n):
    return f"{n:.0f}" if n >= 10 else f"{n:.1f}".rstrip("0").rstrip(".")


def _amt(n):
    """A count of currency units for people: 83, 5,810, 0.4"""
    return f"{n:,.0f}" if n >= 10 else _num(n)
