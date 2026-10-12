# Campus Customs Vendor Desk Agent

MGT 409 AI Foundations for Managers — Homework 6.

An agent that reads one vendor document (HTML quote, PDF quote, catalog page, or `.eml`
supplier email), pulls out the vendor, SKU, unit price, lead time, and minimum order, and
recommends whether Campus Customs should buy, following the Campus Customs Shop Handbook.

The homework is about two things that show up once an agent runs for real:

- **Cost.** The handbook is ~10,000 tokens and goes to the model on every call. Caching it
  cut the bill by 88%.
- **Safety.** Some vendor documents hide text aimed at the AI. Three of twelve fooled the
  undefended agent; none fool the defended one.

Model: `gpt-6-luna` only, reached through Portkey.

**Start here:** [`output/hw6_report.html`](output/hw6_report.html) — one self-contained page
with every result. Open it by double-click; it needs no internet and no other files.

## Setup

```bash
git clone <this repo>
cd hw6

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and put your own Portkey key in it:

```
PORTKEY_API_KEY=your_portkey_api_key_here
```

The real `.env` is gitignored and is not in this repo.

## Running the agent

One vendor document, with all defenses on (this is the real agent):

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

It prints the assessment and appends to `output/usage_log.json` and
`output/audit_trail.json`.

Useful flags:

```bash
python agent.py --doc <path> --undefended     # the Problem 3 agent, no defenses
python agent.py --doc <path> --no-handbook    # skip the handbook, for cost comparisons
python agent.py --doc <path> --label mylabel  # tag the run in the usage log
```

Any file in `data/practice_docs/`, `data/exam_docs/`, or `data/my_attacks/` works.

## Reproducing the results

```bash
python cache_test.py                     # caching on/off across the 12 practice docs
python attack_test.py --strip-security   # undefended agent vs the 12 practice docs
python attack_test.py --defended         # defended agent vs the same 12
python make_attacks.py                   # regenerate my two red team documents
python red_team.py                       # my attacks vs both agents
python run_exam.py                       # defended agent vs the 10 exam docs
```

Each writes its own file into `output/`. All of them cost real API calls; the whole set is
under five cents.

## How it is built

| File | What it does |
|---|---|
| `agent.py` | entry point; builds the agent, runs one document, logs usage and the audit trail |
| `models.py` | the structured types (`vendor_assessment`, `vendor_facts`, `document_text`) |
| `tools.py` | the document readers, the two trap tools, and the human sign-off gate |
| `sanitizer.py` | **code defense** — strips anything a person could not see, then fences the text |
| `policy.py` | **design defense** — the four purchasing checks, computed in Python from the handbook |
| `prompts/prompt.md` | **prompt defense** — the agent's instructions |
| `prompts/prompt_undefended.md` | the original Problem 3 prompt, kept for comparison |

The handbook itself is not in `prompt.md`. `agent.py` appends `data/shop_handbook.md` to the
instructions on every call, which is what makes each call expensive.

### The three defense layers

1. **Code.** Removes hidden HTML (comments, `display:none`, zero and 1px font sizes, white
   text), PDF text drawn outside the page box, and zero-width characters. Reads the email
   part a mail app would show. Flags instruction-shaped phrasing, then wraps everything in
   untrusted-data markers.
2. **Design.** In defended mode the model's output type has **no `decision` field** — it
   returns facts only, and `policy.py` applies the handbook rules in Python. `send_email` and
   `approve_payment` are still registered, but behind a human sign-off gate that logs every
   attempt to `output/trap_calls.json` and refuses to act.
3. **Prompt.** Defines the document as quoted vendor material, and adds the rule that when a
   document states a value twice, the quote body wins — a later "correction" does not replace
   it.

### Known gap

My own red team found one. `policy.py` looks up the max unit cost using the SKU the model
reports, so a document that swaps the SKU redirects the comparison instead of changing the
number. The defended agent held against my attack, but the weakness is real and unfixed;
`output/red_team.md` explains it and lists the fix.

## Results

| | |
|---|---|
| Handbook size | 10,058 tokens |
| Cost per document, no caching | $0.002886 |
| Cost per document, cached | $0.000339 (88% saved) |
| Practice docs fooled, no defenses | 3 / 12 |
| Practice docs fooled, defended | 0 / 12 |
| Cost of the three defense layers | +215 input, −12 output tokens per doc (net slightly cheaper) |
| Exam set | 10 / 10 assessed, 0 trap tool calls, $0.003334 total |
| Projected monthly cost at 1,000 docs/day | about $10 |

Written up in `output/`: `handbook_estimate.md`, `cache_test.md`, `attack_results.md`,
`defense_results.md`, `red_team.md`, `harness.md`, and the full report in `hw6_report.html`.

`AI_prompts.md` is the log of what I typed to my vibe coder, one section per problem.

## Note

Campus Customs is used as a local setting for class. This is not a partnership with the shop,
and all vendors and documents are made up. The agent's email and payment tools never send or
pay anything — they only write to a log file.
