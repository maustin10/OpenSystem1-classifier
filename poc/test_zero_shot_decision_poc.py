"""Fast, model-free tests for the POC schema and typed-output contract."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zero_shot_decision_poc import (  # noqa: E402
    Comparison,
    InputValidationError,
    NliEvidence,
    _local_model_hint,
    _model_load_hint,
    evaluate,
    parse_request,
)


class FixedScorer:
    """Returns prearranged NLI values keyed by declared candidate ID."""

    def __init__(self, logits: dict[str, tuple[float, float]]) -> None:
        self.logits = logits
        self.comparisons: list[Comparison] = []

    def score(self, comparisons: list[Comparison]) -> list[NliEvidence]:
        self.comparisons = list(comparisons)
        return [
            NliEvidence(
                entailment_logit=self.logits[comparison.candidate_id][0],
                entailment_probability=self.logits[comparison.candidate_id][1],
            )
            for comparison in comparisons
        ]


def sample_payload() -> dict:
    return {
        "state": {"ticket_text": "I was charged twice and need help today."},
        "decisions": [
            {
                "id": "team",
                "kind": "choice",
                "question": "Which team owns this ticket?",
                "review_option_id": "review",
                "options": [
                    {"id": "billing", "description": "Duplicate charges and refunds."},
                    {"id": "technical", "description": "Outages and defects."},
                    {"id": "review", "description": "Insufficient evidence."},
                ],
            },
            {
                "id": "same_day",
                "kind": "boolean",
                "question": "Does this require same-day action?",
                "true_description": "Same-day action is required.",
                "minimum_probability": 0.80,
            },
            {
                "id": "urgency",
                "kind": "score",
                "question": "What urgency applies?",
                "levels": [
                    {"id": "routine", "value": 0, "description": "Two business days."},
                    {"id": "high", "value": 2, "description": "Same-day response."},
                    {"id": "critical", "value": 3, "description": "Escalate immediately."},
                ],
            },
        ],
    }


class ZeroShotDecisionPocTests(unittest.TestCase):
    def test_evaluate_builds_typed_results_from_one_flattened_batch(self) -> None:
        request = parse_request(sample_payload())
        scorer = FixedScorer(
            {
                "billing": (4.0, 0.98),
                "technical": (1.0, 0.20),
                "review": (-1.0, 0.05),
                "true": (3.0, 0.91),
                "routine": (-1.0, 0.05),
                "high": (2.0, 0.80),
                "critical": (0.5, 0.20),
            }
        )

        result = evaluate(request, scorer)

        self.assertEqual(len(scorer.comparisons), 7)
        self.assertEqual(result["result_count"], 3)

        choice, boolean, score = result["results"]
        self.assertEqual(choice["answer"], "billing")
        self.assertEqual(choice["recommended_option"], "billing")
        self.assertFalse(choice["review_required"])
        self.assertAlmostEqual(sum(choice["probabilities"].values()), 1.0, places=5)

        self.assertTrue(boolean["answer"])
        self.assertEqual(boolean["probability_true"], 0.91)
        self.assertFalse(boolean["review_required"])

        self.assertEqual(score["dominant_level"], "high")
        self.assertGreater(score["value"], 1.0)
        self.assertLess(score["value"], 3.0)

    def test_choice_routes_to_designated_review_option_when_ambiguous(self) -> None:
        payload = sample_payload()
        payload["decisions"] = payload["decisions"][:1]
        request = parse_request(payload)
        scorer = FixedScorer(
            {
                "billing": (1.00, 0.5),
                "technical": (0.95, 0.5),
                "review": (-1.0, 0.1),
            }
        )

        result = evaluate(request, scorer)["results"][0]

        self.assertEqual(result["recommended_option"], "billing")
        self.assertEqual(result["answer"], "review")
        self.assertTrue(result["review_required"])
        self.assertIn("margin", result["review_reason"])

    def test_parser_rejects_duplicate_option_ids(self) -> None:
        payload = sample_payload()
        payload["decisions"][0]["options"][1]["id"] = "billing"

        with self.assertRaisesRegex(InputValidationError, "duplicate candidate IDs"):
            parse_request(payload)

    def test_parser_rejects_score_without_numeric_level_value(self) -> None:
        payload = sample_payload()
        del payload["decisions"][2]["levels"][0]["value"]

        with self.assertRaisesRegex(InputValidationError, "numeric 'value'"):
            parse_request(payload)


class ModelLoadHintTests(unittest.TestCase):
    """A misdiagnosed model-load failure costs real debugging time.

    Hugging Face reports a proxy block page as "couldn't connect ... check your
    internet connection", which sends the reader after a network fault that does
    not exist. The distinguishing signal (a missing 'X-Repo-Commit' header) is
    buried in the exception's __cause__ chain, not in str(error).
    """

    def _blocked_error(self) -> OSError:
        """Reproduce the real exception chain raised behind a filtering proxy."""
        root = OSError(
            "Response from https://huggingface.co/m/resolve/main/config.json is "
            "missing the 'X-Repo-Commit' header, so it does not seem to be served "
            "by a Hugging Face Hub endpoint."
        )
        outer = OSError(
            "We couldn't connect to 'https://huggingface.co' to load the files, "
            "and couldn't find them in the cached files."
        )
        outer.__cause__ = root
        return outer

    def test_block_page_is_reported_as_a_proxy_block_not_a_network_fault(self) -> None:
        hint = _model_load_hint("some/model", self._blocked_error())

        self.assertIn("block", hint.lower())
        self.assertIn("CSO proxy", hint)
        # Must offer a concrete way forward, not just describe the failure.
        self.assertIn("HF_HUB_OFFLINE=1", hint)
        self.assertIn("--model /path/to/local/model-dir", hint)
        self.assertIn("some/model", hint)
        # Must NOT push the reader toward a TLS fix -- that is a different cause.
        self.assertNotIn("SSL_CERT_FILE", hint)

    def test_signature_is_detected_even_when_nested_deeper_in_the_chain(self) -> None:
        """__context__ must be followed too, not only __cause__."""
        root = OSError("... missing the 'X-Repo-Commit' header ...")
        middle = OSError("wrapped failure")
        middle.__context__ = root
        outer = OSError("We couldn't connect to 'https://huggingface.co'")
        outer.__cause__ = middle

        self.assertIn("CSO proxy", _model_load_hint("m", outer))

    def test_generic_failure_suggests_the_tls_bundle_instead(self) -> None:
        hint = _model_load_hint("some/model", OSError("certificate verify failed"))

        self.assertIn("SSL_CERT_FILE", hint)
        self.assertNotIn("CSO proxy", hint)

    def test_hint_terminates_on_a_self_referential_cause_chain(self) -> None:
        """A cyclic chain must not hang the error path."""
        error = OSError("boom")
        error.__cause__ = error

        self.assertIn("Could not load model", _model_load_hint("m", error))


class LocalModelHintTests(unittest.TestCase):
    """An incomplete model copy must be named as such.

    Archiving a Hugging Face cache without dereferencing symlinks (`tar cz`
    instead of `tar czh`) yields a tree where config/tokenizer are real files but
    the weights are dangling links. transformers reports only "no file named
    model.safetensors", which reads like a wrong --model path rather than a
    truncated transfer, so the real cause has to be surfaced explicitly.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.model_dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_dangling_weight_symlink_is_reported_as_an_incomplete_copy(self) -> None:
        (self.model_dir / "config.json").write_text("{}")
        (self.model_dir / "model.safetensors").symlink_to(
            "../../blobs/9e88e3ba0721cee770645d262f10dbe8125ed592"
        )

        hint = _local_model_hint(self.model_dir)

        assert hint is not None
        self.assertIn("DANGLING SYMLINK", hint)
        self.assertIn("tar czhf", hint)
        # The broken target is the evidence -- it must be shown, not summarised.
        self.assertIn("9e88e3ba0721", hint)

    def test_directory_without_weights_lists_what_is_actually_there(self) -> None:
        (self.model_dir / "config.json").write_text("{}")
        (self.model_dir / "tokenizer.json").write_text("{}")

        hint = _local_model_hint(self.model_dir)

        assert hint is not None
        self.assertIn("No model weights found", hint)
        self.assertIn("config.json", hint)
        self.assertIn("snapshots/<commit-sha>", hint)

    def test_complete_directory_produces_no_hint(self) -> None:
        """A real weight file means the failure is something else entirely."""
        (self.model_dir / "config.json").write_text("{}")
        (self.model_dir / "model.safetensors").write_bytes(b"\x00" * 16)

        self.assertIsNone(_local_model_hint(self.model_dir))

    def test_missing_directory_produces_no_hint(self) -> None:
        """A plain repo id is not a local path; defer to the network hint."""
        self.assertIsNone(_local_model_hint(Path("MoritzLaurer/does-not-exist")))

    def test_model_load_hint_prefers_the_local_diagnosis(self) -> None:
        """A broken local copy outranks any network advice."""
        (self.model_dir / "model.safetensors").symlink_to("../../blobs/deadbeef")

        hint = _model_load_hint(
            str(self.model_dir),
            OSError("We couldn't connect to 'https://huggingface.co'"),
        )

        self.assertIn("DANGLING SYMLINK", hint)
        self.assertNotIn("CSO proxy", hint)


if __name__ == "__main__":
    unittest.main()
