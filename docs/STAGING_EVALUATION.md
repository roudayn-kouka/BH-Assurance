# Wave 3 recommendation evaluation

Use [the synthetic opportunity cases](../scripts/fixtures/wave3-opportunities.json) and the [fictional catalog](../scripts/fixtures/wave3-catalog.json). The catalog extends Synthetic Fleet Cover from the earlier smoke fixture with fictional office and cargo products. The product descriptions are only for evaluating the pilot. The case file contains the explicit opportunity needs and expected results.

| Cases | Count | Expected result |
| --- | ---: | --- |
| CLEAR-01 through CLEAR-08 | 8 | Propose the API candidate with source excerpts addressing every stated need. |
| AMBIG-01 through AMBIG-08 | 8 | Ask to clarify the need without proposing a product. |
| NOFIT-01 through NOFIT-08 | 8 | Display insufficient documentation with no product or coverage claim. |

Chroma retrieval uses the API product candidate and the case context. The recommendation code checks that the returned sources for that product cover all required needs. Gemma selects source IDs through the LangChain recommendation scenario. The draft quotes the selected, verified excerpts verbatim and records their catalog revision, source ID, document and locator. The draft gives no eligibility or coverage assurance. An invalid model selection gives the reviewer a specific internal note with no product or claims. Cases with no stated needs or no sufficient evidence take their documented abstention paths before inference.

## Human scoring

Use an authorized reviewer. Open each draft in the dashboard alongside its opportunity and catalog entries. Check predicted outcome and source excerpts before deciding. For every case, record the case ID, decision, three scores, and a short note for any score below 2. Use this scale for each dimension.

| Dimension | 2 | 1 | 0 |
| --- | --- | --- | --- |
| Product fit | Appropriate candidate for all stated needs, or correct abstention with the right reason | A partial fit or an abstention that does not identify the right reason | Unsuitable product or a clear fit missed |
| Factual grounding | Each material statement follows from the cited excerpts, or the abstention makes no product claims | Source is broadly relevant but an important qualifier or citation is unclear | Unsupported or contradicted product or coverage claim |
| Usability | Reviewer can understand the opportunity, verify the rationale, and decide; the appropriate next step is clear | Reviewer can decide after an edit, additional lookup, or clarification | Draft cannot be reviewed or acted on without substantial rework |

Record reviewer identity, review date, number of cases scored, and totals out of 48 per dimension for a complete round. Record problematic case IDs and examples of the observed wording or missing evidence. For a follow-up after changes, use fresh cases and record the changes with the new case IDs and totals. Keep automated expected-outcome counts separate from these reviewer scores.
