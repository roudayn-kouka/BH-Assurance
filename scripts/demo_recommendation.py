"""Run the company recommendation and pending-draft demo."""

from smoke_recommendation_api import EXPECTED_PRODUCT, check_recommendation_api
from smoke_recommendation_draft import check_recommendation_draft


def main():
    recommendation = check_recommendation_api()
    draft = check_recommendation_draft(recommendation, EXPECTED_PRODUCT)
    print(f"Selected product: {recommendation['profile']['candidate_produit']}")
    print(f"Draft status: {draft['statut']}")


if __name__ == "__main__":
    main()
