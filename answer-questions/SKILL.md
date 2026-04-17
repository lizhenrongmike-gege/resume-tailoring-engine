---
name: answer_questions_v1
description: "Generates answers to free-text application questions captured by the jobcapture extension. Reads the candidate's tailored resume outputs (summary, JD, resume script, career ledger) and the relevant prompt strategy, then writes structured answers for auto-fill and a human-readable markdown record. Trigger phrases: '/answer-questions', 'answer application questions', 'fill my application questions'."
---

# Answer Application Questions

## When to use
Invoke this skill when the jobcapture extension has captured application questions and written `output/applications/{slug}_questions.json`. The skill reads that file, generates answers using the company's existing tailored resume context, and writes `output/applications/{slug}_answers.json` + `{slug}_answers.md`.

## Pre-flight

1. **Scan for pending questions files.** List `output/applications/*_questions.json` whose companion `*_answers.json` does not exist.
2. **If exactly one pending file exists**, select it automatically.
3. **If multiple**, ask the user which slug to answer.
4. **If none**, stop and tell the user to capture questions from the extension first.

## Context loading

For the chosen slug, read — in this order:

1. `output/applications/{slug}_questions.json` — what to answer
2. `output/summaries/{slug}.yaml` — the content decisions made during tailoring (fit score, keywords placed, brief summary)
3. `output/jds/{slug}.txt` — the original job description (if present; not all slugs have one)
4. `output/scripts/generate_{slug}_resume.js` — the actual bullets on the submitted resume
5. `career_ledger.yaml` — the full experience bank for depth beyond the resume
6. `prompts/answer_strategies/default.yaml` — generation rules (tone, structure, length)

If any file in 1–2 or 4 is missing, stop and report the missing file. Items 3 and 5 are nice-to-have — warn but continue.

## Generation rules (from the strategy)

Follow the loaded strategy verbatim. The default strategy specifies:

- **Tone:** Confident but not arrogant. First-person. No filler.
- **Structure:** Lead with the direct answer, then support with specific examples.
- **Source priority:** submitted resume → JD keywords → career ledger. Never fabricate metrics not in the ledger.
- **Mirror JD terminology.** Don't swap in generic synonyms.
- **Don't contradict the resume.** If the resume already covers it, expand.
- **Length:**
  - With a `char_limit`: stay under 90% of the limit.
  - With a `word_limit`: stay under 90% of the limit.
  - No limit + `short_text`: 2–3 sentences.
  - No limit + `long_text`: 3–4 paragraphs with concrete examples.

For each question, before writing the answer:
1. Identify which resume bullet (or ledger achievement) is the primary evidence.
2. Extract 2–3 JD keywords the answer should mirror.
3. Draft, then verify the length rule. Trim if over.

## Output

Write two files:

**`output/applications/{slug}_answers.json`** — structured, for auto-fill:

```json
{
  "company": "...",
  "generated_at": "<ISO-8601 UTC>",
  "strategy_used": "default",
  "answers": [
    {
      "id": "q1",
      "field_selector": "...",
      "question_text": "...",
      "answer": "...",
      "char_count": 1234,
      "word_count": 210,
      "within_limit": true
    }
  ]
}
```

Copy each question's `id`, `field_selector`, and `text` (into `question_text`) from the input file so auto-fill can match on either selector or label text. Compute `char_count` and `word_count` from the answer body. `within_limit` is `true` when the answer respects the applicable limit.

**`output/applications/{slug}_answers.md`** — human-readable record. Use this format:

```markdown
# {Company} — {Role} Application

## {Question text}

{Answer body, with markdown paragraphs/headings if helpful}

## {Next question text}

{Next answer}
```

Match the format of existing files in `output/applications/` (e.g., `glia_sales_engineer.md`).

## Completion

Report to the user:
- The slug answered
- How many questions were answered
- Any questions whose answers came close to the length limit (flag within 5%)
- The two output file paths

Remind the user to return to the browser and click **Fill Answers** in the extension.
