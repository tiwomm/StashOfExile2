"""2.141.0 Vaal Lens (BETA), the thinking part: the board as read (vaallens.read), the tiles the game lights green
for the picked card, and that card -> where it should go (1, 2) and where it must not (touches a reward room).

The plan (rules told by the player): the gold path straight up the middle (i = 0) to Atziri; the Architect only past
the middle row (j 6-9); the key room anywhere, joined back to the paths; reward rooms (the Architect's special
cards, on the outer wall) touched by nothing - a path or room next to one connects it and it destabilizes."""
import difflib
from collections import deque

ATZIRI = (0, 10)
ENTRANCE = (0, 0)
LANE = [(0, j) for j in range(1, 10)]
ARCHITECT_ROWS = range(6, 10)
STEP = ((0, 1), (0, -1), (1, 0), (-1, 0))
# outer squares a reward card is best kept on: every other one on the two long walls, top first
BLOCKERS = [(s * 4, j) for j in (9, 7, 5, 3, 1) for s in (-1, 1)]

# a room card's printed name (any tier) -> its family
ROOMS = {
    "Garrison": ("Guardhouse", "Barracks", "Hall of War", "Warrior Assembly"),
    "Commander": ("Commander's Chamber", "Commander's Hall", "Commander's Headquarters", "Commander's Station"),
    "Armoury": ("Depot", "Arsenal", "Gallery", "Royal Reserves"),
    "Smithy": ("Bronzeworks", "Chamber of Iron", "Golden Forge", "Immaculate Forge"),
    "Generator": ("Dynamo", "Shrine of Empowerment", "Solar Nexus", "Infinite Horizon"),
    "Spymaster": ("Spymaster's Study", "Hall of Shadows", "Omnipresent Panopticon", "Espionage Core"),
    "Synthflesh Lab": ("Prosthetic Research", "Synthflesh Sanctum", "Crucible of Transcendence", "Supremacy of Function"),
    "Flesh Surgeon": ("Surgeon's Ward", "Surgeon's Theatre", "Surgeon's Symphony", "Surgical Glory"),
    "Transcendent Barracks": ("Steelflesh Quarters", "Collective Legion", "Chamber of the Perfected"),
    "Alchemy Lab": ("Chamber of Souls", "Core Machinarium", "Grand Phylactory", "Decorous Phylactory"),
    "Golem Works": ("Workshop", "Automaton Lab", "Stone Legion", "Precision of Science"),
    "Corruption Chamber": ("Crimson Hall", "Catalyst of Corruption", "Locus of Corruption", "Rapture of Corruption"),
    "Thaumaturge": ("Thaumaturge's Laboratory",),
    "Sacrificial Chamber": ("Sacrificial Chamber",),
    "Sealed Vault": ("Sealed Vault",),
}
FAMILY = {n.lower(): fam for fam, names in ROOMS.items() for n in names}
PATHS = ("path", "halls")
KEY = "royal access chamber"
# who raises whose tier when beside it (watched in game)
TOUCH = {
    "Garrison": {"Commander", "Armoury", "Spymaster", "Synthflesh Lab"}, "Commander": {"Garrison"},
    "Armoury": {"Garrison", "Smithy", "Alchemy Lab"}, "Spymaster": {"Garrison"}, "Smithy": {"Armoury", "Golem Works"},
    "Golem Works": {"Smithy"}, "Generator": {"Thaumaturge", "Sacrificial Chamber"},
    "Synthflesh Lab": {"Flesh Surgeon", "Garrison"}, "Flesh Surgeon": {"Synthflesh Lab"},
    "Alchemy Lab": {"Armoury", "Thaumaturge"},
    "Thaumaturge": {"Alchemy Lab", "Corruption Chamber", "Sacrificial Chamber", "Generator"},
    "Corruption Chamber": {"Thaumaturge", "Sacrificial Chamber"},
    "Sacrificial Chamber": {"Corruption Chamber", "Thaumaturge", "Generator"},
}


def card(name):
    """A card's printed name -> ("path", None) | ("key", None) | ("room", family) | None (not read / not known).
    2.141.0: only a name read close to a known card counts - anything else gets the ✕ marks only."""
    low = " ".join(str(name or "").lower().replace("’", "'").split())
    if not low:
        return None
    if difflib.get_close_matches(low, (KEY,), 1, 0.85):
        return ("key", None)
    if difflib.get_close_matches(low, PATHS, 1, 0.85):
        return ("path", None)
    m = difflib.get_close_matches(low, list(FAMILY), 1, 0.85)
    return ("room", FAMILY[m[0]]) if m else None


def names(board):
    """A read board -> {tile: what's there} for the taken tiles ("?" for a covered one)."""
    out = {ENTRANCE: "Entrance"}
    for c, v in board.items():
        if not isinstance(c, tuple):
            continue
        k = (v or {}).get("kind")
        if k in (None, "empty"):
            continue
        out[c] = {"path": "Path", "reward": "Reward", "architect": "Architect", "atziri": "Atziri",
                  "key": "Key Room", "room": (v.get("name") or "Room"), "unknown": "?"}.get(k, "?")
    return out


def inside(c):
    i, j = c
    return c in (ATZIRI, ENTRANCE) or (-4 <= i <= 4 and 1 <= j <= 9)


def near(c):
    return [(c[0] + di, c[1] + dj) for di, dj in STEP if inside((c[0] + di, c[1] + dj))]


def touches_reward(taken, t, kind=None):
    """Placing here joins a reward room: next to one (or, for a reward card, next to a path or room)."""
    if kind == "reward":
        return any(taken.get(n) not in (None, "Reward", "Architect", "Atziri") for n in near(t))
    return any(taken.get(n) == "Reward" for n in near(t))


def route(taken, starts, goal):
    """Fewest free tiles from any start to goal (ties: nearer the middle). -> the tiles between, or None."""
    best, q = {}, deque()
    for s in starts:
        best[s] = (0, abs(s[0]), None)
        q.append(s)
    while q:
        c = q.popleft()
        if c == goal:
            break
        for n in near(c):
            if n != goal and taken.get(n):
                continue
            cost = (best[c][0] + 1, best[c][1] + abs(n[0]))
            if n not in best or cost < best[n][:2]:
                best[n] = (*cost, c)
                q.append(n)
    if goal not in best:
        return None
    out, c = [], best[goal][2]
    while c is not None and c not in starts:
        out.append(c)
        c = best[c][2]
    return out[::-1]


def network(taken):
    """Tiles joined to the entrance through paths and rooms."""
    seen, q = {ENTRANCE}, deque([ENTRANCE])
    while q:
        c = q.popleft()
        for n in near(c):
            if n not in seen and taken.get(n) and taken[n] not in ("Architect", "Atziri", "Reward", "?"):
                seen.add(n)
                q.append(n)
    return seen


def spine(taken):
    """The gold path built so far plus what's left of it to Atziri (the route the rooms keep off)."""
    net = network(taken)
    edge = [c for c in net if any(not taken.get(n) for n in near(c))]
    return set(LANE) | set(route(taken, edge, ATZIRI) or [])


def rank(board, lit, what):
    """-> [(score, tile, why)] best first, for the lit tiles; ruled-out ones (touch a reward room) score -1000.
    what: card() of the picked card, or None (not read: only the ✕ marks count)."""
    taken = names(board)
    kind = what[0] if what else None
    lane = spine(taken)
    out = []
    for t in lit:
        if touches_reward(taken, t, kind):
            out.append((-1000, t, "touches a reward room"))
            continue
        if kind is None:
            continue
        if kind == "path":
            b = dict(taken)
            b[t] = "Path"
            r = route(b, [t], ATZIRI)
            d = len(r) + 1 if r is not None else 99
            score = -d * 10 - abs(t[0]) * 3 + (5 if t in lane else 0)
            out.append((score, t, f"{d} tiles from Atziri after this" if d < 99 else "leads nowhere new"))
        elif kind == "key":
            r = route(taken, [c for c in network(taken)] or [ENTRANCE], t)
            d = len(r) + 1 if r is not None else 99
            out.append((-d, t, f"{d} tiles from your paths"))
        else:
            fam = what[1]
            friends = sorted({taken[n] for n in near(t) if taken.get(n) in TOUCH.get(fam, ())})
            free = sum(1 for n in near(t) if not taken.get(n))
            on_lane = t in lane
            score = len(friends) * 6 + free - (8 if on_lane else 0)
            why = ["next to " + ", ".join(friends)] if friends else []
            if on_lane:
                why.append("on the gold path's way")
            why.append(f"{free} free sides")
            out.append((score, t, " · ".join(why)))
    return sorted(out, key=lambda x: (-x[0], abs(x[1][0]), x[1][1]))


def marks(board, lit, what):
    """-> {tile: ("1" | "2" | "x", why)}: the best two (when the card is known) and every ruled-out tile."""
    out, n = {}, 0
    for score, t, why in rank(board, lit, what):
        if score <= -1000:
            out[t] = ("x", why)
        elif n < 2:
            n += 1
            out[t] = (str(n), why)
    return out
