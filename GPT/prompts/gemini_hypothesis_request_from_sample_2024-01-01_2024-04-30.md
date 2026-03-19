# Gemini Hypothesis Request From Sample

## Goal

Using only the uploaded sample package from the discovery period `2024-01-01` to `2024-04-30`, generate a small set of zero-base BOAT RACE betting hypotheses.

This is not a request to optimize an already known human strategy. This is a fresh hypothesis-generation step from scratch.

## Files You Have

- `races_sample.csv`
- `entries_sample.csv`
- `data_dictionary.md`

## Important Rules

- Do not refer to any existing human-created strategy, known ROI summary, or past adopted logic.
- Use only the uploaded sample data and dictionary.
- Do not assume access to any unseen future period.
- Favor simple, testable, mechanical conditions over complicated narratives.
- Conditions must later be implementable in SQL or Python without ambiguity.
- If a condition depends on a nullable field, include a null-safety assumption.
- Do not rely on racer names or one-off anecdotes.

## What I Want

Please produce `5` zero-base candidate hypotheses.

These are not final strategies yet. They are candidate structures for later backtesting.

## Preferred Style

- Prefer hypotheses driven by relative relationships inside a race.
- Prefer conditions based on combinations such as:
  - wind or wave context
  - lane structure
  - exhibition rank or exhibition gap
  - lane-1 strength or weakness
  - class composition of the race
  - local vs non-local context
  - start-shape imbalance such as `st_diff_from_inside`
- Avoid overly narrow conditions that are likely to be tiny-sample artifacts.

## Output Format

For each hypothesis, use exactly this structure:

```markdown
### Hypothesis ID: [H-001]

**Target Ticket Type:** [example: exacta / trifecta]

**Ticket Pattern:** [example: 1-3 or 2-1,3-1 or 1-2-3,1-3-2]

**Condition Block:**
- [condition 1]
- [condition 2]
- [condition 3]

**Expected Mechanism:**
[short explanation]

**Minimum Sample Guardrail:**
[what minimum sample would you want before trusting this]

**Why It Might Generalize:**
[short explanation]

**Complexity Check:**
[state whether this is low / medium / high complexity]
```

## Additional Constraints

- At least `3` of the `5` hypotheses should be low-to-medium complexity.
- At least `2` of the `5` hypotheses should target `2連単`-style ideas or exacta-style structures rather than only wide trifecta shapes.
- If you propose a trifecta idea, keep the ticket pattern reasonably compact.
- If two ideas are too similar, merge them instead of repeating.

## Final Section

After the 5 hypotheses, add one short section:

```markdown
## Screening Note
```

In that section, briefly say:

- which 2 hypotheses seem most robust
- which 1 hypothesis looks most likely to be overfit
- what extra aggregated file would help you improve the next round, if any

