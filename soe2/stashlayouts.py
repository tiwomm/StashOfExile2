"""2.102.0 Stash scan (beta) - where each stack sits in the fixed-slot stash tabs.

Coordinates are pixels of the stash panel's inside at a 1440-pixel-high game (PANEL x PANEL, top-left = the panel's
corner); every other size scales them by game height / 1440. A slot is (x, y, w, h) of its dark inside (70 x 70).
No pictures of anyone's stash ship with the app: only these numbers and the digit shapes (stashread.GLYPHS).

To add a tab (ROADMAP: Ritual, Expedition, Essence, Fragment, Socketables):
  1. A screenshot of the tab's inside at 1440p, cropped to the panel (like the four already done), with every slot
     filled if possible (an empty slot still works: it reads 0).
  2. Each slot's item name (Ctrl+C), left to right, top to bottom - and which slots are wildcards (any item: skip).
  3. Run tools/stash_slots.py on the screenshot: it prints the slot boxes; paste them below in reading order.
  4. Add the tab to TABS and ORDER. Sub-pages (Breach: Catalysts | Wombgifts) are their own entry; say in "page"
     which button must be lit.
Pending tabs and what each needs:
  ritual      - every Ritual omen (none owned yet to sample)
  essence     - every Essence tier (Lesser / normal / Greater / Perfect + the corrupted ones)
  fragment    - map fragments, splinters, keys
  socketables - runes, soul cores, talismans (may be several pages)"""

PANEL = 847            # the panel's inside at 1440p (it's square)
S = 70                 # a normal slot's inside


def _row(y, xs, names):
    return [(n, (x, y, S, S)) for x, n in zip(xs, names) if n]


_T = ("Orb of Transmutation", "Orb of Augmentation", "Regal Orb", "Exalted Orb", "Chaos Orb")


def _tiers(base):
    return [base, "Greater " + base, "Perfect " + base]


CURRENCY = []
for _i, _b in enumerate(_T):
    CURRENCY += _row(38 + 90 * _i, (29, 110, 191), _tiers(_b))
CURRENCY += _row(38, (299, 389, 479), ("Orb of Alchemy", "Vaal Orb", "Orb of Annulment"))
CURRENCY += _row(128, (299, 389, 479), ("Orb of Chance", "Fracturing Orb", "Divine Orb"))
CURRENCY += _row(218, (344, 434), ("Mirror of Kalandra", "Hinekora's Lock"))
CURRENCY += _row(38, (584, 664, 749), ("Lesser Jeweller's Orb", "Greater Jeweller's Orb", "Perfect Jeweller's Orb"))
CURRENCY += _row(128, (749,), ("Artificer's Orb",))
CURRENCY += _row(245, (569, 659, 749), ("Arcanist's Etcher", "Armourer's Scrap", "Blacksmith's Whetstone"))
CURRENCY += _row(335, (659, 749), ("Glassblower's Bauble", "Gemcutter's Prism"))
CURRENCY += _row(452, (749,), ("Scroll of Wisdom",))
# not read: the 4 shards (y 569; worth little), the crafting hole (370, 321) and the 2 x 7 wildcard rows (y 668, 749)

ABYSS = []
ABYSS += _row(82, (391,), ("Kulemak's Invitation",))
ABYSS += _row(213, (391,), ("Preserved Cranium",))
ABYSS += _row(301, (303, 391, 479), ("Gnawed Jawbone", "Preserved Jawbone", "Ancient Jawbone"))
ABYSS += _row(389, (259, 347, 435, 523), ("Gnawed Collarbone", "Preserved Collarbone", "Ancient Collarbone",
                                          "Altered Collarbone"))
ABYSS += _row(477, (303, 391, 479), ("Gnawed Rib", "Preserved Rib", "Ancient Rib"))
ABYSS += _row(566, (391,), ("Preserved Vertebrae",))
ABYSS += _row(697, (83, 171, 259, 347, 436, 524, 612, 700),
              ("Omen of Abyssal Echoes", "Omen of the Sovereign", "Omen of the Liege", "Omen of the Blackblooded",
               "Omen of Putrefaction", "Omen of Light", "Omen of Sinistral Necromancy", "Omen of Dextral Necromancy"))


def _liq(prefix, names):
    return [(prefix + n).strip() for n in names]


_L3 = ("Diluted Liquid Ire", "Diluted Liquid Guilt", "Diluted Liquid Greed")
_R3 = ("Liquid Disgust", "Liquid Despair", "Concentrated Liquid Fear")
_L2 = ("Liquid Paranoia", "Liquid Envy")
_R2 = ("Concentrated Liquid Suffering", "Concentrated Liquid Isolation")
DELIRIUM = []
DELIRIUM += _row(79, (339, 447), ("Simulacrum Splinter", "Simulacrum"))
DELIRIUM += _row(170, (391,), ("Raven's Reflection",))
for _y, _p in ((268, ""), (470, "Ancient ")):
    DELIRIUM += _row(_y, (94, 184, 274, 508, 598, 688), _liq(_p, _L3 + _R3))
    DELIRIUM += _row(_y + 90, (139, 229, 553, 643), _liq(_p, _L2 + _R2))
DELIRIUM += _row(678, (112, 205, 298, 481, 574, 667),
                 ("Potent Liquid Melancholy", "Potent Liquid Ferocity", "Potent Liquid Contempt",
                  "Ancient Potent Liquid Melancholy", "Ancient Potent Liquid Ferocity",
                  "Ancient Potent Liquid Contempt"))
# not read: the 3 wildcard slots down the middle (x 391)

_CAT = ("Flesh", "Neural", "Adaptive", "Uul-Netol's", "Xoph's", "Tul's", "Esh's", "Chayula's", "Carapace", "Reaver",
        "Sibilant", "Skittering", "Necrotic")
BREACH = []
BREACH += _row(140, (348, 438), ("Breach Splinter", "Breachstone"))
BREACH += [("Breachlord's Sac", (358, 231, 136, 136))]
for _y, _p in ((416, ""), (623, "Refined ")):
    BREACH += _row(_y, (168, 258, 348, 438, 528, 618), [f"{_p}{c} Catalyst" for c in _CAT[:6]])
    BREACH += _row(_y + 90, (123, 213, 303, 393, 483, 573, 663), [f"{_p}{c} Catalyst" for c in _CAT[6:]])
# Wombgifts page: not read (user's call)

# 2.114.2 (the user's Expedition tab, every slot named): Aldur's Saga's slot (74, 255) is left out - it's out of
# the game for now. The two big slots: Shattered Triskelion and The Triskelion Reforged.
_ALLOY = ("Runic", "Adaptive", "Protective", "Expansive", "Swift", "Cyclonic", "Prismatic", "Mystic", "Sovereign",
          "Celestial", "Transcendent")
EXPEDITION = []
EXPEDITION += _row(74, (165, 345, 435, 525, 615),
                   ("Expedition Logbook", "Medved's Saga", "Vorana's Saga", "Uhtred's Saga", "Olroth's Saga"))
EXPEDITION += [("Shattered Triskelion", (274, 202, 140, 140)), ("The Triskelion Reforged", (435, 202, 140, 140))]
EXPEDITION += _row(371, (255, 345, 525), ("Verisium", "Exceptional Verisium", "Liquid Verisium"))
EXPEDITION += _row(461, (255, 345, 435, 525), ("Medved's Crest of the Circle", "Vorana's Crest of the Scythe",
                                               "Uhtred's Crest of the Chalice", "Olroth's Crest of the Sun"))
EXPEDITION += _row(560, (120, 210, 300, 390, 480, 570, 660), [a + " Alloy" for a in _ALLOY[:7]])
EXPEDITION += _row(650, (165, 255, 345, 435, 525, 615), [a + " Alloy" for a in _ALLOY[7:]]
                   + ["The Runebinder's Alloy", "The Runefather's Alloy"])
EXPEDITION += _row(749, (255, 345, 435, 525), ("Blazing Flux", "Chilling Flux", "Crackling Flux", "Void Flux"))

TABS = {
    "currency": {"label": "Currency", "slots": CURRENCY},
    "abyss": {"label": "Abyss", "slots": ABYSS},
    "delirium": {"label": "Delirium", "slots": DELIRIUM},
    "breach": {"label": "Breach", "page": "Catalysts", "slots": BREACH},
    "expedition": {"label": "Expedition", "slots": EXPEDITION},
}
ORDER = ("currency", "abyss", "delirium", "breach", "expedition")
