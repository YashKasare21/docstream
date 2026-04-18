"""
Tests for TemplateMatcher and TEMPLATE_SCHEMAS.

No network calls — all inputs are hand-crafted SemanticDocument fixtures.
"""

from __future__ import annotations

import pytest

from docstream.exceptions import TemplateError
from docstream.models.document import (
    DocumentType,
    SemanticChunk,
    SemanticDocument,
    TemplateData,
    TemplateSchema,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _chunk(chunk_type: str, content: str, importance: float = 0.8) -> SemanticChunk:
    return SemanticChunk(chunk_type=chunk_type, content=content, importance=importance)


def _empty_doc(doc_type: DocumentType = DocumentType.UNKNOWN) -> SemanticDocument:
    return SemanticDocument(document_type=doc_type, title="")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unknown template raises TemplateError
# ─────────────────────────────────────────────────────────────────────────────


def test_unknown_template_raises():
    from docstream.core.template_matcher import TemplateMatcher

    matcher = TemplateMatcher()
    doc = _empty_doc()
    with pytest.raises(TemplateError):
        matcher.match(doc, "nonexistent_template")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Resume template — required fields filled from chunks
# ─────────────────────────────────────────────────────────────────────────────


def test_resume_required_fields_filled(resume_doc):
    from docstream.core.template_matcher import TemplateMatcher

    data = TemplateMatcher().match(resume_doc, "resume")

    assert isinstance(data, TemplateData)
    assert "name" in data.fields
    assert "contact" in data.fields
    assert "experience" in data.fields


# ─────────────────────────────────────────────────────────────────────────────
# 3. Resume template — missing work_experience → missing_required contains it
# ─────────────────────────────────────────────────────────────────────────────


def test_resume_missing_experience_reported():
    from docstream.core.template_matcher import TemplateMatcher

    doc = SemanticDocument(
        document_type=DocumentType.RESUME,
        title="No Experience",
        chunks=[
            _chunk("contact_info", "John Doe, john@example.com", importance=1.0),
        ],
    )
    data = TemplateMatcher().match(doc, "resume")

    assert "experience" in data.missing_required
    assert len(data.warnings) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. IEEE template — all required fields satisfied by paper_doc
# ─────────────────────────────────────────────────────────────────────────────


def test_ieee_required_fields_filled(paper_doc):
    from docstream.core.template_matcher import TemplateMatcher

    data = TemplateMatcher().match(paper_doc, "ieee")

    assert data.missing_required == []
    assert "abstract" in data.fields
    assert "keywords" in data.fields
    assert "sections" in data.fields
    assert "references" in data.fields


# ─────────────────────────────────────────────────────────────────────────────
# 5. Report template — title comes from SemanticDocument.title
# ─────────────────────────────────────────────────────────────────────────────


def test_report_title_from_document():
    from docstream.core.template_matcher import TemplateMatcher

    doc = SemanticDocument(
        document_type=DocumentType.ACADEMIC_REPORT,
        title="Annual Research Report 2024",
        chunks=[
            _chunk("abstract", "This is the executive summary."),
            _chunk("introduction", "Section one content."),
        ],
    )
    data = TemplateMatcher().match(doc, "report")

    assert data.fields.get("title") == "Annual Research Report 2024"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Score — resume doc against "resume" template is high
# ─────────────────────────────────────────────────────────────────────────────


def test_score_resume_high_for_resume_template(resume_doc):
    from docstream.core.template_matcher import TemplateMatcher

    score = TemplateMatcher().score_compatibility(resume_doc, "resume")
    assert score >= 0.7


# ─────────────────────────────────────────────────────────────────────────────
# 7. Score — resume doc against "ieee" is lower than against "resume"
# ─────────────────────────────────────────────────────────────────────────────


def test_score_type_mismatch_gives_lower_score(resume_doc):
    from docstream.core.template_matcher import TemplateMatcher

    matcher = TemplateMatcher()
    resume_score = matcher.score_compatibility(resume_doc, "resume")
    ieee_score = matcher.score_compatibility(resume_doc, "ieee")

    assert resume_score > ieee_score


# ─────────────────────────────────────────────────────────────────────────────
# 8. Score — always in [0.0, 1.0] for all five templates
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("template", ["report", "ieee", "resume", "altacv", "moderncv"])
def test_score_in_valid_range(resume_doc, template):
    from docstream.core.template_matcher import TemplateMatcher

    score = TemplateMatcher().score_compatibility(resume_doc, template)
    assert 0.0 <= score <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Score — unknown template returns 0.0 (no error)
# ─────────────────────────────────────────────────────────────────────────────


def test_score_unknown_template_returns_zero(resume_doc):
    from docstream.core.template_matcher import TemplateMatcher

    score = TemplateMatcher().score_compatibility(resume_doc, "does_not_exist")
    assert score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 10. recommend_templates — returns exactly 5 entries
# ─────────────────────────────────────────────────────────────────────────────


def test_recommend_templates_returns_five(resume_doc):
    from docstream.core.template_matcher import TemplateMatcher

    results = TemplateMatcher().recommend_templates(resume_doc)
    assert len(results) == 5


# ─────────────────────────────────────────────────────────────────────────────
# 11. recommend_templates — sorted descending by score
# ─────────────────────────────────────────────────────────────────────────────


def test_recommend_templates_sorted_descending(paper_doc):
    from docstream.core.template_matcher import TemplateMatcher

    results = TemplateMatcher().recommend_templates(paper_doc)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Multi-field — collects all matching chunks as a list
# ─────────────────────────────────────────────────────────────────────────────


def test_multi_field_collects_all_chunks():
    from docstream.core.template_matcher import TemplateMatcher

    doc = SemanticDocument(
        document_type=DocumentType.RESUME,
        title="Multi Test",
        chunks=[
            _chunk("contact_info", "Alice, alice@example.com", importance=1.0),
            _chunk("work_experience", "Job A", importance=0.9),
            _chunk("work_experience", "Job B", importance=0.8),
            _chunk("work_experience", "Job C", importance=0.7),
        ],
    )
    data = TemplateMatcher().match(doc, "resume")

    experience = data.fields.get("experience", [])
    assert isinstance(experience, list)
    assert len(experience) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 13. Single-field — picks chunk with highest importance
# ─────────────────────────────────────────────────────────────────────────────


def test_single_field_picks_highest_importance():
    from docstream.core.template_matcher import TemplateMatcher

    doc = SemanticDocument(
        document_type=DocumentType.RESEARCH_PAPER,
        title="Importance Test",
        chunks=[
            _chunk("abstract", "Low quality abstract", importance=0.3),
            _chunk("abstract", "High quality abstract", importance=0.95),
            _chunk("keywords", "kw1, kw2"),
            _chunk("introduction", "Intro text"),
            _chunk("methodology", "Methods"),
            _chunk("results", "Results"),
            _chunk("references", "References"),
        ],
    )
    data = TemplateMatcher().match(doc, "ieee")

    assert data.fields["abstract"] == "High quality abstract"


# ─────────────────────────────────────────────────────────────────────────────
# 14. All five template schemas are registered and have required fields
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("template", ["report", "ieee", "resume", "altacv", "moderncv"])
def test_template_schemas_registered(template):
    from docstream.core.template_matcher import TEMPLATE_SCHEMAS

    assert template in TEMPLATE_SCHEMAS
    schema = TEMPLATE_SCHEMAS[template]
    assert isinstance(schema, TemplateSchema)
    assert any(f.required for f in schema.fields), f"{template} has no required fields"


# ─────────────────────────────────────────────────────────────────────────────
# 15. TemplateData carries score and missing_required
# ─────────────────────────────────────────────────────────────────────────────


def test_template_data_has_score_and_missing(resume_doc):
    from docstream.core.template_matcher import TemplateMatcher

    data = TemplateMatcher().match(resume_doc, "resume")

    assert isinstance(data, TemplateData)
    assert isinstance(data.score, float)
    assert isinstance(data.missing_required, list)
    assert data.score > 0.0  # resume_doc has the required fields
