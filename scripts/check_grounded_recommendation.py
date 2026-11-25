"""Verify that drafts can assert only product evidence supplied to the sales chain."""

import json
from pathlib import Path
import sys
from unittest import TestCase, main

from langchain_core.runnables import RunnableLambda

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from utils.grounded_recommendation import Evidence, grounded_recommendation

PRODUCT = "Synthetic Fleet Cover"
PAYLOAD = {
    "user_id": "REF_pm_STAGE_CHECK",
    "user_type": "personne_morale",
    "endpoint_key": "pm_recommendation",
    "endpoint_strategy": "product_recommendation",
    "profile": {"candidate_produit": PRODUCT},
}
FLEET = Evidence(
    id="fleet", product=PRODUCT, document="Fictional catalog", locator="1",
    supports=["fleet"], excerpt="Passage for declared delivery vans.", revision="test-1",
)
TERRITORY = FLEET.model_copy(update={
    "id": "territory", "supports": ["domestic"], "excerpt": "Passage for domestic use.",
})
OTHER = FLEET.model_copy(update={"id": "other", "product": "Other Product", "supports": ["domestic"]})


def no_inference(_prompt):
    raise AssertionError("The model should not run when the input lacks support")


class GroundedRecommendationTests(TestCase):
    def test_verified_source_ids_render_verbatim_with_provenance(self):
        def choose(prompt):
            self.assertIn(PRODUCT, prompt.to_string())
            return json.dumps({"source_ids": ["fleet", "territory"]})

        result = grounded_recommendation(PAYLOAD, ["fleet", "domestic"], [FLEET, TERRITORY], RunnableLambda(choose))
        self.assertEqual(result.outcome, "recommended")
        self.assertEqual(result.product, PRODUCT)
        self.assertEqual(result.sources, [FLEET, TERRITORY])
        for source in result.sources:
            self.assertIn(f"« {source.excerpt} » [{source.id}]", result.body)

    def test_unsupported_needs_and_ambiguous_input_abstain(self):
        for needs, sources, expected in (
            ([], [FLEET], "clarification_required"),
            (["fleet", "domestic"], [FLEET, OTHER], "insufficient_evidence"),
            (["fleet"], [], "insufficient_evidence"),
        ):
            with self.subTest(needs=needs, sources=sources):
                result = grounded_recommendation(PAYLOAD, needs, sources, RunnableLambda(no_inference))
                self.assertEqual(result.outcome, expected)
                self.assertIsNone(result.product)
                self.assertEqual(result.sources, [])
                self.assertNotIn(PRODUCT, result.body)

    def test_model_cannot_add_claims_or_drop_required_evidence(self):
        for response in (
            '{"source_ids": ["fleet", "missing"]}',
            '{"source_ids": ["fleet", "territory"], "claim": "Unlimited coverage"}',
            '{"source_ids": ["fleet", "territory", "fleet"]}',
            '{"source_ids": ["fleet"]}',
            "Unlimited coverage",
        ):
            with self.subTest(response=response):
                model = RunnableLambda(lambda _: response)
                result = grounded_recommendation(PAYLOAD, ["fleet", "domestic"], [FLEET, TERRITORY], model)
                self.assertEqual(result.outcome, "model_output_invalid")
                self.assertIsNone(result.product)
                self.assertEqual(result.sources, [])
                self.assertNotIn("Unlimited coverage", result.body)


if __name__ == "__main__":
    main(verbosity=2)
