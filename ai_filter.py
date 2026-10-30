"""AI relevance gate — decides by the WHOLE story, not by blocked words.

Owner, 21 Oct 2026: "we shouldn't block words we need to block the news if not related —
if we keep blocking words it won't work". Each new headline (with its summary when there
is one) is judged once by a small model: would a NEPSE investor care about this news?
Decisions are remembered in ai_decisions.json, so a story is never asked about twice.
If GEMINI_API_KEY is missing or the AI fails, main.py falls back to the keyword rules.
"""
import json
import os
import time

import requests

CACHE_FILE = 'ai_decisions.json'
CACHE_MAX = 5000
BATCH = 20
BUDGET = 150  # seconds of AI time per run at most (the bot runs every 5 min)
_deadline = [0.0]
KEY = os.environ.get('GEMINI_API_KEY', '')
MODELS = [m for m in [os.environ.get('GEMINI_MODEL'), 'gemini-3.5-flash-lite', 'gemini-flash-lite-latest', 'gemini-3.8-flash', 'gemini-flash-latest'] if m]

PROMPT = """You filter news for a Telegram channel read by NEPSE (Nepal Stock Exchange) investors.
For each item decide KEEP (true) only if it could matter to someone investing in Nepal's share market:
- any NEPSE-listed company or its sector: banks, development banks, finance, microfinance, insurance,
  hydropower, manufacturing, hotels, telecom, investment companies, mutual funds — results, dividends,
  bonus/right shares, AGMs, mergers, IPO/FPO/debentures, management changes, regulatory action, plant
  outages or damage
- the market itself: NEPSE index, turnover, SEBON, NRB, CDSC, brokers, MeroShare, listing, trading rules
- Nepal's economy and money: monetary policy, interest rates, liquidity, remittance, inflation, budget,
  taxes, trade, forex/gold prices in Nepal, government decisions on business or energy
- disasters or events that damage hydropower, roads, power supply or big companies
DROP (false): crime, accidents, party politics and personalities, festivals, religion, culture, sports,
entertainment, weather without economic damage, health, foreign companies or tycoons with no Nepal market
link, world listicles, CSR / charity / sponsorship PR, lifestyle and photo features.
When unsure whether a Nepal business story matters, KEEP it.
Reply with JSON only: [{"i": <index>, "keep": true|false}] covering every index."""


def load_cache():
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    items = list(cache.items())[-CACHE_MAX:]
    with open(CACHE_FILE, 'w') as f:
        json.dump(dict(items), f, ensure_ascii=False, indent=0)


def _ask(batch):
    lines = []
    for i, n in enumerate(batch):
        s = (n.get('summary') or '').strip().replace('\n', ' ')[:200]
        lines.append(f"{i}. [{n.get('source', '')}] {n.get('headline', '')}" + (f" — {s}" if s else ''))
    body = {
        'systemInstruction': {'parts': [{'text': PROMPT}]},
        'contents': [{'role': 'user', 'parts': [{'text': '\n'.join(lines)}]}],
        'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'maxOutputTokens': 4096},
    }
    for model in MODELS:
        for attempt in (1, 2):  # Google is often briefly busy (503) — one retry per model
            if time.time() > _deadline[0]:
                print('[AI] time budget used up — keyword rules for the rest')
                return None
            got = _try(model, body, len(batch))
            if got == 'retry' and attempt == 1:
                time.sleep(3)
                continue
            if isinstance(got, dict):
                return got
            break
    return None


def _try(model, body, size):
    """→ {i: keep} on success, 'retry' when busy / timed out, None to move to the next model."""
    try:
        r = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY},  # header, never in the URL
            json=body, timeout=max(5, min(60, _deadline[0] - time.time())),
        )
    except requests.Timeout:
        print(f'[AI] {model}: timeout')
        return 'retry'
    except requests.RequestException as e:
        print(f'[AI] {model}: {type(e).__name__}')
        return 'retry'
    if r.status_code in (429, 500, 503):
        print(f'[AI] {model}: HTTP {r.status_code}')
        return 'retry'
    if r.status_code != 200:  # 404 = model retired, 400/403 = not allowed — next model
        print(f'[AI] {model}: HTTP {r.status_code}')
        return None
    try:
        parts = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [])
        text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
        out = json.loads(text)
        got = {int(x['i']): bool(x['keep']) for x in out if isinstance(x, dict) and 'i' in x and 'keep' in x}
    except (ValueError, KeyError, TypeError, IndexError) as e:
        print(f'[AI] {model}: bad answer ({type(e).__name__})')
        return None
    if len(got) >= size * 0.8:  # a mostly-complete answer; missing ones fall back to keywords
        return got
    print(f'[AI] {model}: incomplete answer ({len(got)}/{size})')
    return None


def classify(news_list, cache):
    """Adds {link: True/False} to cache for every item the AI judged. Returns how many it judged."""
    if not KEY:
        return 0
    _deadline[0] = time.time() + BUDGET
    todo = [n for n in news_list if n.get('link') and n['link'] not in cache]
    judged = 0
    for k in range(0, len(todo), BATCH):
        batch = todo[k:k + BATCH]
        res = _ask(batch)
        if res is None:
            break  # AI down: the rest use the keyword rules this run
        for i, n in enumerate(batch):
            if i in res:
                cache[n['link']] = res[i]
                judged += 1
    return judged


# ── Same-story check ─────────────────────────────────────────────────────────
# Portals rewrite one story in Nepali AND English with different words and number
# formats ("सुन तोलामा ३ हजार २ सय घट्यो" / "Gold price drops by Rs 3,200"); word
# rules can't see that, a model can. One call per run: new candidates vs what the
# channel already sent in the last DUP_HOURS.
DUP_HOURS = 36
DUP_MAX_SENT = 150

DUP_PROMPT = """You de-duplicate a Telegram news channel for NEPSE (Nepal stock market) investors.
SENT = stories already posted (with how many hours ago). NEW = stories about to be posted, in order.
For each NEW item decide dup=true if it reports the SAME news event/announcement as any SENT item
or any EARLIER NEW item — even if one is Nepali and the other English, worded differently, or numbers
are written differently (३ हजार २ सय = Rs 3,200; मंसिर ≈ December).
dup=false if it is a genuinely different event or a NEW update: e.g. today's gold price vs an earlier
day's, a different day's NEPSE close, the same company's dividend vs its AGM date, a new development
in an ongoing case. When unsure, dup=false.
Reply with JSON only: [{"i": <NEW index>, "dup": true|false}] covering every NEW index."""


def _find_dupes_listwise(candidates, sent_history, cache):
    """→ set of candidate links the AI says repeat an already-sent (or earlier) story.
    Empty set when no key / AI down — main.py's word rules still apply."""
    if not KEY or not candidates:
        return set()
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    recent = []
    for s in sent_history[-600:]:
        try:
            age = (now - datetime.datetime.fromisoformat(s.get('sent_at', ''))).total_seconds() / 3600
        except ValueError:
            continue
        if age < DUP_HOURS:
            recent.append((age, s.get('headline', '')))
    recent = recent[-DUP_MAX_SENT:]
    # Asked fresh every run (no cache): a dup gets written to sent history and never
    # comes back; a "not dup" must be re-checked against whatever was sent since.
    todo = candidates
    if todo:
        lines = ['SENT:'] + [f"S{k} ({a:.0f}h ago): {h}" for k, (a, h) in enumerate(recent)]
        lines += ['', 'NEW:'] + [f"{i}. [{n.get('source', '')}] {n['headline']}" for i, n in enumerate(todo)]
        body = {
            'systemInstruction': {'parts': [{'text': DUP_PROMPT}]},
            'contents': [{'role': 'user', 'parts': [{'text': '\n'.join(lines)}]}],
            'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'maxOutputTokens': 4096},
        }
        _deadline[0] = time.time() + 90
        got = None
        for model in MODELS:
            for attempt in (1, 2):
                if time.time() > _deadline[0]:
                    break
                r = _try_dup(model, body, len(todo))
                if r == 'retry' and attempt == 1:
                    time.sleep(3)
                    continue
                got = r if isinstance(r, dict) else None
                break
            if got is not None:
                break
        if got is None:
            print('[AI-DUP] unavailable — word rules only this run')
            return set()
        return {n['link'] for i, n in enumerate(todo) if got.get(i) is True}
    return set()


def _try_dup(model, body, size):
    try:
        r = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY},
            json=body, timeout=max(5, min(60, _deadline[0] - time.time())),
        )
    except requests.RequestException as e:
        print(f'[AI-DUP] {model}: {type(e).__name__}')
        return 'retry'
    if r.status_code in (429, 500, 503):
        print(f'[AI-DUP] {model}: HTTP {r.status_code}')
        return 'retry'
    if r.status_code != 200:
        print(f'[AI-DUP] {model}: HTTP {r.status_code}')
        return None
    try:
        parts = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [])
        out = json.loads(''.join(p.get('text', '') for p in parts if not p.get('thought')))
        got = {int(x['i']): bool(x['dup']) for x in out if isinstance(x, dict) and 'i' in x and 'dup' in x}
    except (ValueError, KeyError, TypeError, IndexError) as e:
        print(f'[AI-DUP] {model}: bad answer ({type(e).__name__})')
        return None
    return got if len(got) >= size * 0.8 else None


# ── Embedding shortlist + AI verdict (primary) ──────────────────────────────
# One long list of 150 headlines made the small model miss obvious repeats
# ("Government Blacklists 120 Firms" right after "सरकारले १२० फर्म कालोसूचीमा").
# Now: multilingual embeddings find each new story's 5 closest already-sent
# stories (Nepali/English land close together), then the model judges only those.
# Calibrated on real channel pairs: every true repeat scored ≥0.857; unrelated
# same-topic stories scored as low as 0.80 but also as high as 0.96 — so the
# embedding only SHORTLISTS, the model decides.
import base64, math, datetime as _dt

EMB_MODEL = 'models/gemini-embedding-001'
EMB_DIM = 256
EMB_FILE = 'emb_cache.json'
EMB_MIN = 0.80      # below this, never a candidate match
TOP_K = 5
EMB_PER_RUN = 30   # free tier ≈100 embeddings/min: backfill old headlines gradually

VERIFY_PROMPT = """You de-duplicate a Telegram news channel for NEPSE (Nepal stock market) investors.
Each NEW story comes with the most similar stories ALREADY POSTED (with hours ago).
dup=true if the NEW story reports the SAME news event/announcement as any listed one — even if one is
Nepali and the other English, worded differently, focusing on a different detail of the same report,
or with numbers written differently (३ हजार २ सय = Rs 3,200; २७ सय = 2,700; ३० खर्ब = Rs 30 trillion;
मंसिर ≈ December). Several outlets reporting today's NEPSE close / today's gold price / today's forex
rates = the same story.
dup=false if it is a different event or a NEW update: a different day's gold price or NEPSE close,
a weekly summary vs a daily report, the same company's dividend vs its AGM date, a different company,
a new development in an ongoing case. For market/price updates (NEPSE points, turnover, gold, forex),
it is the same story only if the key figures match (after converting formats) — different figures =
different update = dup=false. When unsure, dup=false.
Reply with JSON only: [{"i": <NEW index>, "dup": true|false}] covering every NEW index."""


def _pack(v):
    return base64.b64encode(bytes((max(-127, min(127, round(x * 127))) & 0xFF) for x in v)).decode()


def _unpack(s):
    return [(b - 256 if b > 127 else b) / 127 for b in base64.b64decode(s)]


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _embed(texts):
    """→ list of unit vectors, or None on failure."""
    out = []
    for k in range(0, len(texts), 50):
        body = {'requests': [{'model': EMB_MODEL, 'content': {'parts': [{'text': t}]},
                              'taskType': 'SEMANTIC_SIMILARITY', 'outputDimensionality': EMB_DIM}
                             for t in texts[k:k + 50]]}
        for attempt in (1, 2):
            try:
                r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/{EMB_MODEL}:batchEmbedContents',
                                  headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY},
                                  json=body, timeout=40)
                if r.status_code == 200:
                    out += [_norm(e['values']) for e in r.json()['embeddings']]
                    break
                print(f'[AI-DUP] embed HTTP {r.status_code}')
            except (requests.RequestException, ValueError, KeyError) as e:
                print(f'[AI-DUP] embed {type(e).__name__}')
            if attempt == 1:
                time.sleep(8)
        else:
            return None
    return out


def _load_emb():
    try:
        with open(EMB_FILE) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_emb(d, keep_links):
    with open(EMB_FILE, 'w') as f:
        json.dump({k: v for k, v in d.items() if k in keep_links}, f, separators=(',', ':'))


def _verify(items):
    """items: [(new_headline, [(hours_ago, headline), ...])] → {i: bool} or None."""
    lines = []
    for i, (h, ms) in enumerate(items):
        lines.append(f'NEW {i}: {h}')
        lines += [f'   - ({a:.0f}h ago) {mh}' for a, mh in ms]
    body = {
        'systemInstruction': {'parts': [{'text': VERIFY_PROMPT}]},
        'contents': [{'role': 'user', 'parts': [{'text': '\n'.join(lines)}]}],
        'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'maxOutputTokens': 4096},
    }
    _deadline[0] = time.time() + 90
    for model in MODELS:
        for attempt in (1, 2):
            if time.time() > _deadline[0]:
                return None
            r = _try_dup(model, body, len(items))
            if r == 'retry' and attempt == 1:
                time.sleep(3)
                continue
            if isinstance(r, dict):
                return r
            break
    return None


def find_dupes(candidates, sent_history, cache, hours=DUP_HOURS):
    """→ set of candidate links that repeat a story already sent (or an earlier candidate)."""
    if not KEY or not candidates:
        return set()
    now = _dt.datetime.now(_dt.timezone.utc)
    recent = []
    for s in sent_history[-800:]:
        try:
            age = (now - _dt.datetime.fromisoformat(s.get('sent_at', ''))).total_seconds() / 3600
        except ValueError:
            continue
        if age < hours and s.get('link') and s.get('headline'):
            recent.append((age, s))
    emb = _load_emb()
    missing_all = [s for _, s in recent if s['link'] not in emb]
    missing = missing_all[-EMB_PER_RUN:]          # newest first matter most
    backlog = len(missing_all) > len(missing)
    new_c = [n for n in candidates if n['link'] not in emb]   # candidates seen last run keep their vector
    texts = [s['headline'] for s in missing] + [n['headline'] for n in new_c]
    vecs = _embed(texts) if texts else []
    if vecs is None:
        print('[AI-DUP] embeddings unavailable — list check instead')
        return _find_dupes_listwise(candidates, sent_history, cache)
    for s, v in zip(missing + new_c, vecs):
        emb[s['link']] = _pack(v)
    cvecs = [_unpack(emb[n['link']]) for n in candidates]
    pool = [(a, s['headline'], _unpack(emb[s['link']])) for a, s in recent if s['link'] in emb]
    items, idx = [], []
    for n, v in zip(candidates, cvecs):
        sims = sorted(((sum(x * y for x, y in zip(v, pv)), a, h) for a, h, pv in pool), reverse=True)
        top = [(a, h) for sim, a, h in sims[:TOP_K] if sim >= EMB_MIN]
        if top:
            items.append((n['headline'], top))
            idx.append(n)
        pool.append((0.0, n['headline'], v))       # later candidates also compare against this one
    dupes = set()
    if items:
        got = _verify(items)
        if got is None:
            print('[AI-DUP] verifier unavailable — word rules only this run')
        else:
            dupes = {n['link'] for i, n in enumerate(idx) if got.get(i) is True}
    if backlog:  # some older sent headlines not embedded yet — also run the list check
        print(f'[AI-DUP] embedding backlog {len(missing_all) - len(missing)} — adding list check')
        dupes |= _find_dupes_listwise(candidates, sent_history, cache)
    _save_emb(emb, {s['link'] for _, s in recent} | {n['link'] for n in candidates})
    return dupes
