# Proposed LinkedIn post

I have been exploring a simple question: can we build useful AI decision systems without asking a generative model to produce the answer?

I compared two zero-shot classifiers on the same 12 multiple-choice decisions:

- A local ModernBERT NLI model
- TypeSafe System One using Jev 1.13.0

Both selected the expected answer on all 12 questions.

The difference appeared when I applied the same decision gate: top probability of at least 0.65 and a top-two margin of at least 0.15.

ModernBERT cleared 5 of 12 decisions. TypeSafe cleared all 12.

One important caveat: TypeSafe returned exact 1.0 / 0.0 probability distributions for this intentionally easy benchmark. That came directly from the API, not from client-side thresholding. It is a strong result on these questions, but it does not prove calibration on ambiguous or production data.

The architecture is deliberately constrained. The system evaluates only the options supplied by the application. It cannot invent a category, and it routes weak evidence to review.

I have packaged the code, raw results, installation instructions, and editable comparison deck in the OpenSystem1-classifier repository.

Next, I plan to add harder domain examples and compare DeBERTa, BART-MNLI, multilingual mDeBERTa, and GLiClass on accuracy, calibration, latency, and cost.

#ZeroShotClassification #MachineLearning #NaturalLanguageInference #ResponsibleAI #ModernBERT #MLOps

