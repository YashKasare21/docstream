"""
Template Matcher — maps semantic content to template fields.

Each template has a schema defining what fields it expects.
The matcher fills these fields from semantic chunks,
picking the highest-importance chunk per field (or collecting
all matching chunks when ``multi=True``).

Templates supported:
- report:    title, abstract, sections, bibliography
- ieee:      title, authors, abstract, keywords,
             sections, references
- resume:    name, contact, summary, experience,
             education, skills, projects
- altacv:    sidebar resume (same fields, different layout)
- moderncv:  formal resume (formal style)
"""

from __future__ import annotations

import logging

from docstream.exceptions import TemplateError
from docstream.models.document import (
    DocumentType,
    SemanticChunk,
    SemanticDocument,
    TemplateData,
    TemplateField,
    TemplateSchema,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template schema definitions
# ---------------------------------------------------------------------------

TEMPLATE_SCHEMAS: dict[str, TemplateSchema] = {
    "report": TemplateSchema(
        template="report",
        description="Academic or technical report",
        best_for=[DocumentType.ACADEMIC_REPORT, DocumentType.TECHNICAL_REPORT],
        fields=[
            TemplateField(
                name="title",
                description="Document title",
                required=True,
                chunk_types=[],
            ),
            TemplateField(
                name="abstract",
                description="Abstract or executive summary",
                required=True,
                chunk_types=["abstract", "executive_summary"],
            ),
            TemplateField(
                name="sections",
                description="Body sections",
                required=True,
                multi=True,
                chunk_types=[
                    "introduction",
                    "methodology",
                    "results",
                    "discussion",
                    "findings",
                    "section",
                    "conclusion",
                    "recommendations",
                ],
            ),
            TemplateField(
                name="keywords",
                description="Keywords",
                required=False,
                chunk_types=["keywords"],
            ),
            TemplateField(
                name="bibliography",
                description="Reference list",
                required=False,
                chunk_types=["references"],
            ),
            TemplateField(
                name="appendix",
                description="Appendix material",
                required=False,
                chunk_types=["appendix"],
            ),
        ],
    ),
    "ieee": TemplateSchema(
        template="ieee",
        description="IEEE conference or journal paper",
        best_for=[DocumentType.RESEARCH_PAPER],
        fields=[
            TemplateField(
                name="title",
                description="Paper title",
                required=True,
                chunk_types=[],
            ),
            TemplateField(
                name="abstract",
                description="Abstract (150–250 words)",
                required=True,
                chunk_types=["abstract"],
            ),
            TemplateField(
                name="keywords",
                description="Index terms / keywords",
                required=True,
                chunk_types=["keywords"],
            ),
            TemplateField(
                name="sections",
                description="Paper body",
                required=True,
                multi=True,
                chunk_types=[
                    "introduction",
                    "related_work",
                    "methodology",
                    "results",
                    "discussion",
                    "conclusion",
                    "section",
                ],
            ),
            TemplateField(
                name="references",
                description="IEEE-formatted bibliography",
                required=True,
                chunk_types=["references"],
            ),
            TemplateField(
                name="authors",
                description="Author list with affiliations",
                required=False,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="acknowledgments",
                description="Acknowledgments section",
                required=False,
                chunk_types=["acknowledgments"],
            ),
        ],
    ),
    "resume": TemplateSchema(
        template="resume",
        description="Standard single-column LaTeX résumé",
        best_for=[DocumentType.RESUME],
        fields=[
            TemplateField(
                name="name",
                description="Full name",
                required=True,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="contact",
                description="Contact details (email, phone, LinkedIn)",
                required=True,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="experience",
                description="Work experience entries",
                required=True,
                multi=True,
                chunk_types=["work_experience"],
            ),
            TemplateField(
                name="summary",
                description="Professional summary or objective",
                required=False,
                chunk_types=["summary"],
            ),
            TemplateField(
                name="education",
                description="Education history",
                required=False,
                multi=True,
                chunk_types=["education"],
            ),
            TemplateField(
                name="skills",
                description="Technical and soft skills",
                required=False,
                chunk_types=["skills"],
            ),
            TemplateField(
                name="projects",
                description="Notable projects",
                required=False,
                multi=True,
                chunk_types=["projects"],
            ),
            TemplateField(
                name="certifications",
                description="Certifications and awards",
                required=False,
                chunk_types=["certifications", "awards"],
            ),
        ],
    ),
    "altacv": TemplateSchema(
        template="altacv",
        description="AltaCV two-column sidebar résumé",
        best_for=[DocumentType.RESUME],
        fields=[
            TemplateField(
                name="name",
                description="Full name",
                required=True,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="contact",
                description="Contact details for the sidebar",
                required=True,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="experience",
                description="Work experience entries",
                required=True,
                multi=True,
                chunk_types=["work_experience"],
            ),
            TemplateField(
                name="skills",
                description="Skills wheel (sidebar)",
                required=False,
                chunk_types=["skills"],
            ),
            TemplateField(
                name="education",
                description="Education entries",
                required=False,
                multi=True,
                chunk_types=["education"],
            ),
            TemplateField(
                name="summary",
                description="About me / personal statement",
                required=False,
                chunk_types=["summary"],
            ),
            TemplateField(
                name="languages",
                description="Spoken languages",
                required=False,
                chunk_types=["languages"],
            ),
        ],
    ),
    "moderncv": TemplateSchema(
        template="moderncv",
        description="ModernCV formal résumé",
        best_for=[DocumentType.RESUME],
        fields=[
            TemplateField(
                name="name",
                description="Full name",
                required=True,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="contact",
                description="Contact details",
                required=True,
                chunk_types=["contact_info"],
            ),
            TemplateField(
                name="experience",
                description="Work experience",
                required=False,
                multi=True,
                chunk_types=["work_experience"],
            ),
            TemplateField(
                name="education",
                description="Education history",
                required=False,
                multi=True,
                chunk_types=["education"],
            ),
            TemplateField(
                name="skills",
                description="Skills and languages",
                required=False,
                chunk_types=["skills", "languages"],
            ),
            TemplateField(
                name="interests",
                description="Interests and hobbies",
                required=False,
                chunk_types=["interests", "hobbies"],
            ),
        ],
    ),
}


# ---------------------------------------------------------------------------
# TemplateMatcher
# ---------------------------------------------------------------------------


class TemplateMatcher:
    """Map a ``SemanticDocument`` to a specific LaTeX template's fields.

    Usage::

        matcher = TemplateMatcher()
        data = matcher.match(semantic_doc, "resume")
        scores = matcher.recommend_templates(semantic_doc)
    """

    # Expose schemas as a class attribute for easy inspection / testing
    SCHEMAS: dict[str, TemplateSchema] = TEMPLATE_SCHEMAS

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def match(
        self,
        semantic_doc: SemanticDocument,
        template: str,
    ) -> TemplateData:
        """Fill template fields from a ``SemanticDocument``.

        Args:
            semantic_doc: Analyzed document produced by ``SemanticAnalyzer``.
            template: Target template name (``"report"``, ``"ieee"``,
                      ``"resume"``, ``"altacv"``, ``"moderncv"``).

        Returns:
            A ``TemplateData`` with populated ``fields``, ``missing_required``,
            ``warnings``, and ``score``.

        Raises:
            TemplateError: If *template* is not one of the five built-in names.
        """
        if template not in TEMPLATE_SCHEMAS:
            raise TemplateError(
                f"Unknown template {template!r}. Available: {sorted(TEMPLATE_SCHEMAS)}"
            )

        schema = TEMPLATE_SCHEMAS[template]
        filled_fields: dict = {}
        missing_required: list[str] = []
        warnings: list[str] = []

        # Index chunks by type for O(total_chunks) lookup across all fields
        chunks_by_type: dict[str, list[SemanticChunk]] = {}
        for chunk in semantic_doc.chunks:
            chunks_by_type.setdefault(chunk.chunk_type, []).append(chunk)

        for tfield in schema.fields:
            # Special case: title is pulled from SemanticDocument.title
            if tfield.name == "title" and not tfield.chunk_types:
                value = (semantic_doc.title or "").strip()
                if value:
                    filled_fields["title"] = value
                elif tfield.required:
                    missing_required.append("title")
                    warnings.append("Required field 'title' not found in document")
                continue

            # Gather all chunks whose type matches any of the field's chunk_types
            matching: list[SemanticChunk] = []
            for ct in tfield.chunk_types:
                matching.extend(chunks_by_type.get(ct, []))

            if not matching:
                if tfield.required:
                    missing_required.append(tfield.name)
                    warnings.append(
                        f"Required field '{tfield.name}' could not be filled — "
                        f"no chunks of type {tfield.chunk_types}"
                    )
                continue

            if tfield.multi:
                # Preserve document order (already ordered by chunk position)
                filled_fields[tfield.name] = [c.content for c in matching]
            else:
                # Pick the highest-importance chunk
                best = max(matching, key=lambda c: c.importance)
                filled_fields[tfield.name] = best.content

        score = self.score_compatibility(semantic_doc, template)

        return TemplateData(
            template=template,
            fields=filled_fields,
            missing_required=missing_required,
            warnings=warnings,
            score=score,
        )

    def score_compatibility(
        self,
        semantic_doc: SemanticDocument,
        template: str,
    ) -> float:
        """Return a 0.0–1.0 compatibility score for a (document, template) pair.

        Scoring formula:
          - required_score = required fields satisfied / total required fields
          - optional_score = optional fields satisfied / total optional fields
          - base = required_score × 0.7 + optional_score × 0.3
          - +0.10 bonus if the document's ``DocumentType`` is in
            ``schema.best_for`` (capped at 1.0)

        Args:
            semantic_doc: Analyzed document.
            template: Template name to score against.

        Returns:
            Float in [0.0, 1.0].  Returns 0.0 for unknown templates.
        """
        if template not in TEMPLATE_SCHEMAS:
            return 0.0

        schema = TEMPLATE_SCHEMAS[template]
        chunk_types_present = {c.chunk_type for c in semantic_doc.chunks}

        required_fields = [f for f in schema.fields if f.required]
        optional_fields = [f for f in schema.fields if not f.required]

        def _field_satisfied(tfield: TemplateField) -> bool:
            if tfield.name == "title" and not tfield.chunk_types:
                return bool((semantic_doc.title or "").strip())
            return any(ct in chunk_types_present for ct in tfield.chunk_types)

        req_filled = sum(1 for f in required_fields if _field_satisfied(f))
        opt_filled = sum(1 for f in optional_fields if _field_satisfied(f))

        req_total = len(required_fields)
        opt_total = len(optional_fields)

        req_score = req_filled / req_total if req_total else 1.0
        opt_score = opt_filled / opt_total if opt_total else 1.0

        base = req_score * 0.7 + opt_score * 0.3

        # Document-type bonus
        if semantic_doc.document_type in schema.best_for:
            base = min(1.0, base + 0.10)

        return round(base, 4)

    def recommend_templates(
        self,
        semantic_doc: SemanticDocument,
    ) -> list[tuple[str, float]]:
        """Return all templates ranked by compatibility score (descending).

        Args:
            semantic_doc: Analyzed document.

        Returns:
            List of ``(template_name, score)`` tuples, highest score first.
            Always contains exactly ``len(TEMPLATE_SCHEMAS)`` entries.
        """
        scores = [(name, self.score_compatibility(semantic_doc, name)) for name in TEMPLATE_SCHEMAS]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
