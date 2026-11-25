"""LLM outputs are cleaned before being stored as drafts for the reviewer."""

from utils.llm_output import clean_subject, extract_mail_body


def test_json_body_requested_by_the_prompts_is_unwrapped():
    raw = '```json\n{\n  "corps_du_mail_en_français": "Bonjour Ahmed,\\n\\nMerci."\n}\n```'
    assert extract_mail_body(raw) == "Bonjour Ahmed,\n\nMerci."


def test_raw_newlines_inside_the_json_string_are_tolerated():
    # invalid JSON, but a frequent LLM output
    raw = '```json\n{\n  "corps_du_mail_en_français": "Bonjour Ahmed,\n\nMerci."\n}\n```'
    assert extract_mail_body(raw) == "Bonjour Ahmed,\n\nMerci."


def test_truncated_json_still_yields_the_body():
    raw = '{"corps_du_mail_en_français": "Bonjour \\"cher\\" client"'
    assert extract_mail_body(raw) == 'Bonjour "cher" client'


def test_plain_text_and_other_shapes_are_kept():
    assert extract_mail_body("  Bonjour, simple texte. ") == "Bonjour, simple texte."
    assert extract_mail_body('{"message": "Texte"}') == "Texte"
    assert extract_mail_body(None) is None


def test_subject_line_repeated_in_the_body_is_dropped():
    raw = "Objet : Votre protection sur mesure\n\nBonjour Madame,\n\nVoici notre offre."
    assert extract_mail_body(raw) == "Bonjour Madame,\n\nVoici notre offre."
    assert extract_mail_body("**Objet :** Test\nBonjour") == "Bonjour"


def test_subject_is_one_clean_line():
    assert clean_subject('Objet: "Protection accident - Contact"\nautre') == "Protection accident - Contact"
    assert clean_subject("  Subject : Renouvellement  ") == "Renouvellement"
    assert clean_subject("Votre devis auto") == "Votre devis auto"
