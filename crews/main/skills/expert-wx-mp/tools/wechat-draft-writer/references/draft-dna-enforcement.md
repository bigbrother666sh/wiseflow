# Draft DNA Enforcement

## Required Inputs

- Confirmed outline and article objective.
- Reference materials.
- `dna/wx_mp/<dna-id>.md` instruction.
- `dna/wx_mp/<dna-id>.evaluation.md` evaluation plan.

## Before Writing

- Execute every item in the DNA instruction.
- Translate the 14 dimensions into the concrete opening, sections, argument flow, ending, and title behavior.
- Respect signature expressions by their usage conditions; do not stuff every high-frequency term into one article.

## After Writing

For a statistical DNA, run:

```bash
wechat-style-profiler evaluate \
  --metrics dna/wx_mp/<dna-id>.metrics.json \
  --article output_articles/<article>/article.md \
  --output output_articles/<article>/dna-evaluation.json
```

For a hand-written DNA, calculate the evaluation table and cite evidence.

## Delivery Gate

- Overall score must be at least 80.
- Any dimension marked as critical in the evaluation plan must not be 0.
- Revise and recalculate after changes.
- DNA evaluation does not replace fact checking, compliance review, or content-calibrator scoring.

## Not a Global Banned-Word System

The draft writer does not impose overseas-platform English banned-word rules. Language risk is handled by platform-specific publishing review. If the DNA instruction contains account-specific anti-patterns, follow those anti-patterns.
