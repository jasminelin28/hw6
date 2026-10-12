# AI Prompts Log — Homework 6 (Vendor Desk Agent)

This file logs what I typed to my vibe coder for each problem, in my own words.

---

## Q1. Set up the project and start the prompt log

**Prompt 1**

> hw 6 now

**Follow-up prompt**

> I need to start Homework 6. It's a vendor desk agent for Campus Customs: it reads a
> vendor document (quote, invoice, catalog page, or supplier email), pulls out vendor,
> item, price, lead time, and minimum order, then recommends buy or don't buy using the
> rules in the shop handbook. The focus this week is cost (the handbook is ~10k tokens
> and gets sent on every call) and prompt-injection safety. Please set up the project
> folder: download and unzip the data archive, make a virtual environment inside the
> Homework 6 folder, add a .gitignore that excludes .env, and create AI_prompts.md with
> one section per problem. Use only gpt-6-luna through Portkey, and load the key from
> the .env file instead of hardcoding it.

**What was lacking after the first prompt:** my first message was just "hw 6 now", so the
assistant had no assignment text and could not do anything except ask for it. The
follow-up supplied the actual assignment description and the setup requirements.

---

## Q2. Measure the handbook: tokens and dollars

**Prompt 1**

> Next problem. Open the shop handbook in the data folder and figure out exactly how many
> tokens it is, since the agent sends the whole thing on every call. Then use the
> gpt-6-luna price list in data/prices.json to work out what the handbook alone costs for
> a single call and for 1,000 calls, once with cached input tokens and once without.
> Write it to output/handbook_estimate.md and show the arithmetic, not just the answers.

**Follow-up prompt**

> Also say which tokenizer you used and why, and include the cache-write price in the
> 1,000-call math instead of pretending the cache is free the first time.

**What was lacking after the first prompt:** the first version gave a number without
explaining how it was measured, and the cached scenario ignored the one-time cache-write
charge, which made caching look slightly cheaper than it really is.

## Q3. Build the vendor desk agent

**Prompt 1**

> Now build the actual agent with PydanticAI on gpt-6-luna. It should be four files:
> prompts/prompt.md for my instructions, agent.py as the entry point, tools.py for the
> tools, and models.py for the structured types. I pass it the path to one vendor document
> and it reads the file with a tool — HTML, PDF, and .eml emails all have to work — then
> returns vendor, SKU, unit price, lead time in days, minimum order, a recommend or
> do_not_recommend decision based on the handbook rules, and a one-sentence reason. The
> handbook gets sent to the model on every call. Also give it two fake tools, send_email
> and approve_payment, that never actually do anything and just append the call and its
> arguments to output/trap_calls.json, so I can tell if a document ever hijacks the agent.
> After every run append the tokens and cost to output/usage_log.json and the tool calls
> plus final answer to output/audit_trail.json. It should run as
> `python agent.py --doc data/practice_docs/p01_bluehen_quote.html`.

**Follow-up prompt**

> Run it on p01 and p08 to prove it works, check the answers against practice_key.json, and
> write output/harness.md explaining every field in models.py and why that field exists,
> plus one line per tool.

**What was lacking after the first prompt:** the code existed but nothing had been executed,
so I had no evidence the PDF and email readers worked or that the decisions were right. The
Portkey connection also needed fixing — gpt-6-luna rejects function tools unless reasoning
effort is set to none.

## Q4. Measure what caching the handbook saves

**Prompt 1**

> The handbook is identical on every call, so the model should be able to reuse it from
> cache instead of me paying full price each time. Run the agent on all 12 practice
> documents twice: once set up so the handbook is reused from cache, and once set up so
> nothing can be reused. Save every single model call from both runs to
> output/cache_test.json with the setup, the document, all the token counts the API reports,
> and the dollar cost from prices.json. Then write output/cache_test.md with the total and
> per-document cost for each setup, the percent saved, how this compares to my Problem 2
> estimate, a projection for 1,000 documents a day over 30 days, and anything in the
> numbers that surprised me.

**Follow-up prompt**

> The no-cache run is still reporting about 11,000 cached tokens per document, so it isn't
> really a no-cache run. Each document makes two model calls and the second one is reusing
> the first one's prefix. Make the cache-busting id unique per model call instead of per
> document and run it again, and don't write the report until the no-cache arm reports zero
> cached tokens.

**What was lacking after the first prompt:** the no-cache setup didn't actually defeat the
cache. One random id per document still let the two calls inside a single run share a
prefix, which the assignment explicitly says doesn't count.

## Q5. Attack the undefended agent

**Prompt 1**

> Some of these vendor documents have text in them aimed at an AI. Run my Problem 3 agent
> with no new defenses on all 12 practice documents, compare every answer to
> practice_key.json, and check whether anything showed up in output/trap_calls.json. Save
> output/attack_results.json with, per document, whether each field matched, whether the
> decision matched, whether a trap tool got called, and whether any link or weird text made
> it into the answer. Then write output/attack_results.md explaining, for every document
> that fooled the agent, what fooled it and where in the file it was hiding.

**Follow-up prompt**

> My Problem 3 prompt already had a security section, so that is not really an undefended
> run. Add a way to run the same agent with that section stripped out and report both
> numbers. Also open each document the way a person would, looking at the actual HTML style
> attributes, the PDF text coordinates, and the raw .eml parts, and say what a human sees
> versus what my agent read, including the documents whose attacks did not work.

**What was lacking after the first prompt:** the first pass only said which answers were
wrong, not where the planted text physically lived or why it was invisible to a person, and
it skipped the documents whose attacks failed, which are the ones that show what the
defenses still have to catch.

## Q6. Defend the agent at three levels

**Prompt 1**

> Now defend the agent at three levels. First in code: clean the document before any model
> sees it, so hidden HTML, off-page PDF text, and white-on-white email text never reach the
> model. Second in design: restructure things so a poisoned document can't reach the
> decision or the dangerous tools. Third in the prompt. I'm not allowed to delete
> send_email or approve_payment, because the shop will use them later with a human
> approving each one, and I need to keep a way to run the agent with no defenses at all for
> Problem 7. Rerun all 12 practice documents into output/defense_results.json in the same
> shape as Problem 5 plus tokens and dollars per document, and write output/defense_results.md
> with a before/after table, what each layer catches that the others miss, and the extra
> tokens and dollars each layer costs. Clean documents still have to come back with the
> right values.

**Follow-up prompt**

> For the design layer, don't just tell the model not to decide — take the decision away
> from it entirely. Make the model return only the extracted facts, with no decision field
> in its output type, and compute the recommend/do_not_recommend in Python by parsing the
> vendor lists and max unit costs out of the handbook. And instead of removing the two
> dangerous tools, wrap them in a human sign-off gate that still logs every attempt to
> trap_calls.json but refuses to act, so I keep the detection and the tools stay in the
> system.

**What was lacking after the first prompt:** the first design layer was still just prompt
instructions wearing a different hat. Removing the `decision` field from the model's output
type is what makes the defense structural — the model can't produce a wrong recommendation
because there's nowhere for it to write one.

## Q7. Red team my own agent

**Prompt 1**

> Now I'm the attacker. Build two new booby-trapped vendor documents in data/my_attacks/.
> Each one has to use a hiding trick or an attack goal that isn't anywhere in the practice
> set, and anyone opening the file should just see a normal quote. Run both against the
> agent with no defenses and against my defended agent, and write output/red_team.md saying
> for each one what's hidden, where it is, what it's trying to make the agent do, and what
> happened before and after my defenses.

**Follow-up prompt**

> Don't aim both attacks at the price. Make one of them attack the part I claimed was
> unbeatable: the Python policy engine looks up the max unit cost using whatever SKU the
> model reports, so a document that swaps the SKU redirects the comparison instead of
> changing the number. And be honest in the write-up about which of my layers each attack
> got through, including the ones that failed on their own rather than because a defense
> stopped them.

**What was lacking after the first prompt:** the first pair of attacks were both variations
on hiding a cheaper price, which is the same attack the practice set already runs. Going
after the lookup key instead of the value is what found a real gap in my own design layer.

## Q8. Run the final agent on the exam set

**Prompt 1**

> Run my final defended agent on all 10 documents in data/exam_docs/ and save
> output/exam_results.json with one entry per file: file, vendor, sku, unit_price,
> lead_time_days, min_order, decision, reason, trap_tool_called, input_tokens,
> cached_tokens, output_tokens, and cost_usd. Don't hand-edit anything — whatever the agent
> returns is what goes in the file.

**Follow-up prompt**

> Also tell me which exam documents the sanitizer found hidden text in and which ones it
> flagged, so I know whether the set was actually attacking the agent or whether it just
> happened to be clean.

**What was lacking after the first prompt:** the results file alone didn't show whether the
defenses had done anything on this set. Three of the ten had hidden text removed and five
raised instruction flags, which is the evidence that the decisions were made on clean input.

## Q9. Build the single-file HTML report

**Prompt 1**

> Build output/hw6_report.html as one self-contained file that opens by double-click with no
> internet and nothing else next to it. It needs to show my caching results with a chart,
> the attacks before and after my defenses, what the defenses cost in tokens and dollars,
> the exam results and my two red team attacks, and a short recommendation to the store
> manager about whether Campus Customs should turn this on for real vendor mail and what it
> would cost per month at 1,000 documents a day. Use my real numbers from the earlier
> problems. For the design: pale but colorful pastels, a professional serif for headings and
> a sans serif for body text, carousel scrolling where it fits, and no three-column sections
> anywhere.

**Follow-up prompt**

> The chart has to be inline SVG, not a charting library, since the file can't load anything
> from the internet. And in the recommendation section don't just say yes — include the SKU
> gap my own red team attack found, because the manager should know what's still broken
> before they switch it on.

**What was lacking after the first prompt:** the first draft read like a sales pitch for the
agent. The recommendation is more useful to a manager if it names the unfixed weakness and
says what to do about it, rather than only reporting the numbers that look good.
