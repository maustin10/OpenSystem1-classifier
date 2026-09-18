# Proposed LinkedIn post

I have been exploring a simple question: can we build useful AI routing systems without asking a generative model to produce the answer?

I compared two zero-shot classifiers on the same 12 multiple-choice decisions:

- A local ModernBERT NLI model
- TypeSafe System One using Jev 1.13.0

Both selected the expected answer on all 12 questions. But that was an intentionally easy plumbing test, so I moved to a harder Stage-1 tool-routing benchmark derived from the Berkeley Function Calling Leaderboard (BFCL).

The new set has 30 cases:

- 20 requests that require choosing one tool from multiple schemas
- 10 cases where no supplied tool should be called

Results:

- ModernBERT: 23/30 overall, including 17/20 tool selections and 6/10 no-tool decisions
- TypeSafe: 29/30 overall, including 20/20 tool selections and 9/10 no-tool decisions

The difference appeared when I applied the same decision gate: top probability of at least 0.65 and a top-two margin of at least 0.15.

On the original easy set, ModernBERT cleared 5 of 12 decisions and TypeSafe cleared all 12. On the harder routing set, the same gate cleared 0 of 30 ModernBERT routes and all 30 TypeSafe routes.

One important caveat: TypeSafe's one wrong route also cleared the gate. On this harder set, 25 of 30 responses were exact 1.0 / 0.0 distributions, while five had softer probabilities. Those values came directly from the API, not from client-side thresholding. Confidence controls abstention; it does not guarantee correctness.

The architecture is deliberately constrained. The system evaluates only the options supplied by the application. It cannot invent a category, and it routes weak evidence to review.

I have packaged the BFCL-derived data, reproducible benchmark code, raw API responses, installation instructions, and editable comparison deck in the OpenSystem1-classifier repository.

This is deliberately a routing benchmark, not an official BFCL score. The next stage is a deterministic, schema-aware argument extractor; only then does BFCL AST and executable evaluation become meaningful.

#ZeroShotClassification #MachineLearning #NaturalLanguageInference #ResponsibleAI #ModernBERT #MLOps
