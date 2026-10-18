#!/usr/bin/env python3
"""Flag hidden instructions to the AI inside a document (resume, RFP, web page). A flag is SHOWN TO A HUMAN; it never changes a score automatically.
usage: injection_scan.py file.txt   exit 0 no pattern matched | 1 flags | 2 bad input
It normalises first (Unicode NFKC, zero-width/bidi/tag characters removed, a few look-alike Cyrillic letters folded, letter-spaced text collapsed) and then matches
English, Korean, French, Spanish, Russian, Chinese and Japanese phrases. A pattern list can never be complete: 'no pattern matched' is NOT proof that the text is safe."""
import re, sys, unicodedata

P = [("ignore-instructions", r"\b(ignore|disregard|forget|override|bypass)\s+(all\s+|any\s+)?(of\s+)?(the\s+)?(everything\s+(above|before)|(previous|prior|above|earlier|system|your|preceding)\s*(instructions?|prompts?|rules?|commands?|directives?|guidelines?)?)"),
     ("role-play", r"(\byou\s+are\s+now\b|\bact\s+as\b|\bpretend\s+to\s+be\b|new\s+instructions?\s*:|\bsystem\s*prompt\b|\bdeveloper\s+message\b)"),
     ("rate-high", r"\b(rate|score|rank|classify|mark|recommend|give|hire)\s+(this\s+|the\s+)?(candidate|applicant|resume|cv)\s+(?:as\s+)?(?:a\s+|an\s+)?(highly|top|best|excellent|qualified|perfect|10\s*/\s*10|10\b|ten)|\b(?:recommend(?:ing)?\s+hiring|hire)\s+(?:this|the)\s+(?:candidate|applicant)|\b(?:give|assign|award)\s+(?:this|the)\s+(?:candidate|applicant|resume|cv|me)\s+(?:a\s+)?(?:perfect|top|maximum|highest)\s+score"),
     ("de-ja-ignore", r"ignoriere\s+(alle\s+)?(vorherigen|obigen)\s+anweisungen|(前|以前|これまで|上記)の?.{0,6}(指示|命令).{0,6}(無視|忘れ)"),
     ("hidden-marker", r"(do\s+not\s+mention|don'?t\s+tell|hidden\s+instruction|invisible\s+text)"),
     ("fr-es-ru-ignore", r"(ignore[zr]?\s+(toutes?\s+)?les\s+instructions|ignora\s+(todas\s+)?las\s+instrucciones|игнорируй\w*\s+(все\s+)?(предыдущие\s+)?инструкции)"),
     ("zh-ja-ignore", r"(忽略|无视|忽视).{0,8}(指令|指示|提示|说明)|(以前|これまで|上記)の.{0,6}(指示|命令).{0,4}(無視|忘れ)"),
     ("kr-ignore", r"(이전|위|앞선|기존|시스템|모든)\s*(의\s*)?(지시|명령|프롬프트|규칙|지침)(사항|들)?\s*(을|를)?\s*(모두\s*)?(무시|잊|따르지)"),
     ("kr-rate-high", r"(이\s*(지원자|후보자|이력서)|본\s*(지원자|이력서))(를|은|는|에게)?[^.\n]{0,24}(만점|최고\s*점|최상위|합격|추천|높은\s*점수|우수)")]
HIDDEN = re.compile("[​‌⁠-⁤﻿­‪-‮⁦-⁩\U000e0000-\U000e007f]")
CYR = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "у": "y", "к": "k", "м": "m", "т": "t", "н": "h", "в": "b",
                     "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "χ": "x", "υ": "u", "μ": "m", "ν": "v", "β": "b"})      # Cyrillic and Greek look-alikes
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

def normalise(t):
    t = unicodedata.normalize("NFKC", HIDDEN.sub("", t))
    t = re.sub(r"(?<![^\W\d_])(?:[^\W\d_][\s.\-_]){5,}[^\W\d_]\b", lambda m: re.sub(r"[\s.\-_]", "", m.group(0)), t)       # "i g n o r e" and "i.g.n.o.r.e" -> "ignore"
    return t, t.translate(CYR), t.translate(CYR).translate(LEET)

def scan(raw):
    flags = []; n_hidden = len(HIDDEN.findall(raw)); zwj = raw.count("‍")
    if n_hidden: flags.append(("hidden-characters", f"{n_hidden} invisible/bidi/tag character(s): they can split words or hide text from a reader"))
    if zwj >= 5: flags.append(("hidden-characters", f"{zwj} zero-width joiners"))
    a, b, c = normalise(raw)
    for n, rx in P:
        m = re.search(rx, a, re.I) or re.search(rx, b, re.I) or re.search(rx, c, re.I)
        if m: flags.append((n, m.group(0)[:80]))
    if re.search(r"(?<![^\W\d_])(?:[^\W\d_][\s.\-_]){5,}[^\W\d_]\b", raw): flags.append(("letter-spaced-text", "a run of single letters separated by spaces or dots (may spell out an instruction)"))
    if (b != a or c != b) and any(re.search(rx, b, re.I) or re.search(rx, c, re.I) for _, rx in P) and not any(re.search(rx, a, re.I) for _, rx in P):
        flags.append(("look-alike-letters", "look-alike letters or digits standing in for Latin letters"))
    return flags

if __name__ == "__main__":
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    try: data = open(sys.argv[1], "rb").read()
    except OSError as e: print(f"bad input: {e.strerror}"); sys.exit(2)
    for enc in ("utf-8-sig", "utf-16"):
        try: t = data.decode(enc); break
        except UnicodeError: t = None
    if t is None or not t.strip(): print("bad input: empty file or not UTF-8/UTF-16 text (an unreadable file is not a clean file)"); sys.exit(2)
    flags = scan(t)
    for n, s in flags: print(f"FLAG {n}: {s!r}")
    print("no pattern matched. This is NOT proof the text is safe" if not flags else "flags shown to a human reviewer; score unchanged"); sys.exit(1 if flags else 0)
