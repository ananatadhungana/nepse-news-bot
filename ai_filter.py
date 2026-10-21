"""AI relevance gate — decides by the WHOLE story, not by blocked words.

Owner, 21 Oct 2026: "we shouldn't block words we need to block the news if not related —
if we keep blocking words it won't work". Each new headline (with its summary when there
is one) is judged once by a small model: would a NEPSE investor care about this news?
Decisions are remembered in ai_decisions.json, so a story is never asked about twice.
If GEMINI_API_KEY is missing or the AI fails, main.py falls back to the keyword rules.
"""
import json
import os

import requests

CACHE_FILE = 'ai_decisions.json'
CACHE_MAX = 5000
BATCH = 40
KEY = os.environ.get('GEMINI_API_KEY', '')
MODELS = [m for m in [os.environ.get('GEMINI_MODEL'), 'gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-2.5-flash'] if m]

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
        try:
            r = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY},  # header, never in the URL
                json=body, timeout=40,
            )
            if r.status_code != 200:
                print(f'[AI] {model}: HTTP {r.status_code}')
                continue
            parts = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [])
            text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
            out = json.loads(text)
            got = {int(x['i']): bool(x['keep']) for x in out if isinstance(x, dict) and 'i' in x and 'keep' in x}
            if len(got) >= len(batch) * 0.8:  # a mostly-complete answer; missing ones fall back to keywords
                return got
            print(f'[AI] {model}: incomplete answer ({len(got)}/{len(batch)})')
        except Exception as e:  # network, quota, bad JSON → try the next model
            print(f'[AI] {model}: {type(e).__name__}')
    return None


def classify(news_list, cache):
    """Adds {link: True/False} to cache for every item the AI judged. Returns how many it judged."""
    if not KEY:
        return 0
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
