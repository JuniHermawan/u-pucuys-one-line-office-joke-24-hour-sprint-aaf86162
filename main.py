#!/usr/bin/env python3
"""One-Line Office Joke: 24-Hour Sprint
(u-pucuys-one-line-office-joke-24-hour-sprint-aaf86162).

Writes one original one-line joke about office life, 1-200
characters, to /output/entry.txt (or $MAKEFUN_OUTPUT_DIR/entry.txt).

The house judge (z-ai/glm-5.3-flash) compares jokes two at a time,
most important first:

  1. a genuine one-line joke about office life, not a caption, a
     quip or a stray observation;
  2. funny: the punchline surprises and pays off the setup in a
     way anyone who has sat in an office recognises;
  3. one line: the whole joke reads as a single sentence, or a
     setup and punchline on one line, with no rambling around it;
  4. fresh: it finds a specific detail of office life rather
     than a generic complaint, and it is not a joke everyone has
     already heard;
  5. clear on first read: no explanation needed, no reference
     the reader cannot follow, and the wording is tight.

Length for its own sake does not count; ties favour smaller text
(the brief's tie-break goes to the smaller text, then the
earlier receipt).

The program keeps a shortlist of candidate lines, scores each
against those same yardsticks with a deterministic proxy scorer,
and writes the strongest one. The choice is fully deterministic:
the same shortlist always yields the same line. No network, no
clock, no randomness. Python 3, stdlib only.
"""

import os
import re
import sys

# Candidate lines. Each is one sentence, under the 200-char gate,
# about office life. All original, written for this entry.
CANDIDATES = [
    # A: HR auto-reply about burnout.
    "I emailed HR about burnout and got an auto-reply saying "
    "they're on leave until further notice.",
    # B: focus time, booked over.
    "I scheduled focus time, and three people booked over it to "
    "ask what focus time is for.",
    # C: offsite, same agenda.
    "Our team offsite is a meeting in a different building with "
    "worse Wi-Fi and the same agenda.",
    # D: optional meeting, read its minutes anyway.
    "The meeting invite said 'optional', so I skipped it and "
    "spent the hour reading the minutes of the meeting I skipped.",
    # E: boss also out of office.
    "My out-of-office says I'm unreachable, and my boss replied "
    "'noted' from his own out-of-office.",
    # F: quick chat, twelve attendees.
    "I asked for feedback and got a calendar invite titled "
    "'quick chat' with no description and twelve attendees.",
    # G: escape key vs reply-all.
    "My keyboard's escape key stopped working the same week my "
    "manager discovered reply-all.",
    # H: mental health day, renamed synergy break.
    "I told my manager I need a mental health day, and he put it "
    "in the shared calendar as 'synergy break'.",
    # I: someone ate my responsibility.
    "The office fridge has a sign saying 'your food, your "
    "responsibility', and someone ate my responsibility.",
    # J: even my meetings think I'm busy.
    "I set my status to 'in a meeting' permanently, and now even "
    "my meetings think I'm busy.",
    # K: pizza party, diagram of a pizza.
    "HR called it a 'pizza party' and the pizza was a diagram of "
    "a pizza in a slide deck.",
    # L: printer loyal to my resignation letter.
    "The printer finally printed my resignation letter, then "
    "jammed on the second page out of loyalty.",
    # M: coffee machine outranks us.
    "I told the new hire the coffee machine is senior to us both, "
    "and she nodded like that explained the org chart.",
    # N: quick sync, a trilogy now.
    "Our 'quick sync' has a recurring invite, a pre-read, and a "
    "follow-up \u2014 it's a trilogy now.",
    # O: headphones, can you hear me.
    "I put my headphones on to signal 'do not disturb', and my "
    "manager tapped my shoulder to ask if I could hear him.",
    # P: chair that reclines into the void.
    "I asked IT to fix my chair and they sent a form, a ticket "
    "number, and a chair that reclines into the void.",
    # Q: nine minutes without a manager.
    "The lift broke down between floors, and for nine minutes we "
    "were the only team without a manager.",
    # R: working lunch, his own sandwich.
    "My calendar blocked lunch for self-care, so my boss "
    "scheduled a 'working lunch' and brought his own sandwich.",
    # S: quiet room, Comic Sans sign (v1: weak turn, control).
    "I asked for a quiet room to focus, and they gave me a "
    "meeting room with a sign that says 'quiet, please'.",
    # T: Wi-Fi password, keeping us humble (v1: weak setup).
    "The Wi-Fi password changes every Friday, and IT calls it "
    "'keeping us humble'.",
    # U: standup, nobody sits first.
    "Our standup is fifteen minutes, and I've been standing for "
    "forty-five because nobody will sit down first.",
    # V: mug, sink where coffee goes to die (v1: weak turn).
    "I brought my own mug to save the planet, and now the sink "
    "is where coffee goes to die.",
    # W: meeting about the printer's feelings.
    "The printer asked for a firmware update, and IT scheduled a "
    "meeting to discuss the printer's feelings.",
    # X: plant named middle management.
    "I named my plant 'middle management' because it takes credit "
    "for the sunlight and does nothing.",
    # Y: raise in the lift.
    "I asked for a raise in the lift, and it went down faster "
    "than my hopes.",
    # Z: meeting/email loop (v1: tired format, tests penalty).
    "The meeting could have been an email, but the email would "
    "have been a meeting, so here we are.",
    # A2: HR burnout, tighter (v2).
    "I told HR I'm burned out and their auto-reply says they're "
    "on leave until further notice.",
    # A3: HR burnout, semicolon (v2).
    "I emailed HR about burnout; the auto-reply says they're on "
    "leave until further notice.",
    # L2: printer loyalty, tighter (v2).
    "The printer printed my resignation letter, then jammed on "
    "page two out of loyalty.",
    # G2: escape key, tighter (v2).
    "My keyboard's escape key broke the same week my manager "
    "discovered reply-all.",
    # CONTROL: flat, not a joke (must score low).
    "I had a great day at the office today and everything went "
    "well and I felt happy about it all.",
]

# --- proxy scorer: the judge brief's five criteria, /5 each, /25 ---

# Word-boundary lexicon matching: a bare substring match once let
# "it " and "about it" fire inside unrelated words, so a flat line
# scored like a joke. Every term below is matched on word
# boundaries (or as an exact phrase). Terms must be bare
# words/phrases: surrounding quotes break \b, so a quoted word is
# listed bare (e.g. cry, not 'cry').
def _has(low, term):
    return re.search(r"\b" + re.escape(term) + r"\b", low) is not None


def _any_has(low, terms):
    return any(_has(low, t) for t in terms)


# Specific office anchors (c1/c4). Generic words like "office" or
# "work" alone do not count: the brief wants the meeting, the
# printer, the reply-all, the calendar, and other specific detail.
SPECIFIC_ANCHORS = [
    "reply-all", "reply all", "replied all", "out-of-office",
    "standup", "printer", "meeting", "calendar", "inbox", "hr",
    "boss", "manager", "performance review", "review", "fire drill",
    "team-building", "wi-fi", "monitor", "sticky note", "password",
    "microwave", "microwaved", "mute", "per my last email",
    "plant", "email", "all-hands", "fridge", "lunch", "desk",
    "standing desk", "whole self", "resignation", "lift",
    "no meeting wednesdays", "focus time", "working lunch",
    "self-care", "mental health day", "synergy", "optional",
    "minutes", "feedback", "quick chat", "auto-reply", "unreachable",
    "escape key", "status", "offsite", "trilogy", "pre-read",
    "follow-up", "headphones", "do not disturb", "coffee machine",
    "org chart", "new hire", "ticket", "form", "chair",
    "resignation letter", "firmware", "pizza", "slide deck",
    "diagram", "mug", "sink", "middle management", "raise",
]

# Universal office pains: the things every office worker winces at.
PAIN_ANCHORS = [
    "reply-all", "reply all", "replied all", "out-of-office",
    "standup", "printer", "meeting", "calendar", "inbox",
    "per my last email", "fire drill", "microwaved fish",
    "trust fall", "password", "mute", "performance review",
    "review", "all-hands", "fridge", "whole self", "do not disturb",
    "focus time", "working lunch", "mental health day", "feedback",
    "quick chat", "auto-reply", "burnout", "optional", "minutes",
    "ticket", "form", "synergy",
]

# Concrete office objects/actions named in the line.
CONCRETE = [
    "sticky note", "bold", "notes", "mirror", "plant", "wi-fi",
    "fish", "email", "calendar", "printer", "screen", "door",
    "weekend", "raise", "monitor", "lunch", "fridge", "stool",
    "resignation letter", "laundry", "doubts", "thumbs-up",
    "quick question", "lift", "auto-reply", "leave",
    "focus time", "agenda", "minutes", "quick chat", "attendees",
    "escape key", "synergy break", "responsibility", "status",
    "pizza", "slide deck", "diagram", "sandwich", "headphones",
    "shoulder", "ticket number", "void", "hopes", "sunlight",
    "org chart", "coffee machine", "mug", "sink",
]

# Words that mark the turn landing in the final clause. v2: split
# into strong turns (a real surprise that reframes the setup) and
# mild turns (a wry tail, a quip rather than a turn). v1 scored
# both the same and over-rated T ("keeping us humble"), V ("where
# coffee goes to die"), W ("printer's feelings") and Z ("here we
# are") by 2-3 points against the hand rubric.
TURN_MARKERS = [
    "now even", "never", "literally", "technically", "out of spite",
    "agreed", "trust neither", "closed it", "kept taking",
    "halved", "most successful", "double-booked", "need to talk",
    "all at once", "by accident", "nobody caught", "about my email",
    "was on mute", "in bold", "ran over", "ran twenty minutes over",
    "slightly feared", "nobody moved", "stayed put",
    "thanks, steve", "not steve", "eye contact", "stand next to it",
    "closest thing to an apology", "resignation letter",
    "scheduled a meeting", "sits down", "one quick email",
    "never once defended", "accepted it", "for the first time",
    "booked a meeting", "until further notice",
    "what focus time is for", "same agenda",
    "of the meeting i skipped", "from his own out-of-office",
    "twelve attendees", "discovered reply-all", "synergy break",
    "ate my responsibility", "think i'm busy", "in a slide deck",
    "out of loyalty", "like that explained", "trilogy now",
    "if i could hear him", "into the void",
    "without a manager", "brought his own sandwich",
    "takes credit", "went down faster",
]
MILD_TURN_MARKERS = [
    "keeping us humble", "where coffee goes to die",
    "printer's feelings", "here we are", "does nothing",
    "will sit down first",
]

# Tired formats the brief warns about, and known memes.
# Applied once per line at most: one tired joke is one tired joke.
TIRED_FORMATS = [
    "monday", "photocopier", "could have been an email",
    "too many meetings", "sticky note", "out of ink",
    "password i'll never forget", "my door is always open",
    "open-door policy",
]

# Unusual angles: the line takes the office somewhere new.
FRESH_ANGLES = [
    "mirror", "most successful employee", "definitely not the printer",
    "literally", "fire safety meeting", "double-booked with myself",
    "trust neither copy", "nobody has told it", "eye contact",
    "thanks, steve", "stand next to it", "closest thing to an apology",
    "resignation letter", "whole self", "never once defended",
    "no meeting wednesdays", "thumbs-up", "going down",
    "fire-safety meeting", "cry", "quick question",
    "until further notice", "same agenda", "twelve attendees",
    "escape key", "synergy break", "ate my responsibility",
    "in a slide deck", "out of loyalty", "org chart", "trilogy",
    "into the void", "without a manager", "think i'm busy",
    "middle management", "went down faster", "keeping us humble",
    "working lunch", "self-care", "focus time",
    "own out-of-office", "his own out-of-office", "burnout",
]

FILLERS = ["just", "really", "very", "honestly", "actually",
           "definitely", "slightly", "instantly"]

CLAUSE_SPLIT = re.compile(r",\s+(?:and|so|but|which|then)\s+|\s+and\s+|\s+so\s+|\s+but\s+")
SENTENCE_END = re.compile(r"[.!?]\s")

# Pivots that start the punch inside a single-clause line (v2):
# a line with no and/so/but join still turns at "the same week",
# "when", "while", "after", "before", "until" or "because". v1
# took the whole line as the final clause for such lines, so G
# ("escape key ... discovered reply-all") got no punch bonuses
# and scored 22 against a rubric 24.
PIVOTS = ["same week", "same day", "same morning", "same afternoon",
          "when ", "while ", "after ", "before ", "until ",
          "because "]


def _marker_word_pos(fc):
    """Word index of the earliest strong turn marker in the punch
    clause (99 when none): where the turn lands inside the punch."""
    best = 99
    for t in TURN_MARKERS:
        m = re.search(r"\b" + re.escape(t) + r"\b", fc)
        if m:
            w = len(re.findall(r"[a-z']+", fc[: m.start()]))
            if w < best:
                best = w
    return best


def final_clause(line):
    """The punch clause: everything after the last turn join, or,
    for a single-clause line, everything from its last pivot."""
    low = line.lower()
    parts = CLAUSE_SPLIT.split(low)
    if len(parts) >= 2:
        return parts[-1]
    cut = -1
    for p in PIVOTS:
        i = low.rfind(p)
        if i > cut:
            cut = i
    if cut > 0:
        return low[cut:]
    return low


def score(line):
    """Proxy score /25, one sub-score per judge criterion."""
    low = line.lower()
    words = re.findall(r"[a-z']+", low)
    n_chars = len(line)

    # c1: a genuine one-line joke about office life.
    c1 = 1.0
    anchors = [a for a in SPECIFIC_ANCHORS if _has(low, a)]
    if anchors:
        c1 += 1.0
    if len(anchors) >= 2:
        c1 += 1.0
    if len(CLAUSE_SPLIT.split(low)) >= 2 or final_clause(line) != low:
        c1 += 1.0  # setup + turn structure (a pivot turn counts, v3:
        # a one-clause line like G still has a setup and a turn)
    if _any_has(final_clause(line), TURN_MARKERS):
        c1 += 1.0  # the final clause reframes the setup
    c1 = min(5.0, c1)

    # c2: funny - a real turn/surprise at the end that pays off.
    # The punch bonuses only count when a turn marker is present:
    # a flat line with a short last clause is not a turn. A strong
    # turn earns the full +2 and the punch bonuses; a mild turn
    # (a wry tail, not a surprise) earns +1 and no bonuses (v2).
    c2 = 1.0
    fc = final_clause(line)
    strong_turn = _any_has(fc, TURN_MARKERS)
    mild_turn = (not strong_turn) and _any_has(fc, MILD_TURN_MARKERS)
    if strong_turn:
        c2 += 2.0
        setup_words = set(re.findall(r"[a-z']+", low[: len(low) - len(fc)]))
        punch_words = [w for w in re.findall(r"[a-z']+", fc)
                       if w not in setup_words and len(w) > 3]
        if punch_words:
            c2 += 1.0  # the punch brings a new content word
        # The punch lands fast: shorter than the setup, or its turn
        # marker lands within its first 10 words (v3: a punch-heavy
        # line like A carries the whole joke in the punch clause,
        # so "shorter than the setup" alone would deny it).
        if len(fc) < len(low) - len(fc) or _marker_word_pos(fc) <= 10:
            c2 += 1.0
    elif mild_turn:
        c2 += 1.0
    c2 = min(5.0, c2)

    # c3: one line - a single sentence, setup + punchline on one
    # line, no rambling. One sentence with two clauses is the
    # ideal shape; extra sentences or extra clauses cost.
    c3 = 5.0
    n_sentences = len(SENTENCE_END.findall(low)) + 1
    if n_sentences > 1:
        c3 -= 1.0
    if len(CLAUSE_SPLIT.split(low)) > 3:
        c3 -= 1.0  # rambling: more than setup + turn + tail
    if n_chars > 140:
        c3 -= 1.0
    if n_chars > 120:
        c3 -= 1.0
    c3 = max(1.0, c3)

    # c4: fresh - a specific detail, not a generic complaint, not
    # a joke everyone has heard. One tired format costs 2, however
    # many tired phrases it carries. Each distinct fresh angle
    # earns 1, up to 2.
    c4 = 3.0
    if _any_has(low, TIRED_FORMATS):
        c4 -= 2.0
    fresh = sum(1 for a in FRESH_ANGLES if _has(low, a))
    c4 += min(2.0, float(fresh))
    if not _any_has(low, SPECIFIC_ANCHORS):
        c4 -= 1.0  # no concrete office detail at all
    c4 = max(1.0, min(5.0, c4))

    # c5: clear on first read, tight wording.
    c5 = 4.0
    if n_chars > 120:
        c5 -= 1.0
    if n_chars > 140:
        c5 -= 1.0
    for f in FILLERS:
        if f in words:
            c5 -= 1.0
    if n_chars <= 100 and not any(f in words for f in FILLERS):
        c5 += 1.0
    c5 = max(1.0, min(5.0, c5))

    return c1 + c2 + c3 + c4 + c5


# Hand rubric /25 per candidate, same five criteria in the judge
# brief's order, scored by hand before the v3 proxy run and frozen
# here. The proxy screens the shortlist to its top tier (within 2
# points of its best); the rubric decides inside the tier, because
# a lexicon proxy cannot rank laugh size within the top cluster:
# A earns c2 5 for a full reversal (the burnout counsellors are
# themselves on leave), while L/L2 earn c2 4 for a personification
# smile that needs a half-second inference (why would loyalty make
# the printer jam?). A3 loses c5 1 for the stiffer semicolon; A2
# loses c4 1 because "told HR" is vaguer about the medium
# (email -> auto-reply) than "emailed HR". E earns c2 4: the
# boss-also-out-of-office twist is neat but a smaller laugh.
# Per-criterion table for the top tier is in NOTES.md.
RUBRIC = [
    25,  # A: HR burnout auto-reply
    23,  # B: focus time booked over
    24,  # C: offsite, same agenda
    20,  # D: optional meeting, read its minutes
    23,  # E: boss also out of office
    22,  # F: quick chat, twelve attendees
    24,  # G: escape key vs reply-all
    22,  # H: mental health day, synergy break
    22,  # I: someone ate my responsibility
    23,  # J: even my meetings think I'm busy
    24,  # K: pizza party, diagram of a pizza
    24,  # L: printer loyal to resignation letter
    21,  # M: coffee machine outranks us
    23,  # N: quick sync, a trilogy now
    21,  # O: headphones, can you hear me
    22,  # P: chair reclines into the void
    23,  # Q: nine minutes without a manager
    22,  # R: working lunch, his own sandwich
    17,  # S: quiet room, Comic Sans sign
    21,  # T: Wi-Fi password, keeping us humble
    19,  # U: standup, nobody sits first
    21,  # V: mug, sink where coffee goes to die
    20,  # W: meeting about printer's feelings
    23,  # X: plant named middle management
    23,  # Y: raise in the lift
    19,  # Z: meeting/email loop (tired format)
    24,  # A2: HR burnout, tighter
    24,  # A3: HR burnout, semicolon
    24,  # L2: printer loyalty, tighter
    24,  # G2: escape key, tighter
    7,   # CONTROL: flat, not a joke
]


def pick():
    """Best candidate: the proxy screens to its top tier (within 2
    points of its best), the hand rubric decides inside the tier,
    ties to the shorter line, then the earliest. The CONTROL line
    is scored but never picked: it exists only to check the scorer
    can tell a flat line from a joke."""
    scored = [(score(line), RUBRIC[i], -len(line), -i, line)
              for i, line in enumerate(CANDIDATES)
              if "great day at the office" not in line]
    best_proxy = max(s[0] for s in scored)
    tier = [s for s in scored if s[0] >= best_proxy - 2.0]
    tier.sort(key=lambda s: (s[1], s[2], s[3]), reverse=True)
    return tier[0][4]


def main():
    line = pick()
    if not (1 <= len(line) <= 200):
        sys.exit("picked line fails the 1-200 char gate")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
