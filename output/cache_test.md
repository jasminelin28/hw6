# Cache Test: What Reusing the Handbook Is Worth

Model: `gpt-6-luna`. Documents: all 12 in `data/practice_docs/`. Every model call from both
setups is in `output/cache_test.json`. Script: `cache_test.py`.

## How each setup was built

**With cache.** The prompt prefix is byte-identical on every call: the same instructions,
the same handbook, in the same order. One warm-up call runs first so the prefix is already
in cache before the 12 measured documents start.

**Without cache.** A fresh random id is injected at the very front of the prompt on every
single model call, so the prefix the provider hashes is never one it has seen before:

```python
def instructions_arg() -> str:
    return "<!-- call id " + uuid.uuid4().hex + " -->\n" + static_instructions
```

This had to be *per model call*, not per document. My first attempt used one id per
document, and the no-cache arm still reported about 11,000 cached tokens per document,
because each run makes two model calls (one to decide to read the document, one to answer
after the tool returns) and the second call reused the first call's prefix. Only after
moving the id into a function that re-runs on every request did the cached count go to zero.

## Proof each setup did what I think

Token counts as reported by the API, summed over all 24 model calls per setup:

| Setup | Model calls | Input tokens | Cached input | Cache write | Output |
|---|---|---|---|---|---|
| Without cache | 24 | 271,800 | **0** | 268,776 | 1,473 |
| With cache | 24 | 271,247 | **265,203** | 3,020 | 1,472 |

The no-cache arm reports exactly **0** cached tokens across all 24 calls. The cached arm
reads about 97.8% of its input from cache (265,203 / 271,247).

## Cost

| Setup | Total, 12 docs | Per document | Per model call |
|---|---|---|---|
| Without cache | **$0.034637** | **$0.002886** | $0.001443 |
| With cache | **$0.004067** | **$0.000339** | $0.000169 |

**Saved: $0.030570 on 12 documents, or 88.26%.** Caching makes each document about 8.5x
cheaper.

Per-call averages, which show where the money goes:

| Setup | Call | Input | Cached | Cache write | Fresh input | Output | Cost |
|---|---|---|---|---|---|---|---|
| no cache | 1 | 11,220 | 0 | 11,094 | 126 | 44 | $0.001421 |
| no cache | 2 | 11,430 | 0 | 11,304 | 126 | 78 | $0.001465 |
| with cache | 1 | 11,196 | 11,030 | 40 | 126 | 44 | $0.000150 |
| with cache | 2 | 11,408 | 11,070 | 211 | 126 | 78 | $0.000189 |

## Real numbers vs the Problem 2 estimate

Problem 2 estimated the handbook at 10,058 tokens and **$0.001006** per uncached call.

What actually happens:

- The API reports about **11,100 to 11,400 input tokens per call**, against my 10,058
  estimate. The extra roughly 1,100 to 1,350 tokens are the things I did not count:
  `prompts/prompt.md`, the three tool schemas, the structured output schema, the user
  message, and on the second call the document text and the first call's tool message. The
  handbook estimate itself was close; the per-call total was the part I under-counted.
- **Each document costs two model calls, not one.** This is the big miss. Problem 2 priced
  one call per document; the tool-calling loop sends the whole handbook again on the second
  call. So a document is roughly double the estimate before anything else.
- Estimate for one document, uncached, scaled to two calls: 2 x $0.001006 = **$0.002012**.
  Measured: **$0.002886**, about 43% higher. The gap is the uncounted prompt overhead plus
  the cache-write premium described below.
- Cached: Problem 2 estimated $0.000101 per call. Measured, $0.000169 per call and
  $0.000339 per document, again close once you account for two calls and the extra prompt.

The direction of the estimate was right (caching is worth roughly 90%); the per-document
magnitude was about 40% low.

## Projection: 1,000 documents a day for 30 days

30,000 documents, at the measured per-document costs:

| Setup | Per document | 1 day (1,000 docs) | 30 days (30,000 docs) |
|---|---|---|---|
| Without cache | $0.002886 | $2.89 | **$86.59** |
| With cache | $0.000339 | $0.34 | **$10.17** |
| **Saved** | $0.002547 | $2.55 | **$76.42** |

At this volume caching is the difference between about $87 and about $10 a month. The
numbers are small because `gpt-6-luna` is cheap, but the ratio is what matters: the same
88% applies if the volume or the model price goes up 100x.

## What surprised me

**1. The no-cache arm is charged for cache writes it never reads.** With caching defeated,
the API still reported about 11,094 cache-write tokens per call, and cache writes cost
$0.125 per 1M, which is *more* than plain input at $0.10 per 1M. So defeating the cache
does not just lose me the discount, it moves most of my input tokens onto a 25% more
expensive line. Why it happens: the provider writes any sufficiently long prefix into cache
automatically, hoping for a future hit. Each of my unique prefixes was written once and then
never matched, because the next call had a different random id. That is the worst case: pay
the write premium, get none of the reads.

**2. The second model call is as expensive as the first.** I had pictured the handbook being
sent "on every call" as meaning once per document. It is sent once per *model request*, and
the tool-calling loop needs two. Half my bill is the model rereading the handbook so it can
answer a question it had already read the handbook to ask. This is the single biggest lever
left after caching.

**3. Cached reads are nearly free but not quite zero.** Even in the cached arm each call
still pays for about 126 fresh input tokens (the changing part: the document path, the tool
result) and 40 to 211 cache-write tokens, because the tail of the prompt that differs has
to be written each time. That residue is why the saving is 88% and not the 90% the raw
price ratio ($0.01 vs $0.10) suggests.

**4. Cache hits survived across separate processes.** Each document is a fresh
`python` process with a newly built agent, and the cache still hit. The cache lives on the
provider side and is keyed on the prompt prefix, not on my session, so I did not have to
keep anything alive locally to get the discount.
