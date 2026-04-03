"""
Core DocStream functionality.

v2 modules (extractor_v2, generator, compiler, ai_provider)
are imported directly by submodule path — not re-exported here.
Old v1 modules (docstream, extractor, structurer, renderer)
are available but not imported eagerly to avoid loading
deprecated dependencies at package initialization time.
"""
