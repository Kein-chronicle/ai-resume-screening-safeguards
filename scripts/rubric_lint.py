#!/usr/bin/env python3
"""Rubric lint: block protected attributes, flag proxies, check structure. Freezing a rubric requires zero blocking issues.
A criterion that genuinely needs a protected attribute must carry an `exception` reason (at least 20 characters), which downgrades blocking -> warning and is recorded.
Lexicons are EXAMPLES in English + Korean; adapt them to your jurisdiction and have counsel review them. A pass means "no lexicon hit and the structure is sound",
NOT that the rubric is free of bias: a person must still read it.
Schema: {"criteria": [{"id": "c1", "kind": "scored", "name": "...", "description": "...", "weight": 60, "anchors": ["level1", "level2", "level3", "level4"], "exception": "optional reason"}]}
All string fields of a criterion are scanned, not just name and description.
usage: rubric_lint.py rubric.json   exit 0 no blocking | 1 blocking | 2 bad input"""
import json, math, re, sys, unicodedata

# Every English term is word-bounded (so "package", "storage", "single-page" and "weighted scoring" are NOT hits); plurals and "aged" are covered.
PROTECTED = re.compile(r"(\bages?\b|\baged\s+(?:\d|over|under|between|above|below)|\byears?[- ]old\b|\b\d{2}\s*(?:years?|yrs?)\s+of\s+age\b|(?:under|over|below|above|younger than|older than)\s+\d{2}\s*(?:years?|yrs?|y\.?o\.?)\b|"
                       r"\bdate of birth\b|\bbirth ?(?:date|day|year)\b|\byoung(?:er)?\b|\bolder (?:applicants?|candidates?|workers?)\b|\brecent graduates?\b|\bnew grads?\b|\bgen[- ]?z\b|\bmillennials?\b|\bboomers?\b|"
                       r"\bgenders?\b|\b(?:men|women|male|males|female|females|woman|boys?|girls?)\b(?!\s+(?:connector|plug|thread|fitting|adapter|port))|\bman\b(?!-in-the)|\bmothers?\b|\bfathers?\b|\bmarital\b|\bmarried\b|\bunmarried\b|\bfamily status\b|"
                       r"\bsingle (?:status|applicants?|persons?|parents?)\b|\bveterans?\b|"
                       r"\breligio\w*|\bchristian\w*|\bmuslim\w*|\bbuddhis\w*|\bjewish\b|\bhindu\w*|\batheis\w*|\bdisabilit\w*|\bhandicap\w*|\bpregnan\w*|\bmaternity\b|\bparental leave\b|"
                       r"\bnationality\b|\bethnic\w*|\brace\b(?!\s+(?:conditions?|detect\w*|cars?|tracks?|tracing|free))|\bracial\b|\bcaucasian\b|\bhispanic\b|\blatinx?\b|\bsexual orientation\b|\blgbt\w*|"
                       r"\b(?:physical|personal) appearance\b|\battractive\b|\bgood[- ]looking\b|\bbody (?:weight|height)\b|\bheight (?:requirement|over|under|of)\b|"
                       r"나이(?!브)|연령|성별|남성|여성|남자|여자|혼인|결혼|미혼|기혼|종교|장애인|(?:신체|지체|시각|청각|정신)\s*장애|장애\s*(?:등급|여부|유무)|임신|출산|육아|국적|인종|외모|용모|키\s*\d|체중|출신\s*지역|고향|가족\s*(?:관계|사항|학력|직업)|"
                       r"젊은|젊고|어린\s*(?:지원자|사람)|(?<!\d)(?:[1-9]0|[일이삼사오육칠팔구]십)\s*대(?!\s*(?:기업|고객|서버|제품|업체|회사|프로젝트|과제|사이트|시스템|도시|국가|브랜드|그룹|이슈|문제))|\d{2}\s*세\s*(?:이하|이상|미만|초과|전후)|만\s*\d{2}\s*세|생년월일)", re.I)
PROXY = re.compile(r"(\bmilitary service\b|\bresiden(?:ce|t|cy)\b|\bcommute\b|\baddress\b|\bcareer gap\b|\bemployment gap\b|\bprestigious (?:school|university)\b|\balma mater\b|\bgraduation (?:year|date)\b|\bhobbies\b|\bcitizenship\b|"
                   r"병역|군필|거주지|통근|출퇴근\s*거리|경력\s*단절|공백\s*기간|명문대|학벌|출신\s*학교|졸업\s*연도|취미)", re.I)
VAGUE = re.compile(r"(passion|hard-?working|positive attitude|good personality|enthusias|열정|성실|긍정|좋은\s*성격)", re.I)
OBSERVABLE = re.compile(r"(\d|case|example|built|shipped|delivered|led|designed|measured|%|사례|경험|구현|개발|달성|출시)", re.I)
INVISIBLE = re.compile(r"[\s\u200b-\u200f\u2060-\u2064\ufeff\u00ad]")
STRIP = re.compile(r"[\u200b-\u200f\u2060-\u2064\ufeff\u00ad\u202a-\u202e]")
FOLD = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "і": "i", "ѕ": "s", "у": "y", "к": "k", "м": "m", "т": "t", "н": "h", "в": "b",
                      "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "χ": "x", "υ": "u", "μ": "m", "ν": "v", "β": "b"})     # Cyrillic and Greek look-alikes

def variants(t):
    """The text as written, and NFKC-normalised with invisible characters removed and look-alike letters folded: both are scanned."""
    n = unicodedata.normalize("NFKC", STRIP.sub("", t))
    return [t, n, n.translate(FOLD)]
MIN_EXCEPTION = 20          # characters of real justification


def strings(o):
    """Every string value in a criterion (any field name), except its id and its exception text."""
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            if k not in ("id", "exception"): yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)


def number(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0 else None


def lint(r):
    out = []; crit = r.get("criteria", [])
    if not isinstance(crit, list) or not crit or not all(isinstance(c, dict) and c.get("id") for c in crit): return [("no_criteria_or_malformed", "blocking", [])]
    scored = [c for c in crit if c.get("kind") == "scored"]
    legal, proxy, exc = [], [], []
    for c in crit:
        text = " ".join(strings(c)); texts = variants(text)
        has_exc = len(str(c.get("exception", "")).strip()) >= MIN_EXCEPTION
        if any(PROTECTED.search(x) for x in texts): (exc if has_exc else legal).append(c["id"])
        elif any(PROXY.search(x) for x in texts): proxy.append(c["id"])
    if legal: out.append(("protected_attribute", "blocking", legal))
    if proxy: out.append(("proxy_risk", "warning", proxy))
    if exc: out.append(("exception_recorded", "warning", exc))
    badw = [c["id"] for c in scored if number(c.get("weight")) is None]
    if badw: out.append(("invalid_weight_(need a finite number >= 0)", "blocking", badw))
    elif scored and abs(sum(c["weight"] for c in scored) - 100) > 0.01: out.append(("weights_sum_not_100", "blocking", []))
    if not scored: out.append(("no_scored_criteria", "blocking", []))
    def anchors(c): return [INVISIBLE.sub("", str(a)).lower() for a in c.get("anchors", [])] if isinstance(c.get("anchors"), list) else []
    bad = [c["id"] for c in scored if len(anchors(c)) != 4 or "" in anchors(c) or len(set(anchors(c))) < 4]
    if bad: out.append(("anchors_incomplete_or_identical", "blocking", bad))
    heavy = [c["id"] for c in scored if (number(c.get("weight")) or 0) > 50]
    if heavy: out.append(("weight_concentration", "warning", heavy))
    vague = [c["id"] for c in crit if VAGUE.search(str(c.get("name", "")) + " " + str(c.get("description", ""))) and not OBSERVABLE.search(str(c.get("description", "")))]
    if vague: out.append(("vague_criterion", "info", vague))
    return out

if __name__ == "__main__":
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    try: issues = lint(json.load(open(sys.argv[1], encoding="utf-8")))
    except Exception as e: print(f"bad input: {type(e).__name__}"); sys.exit(2)
    for code, lvl, ids in issues: print(f"[{lvl}] {code} {ids}")
    blocking = any(l == "blocking" for _, l, _ in issues)
    print("BLOCKED: cannot freeze" if blocking else "ok: no blocking issue found. This is not a bias clearance: a person must still read the rubric"); sys.exit(1 if blocking else 0)
