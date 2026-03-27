"""
Template Matcher — maps semantic content to template fields.

Each template has a schema defining what fields it expects.
The matcher fills these fields from semantic chunks,
filling gaps intelligently and warning about missing content.

Templates supported:
- report:    title, abstract, sections, bibliography
- ieee:      title, authors, abstract, keywords,
             sections, references
- resume:    name, contact, summary, experience,
             education, skills, projects
- altacv:    (same as resume but different layout)
- moderncv:  (same as resume but formal style)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from docstream.core.semantic_analyzer import DocumentType, SemanticDocument


@dataclass
class TemplateSchema:
    """Declares required and optional fields for a template.

    Attributes:
        required_fields: Fields that must be populated for a valid output.
        optional_fields: Fields that improve output quality but are not mandatory.
        best_for: ``DocumentType`` values this template is optimised for.
    """

    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    best_for: "List[DocumentType]" = field(default_factory=list)


@dataclass
class TemplateData:
    """Filled template ready for LaTeX rendering.

    Attributes:
        template: Template name (e.g. ``"report"``, ``"resume"``).
        fields: Mapping of field names to content strings.
        missing_required: Required fields that could not be filled.
        warnings: Non-blocking issues to surface to the user.
    """

    template: str
    fields: dict[str, Any] = field(default_factory=dict)
    missing_required: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TemplateMatcher:
    """Map semantic content to template fields."""

    # Registry of known template schemas.
    SCHEMAS: dict[str, TemplateSchema] = {}

    def match(
        self,
        semantic_doc: "SemanticDocument",
        template: str,
    ) -> TemplateData:
        """Fill template fields from a ``SemanticDocument``.

        Args:
            semantic_doc: Analyzed document produced by ``SemanticAnalyzer``.
            template: Target template name.

        Returns:
            A ``TemplateData`` instance with populated fields.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError

    def score_compatibility(
        self,
        semantic_doc: "SemanticDocument",
        template: str,
    ) -> float:
        """Return a 0.0–1.0 compatibility score for a template.

        Higher scores mean the document's content maps well to
        the template's expected fields.

        Args:
            semantic_doc: Analyzed document produced by ``SemanticAnalyzer``.
            template: Template name to score against.

        Returns:
            Float in [0.0, 1.0].

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
