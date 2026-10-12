# Handbook Token and Cost Estimate

Model: `gpt-6-luna`. Prices from `data/prices.json` (USD per 1M tokens):

| Price type | $ / 1M tokens |
|---|---|
| input (uncached) | 0.10 |
| cached input | 0.01 |
| cache write | 0.125 |
| output | 0.50 |

## 1. Token count

**`data/shop_handbook.md` = 10,058 tokens.**

How I got it: I tokenized the raw file with the `tiktoken` library using the
`o200k_base` encoding, which is the encoding used by the current GPT model family,
and took the length of the token list:

```python
import tiktoken, pathlib
text = pathlib.Path("data/shop_handbook.md").read_text(encoding="utf-8")
enc = tiktoken.get_encoding("o200k_base")
n_tokens = len(enc.encode(text))   # 10058
```

Supporting size figures: 28,903 characters and 6,127 whitespace-separated words.
The ratio of 28,903 / 10,058 = about 2.9 characters per token, which is the normal
range for English prose, so the count looks reasonable.

This is the handbook text only. A real call also carries the system instructions,
the vendor document, and the model's reply, so the true per-call input is higher.

## 2. Cost of the handbook alone

Cost formula: `cost = (tokens / 1,000,000) x price_per_1M`.

### Without caching (handbook re-sent as fresh input every call)

- One call: (10,058 / 1,000,000) x $0.10 = **$0.0010058**, about one tenth of a cent.
- 1,000 calls: $0.0010058 x 1,000 = **$1.0058**.

### With caching (handbook written to cache once, then read from cache)

- Cache write, charged once: (10,058 / 1,000,000) x $0.125 = **$0.00125725**.
- One cached read: (10,058 / 1,000,000) x $0.01 = **$0.00010058**, about one hundredth of a cent.
- 1,000 calls, all reading a cache that already exists:
  $0.00010058 x 1,000 = **$0.10058**.
- 1,000 calls counted realistically, 1 cache write plus 999 cached reads:
  $0.00125725 + ($0.00010058 x 999) = **$0.1017**.

### Side by side

| Scenario | 1 call | 1,000 calls |
|---|---|---|
| No caching | $0.001006 | $1.0058 |
| Cached reads only | $0.000101 | $0.1006 |
| 1 cache write + 999 cached reads | $0.001257 (the write) | $0.1017 |

**Takeaway:** caching the handbook cuts its cost by about 90%, roughly $1.01 down to
$0.10 per 1,000 calls. The cache write costs about 1.25x a normal input send, so the
write pays for itself as soon as the second call reuses it.

These are estimates. Problem 4 checks them against the token counts reported by real runs.
