# Known Issues — v0.1.0 Testing

## Format: [STATUS] Description — PDF type — Error message

### Found & Fixed During Real-World Testing

- [x] `gemini-1.5-flash` model removed from Google API → updated to `gemini-2.0-flash`
- [x] `llama-3.1-70b-versatile` decommissioned on Groq → updated to `llama-3.3-70b-versatile`
- [x] Lua `write_inlines` crash on nil / unhandled inline types (Link, Math, Cite, etc.) → added full Pandoc inline coverage + nil guard
- [x] `IEEEtran.cls` missing in Docker images → added `texlive-publishers` to Dockerfiles
- [x] CLI `extract --output` fails on nested directories → added `parent.mkdir(parents=True)`
- [x] `test_pdfs/` directory leaked into Docker image → added to `.dockerignore`

### Known Limitations (not bugs)

- Author names from multi-author PDFs may be concatenated without commas (depends on AI structuring output)
- Gemini free-tier quota can be exhausted quickly with large documents; consider upgrading to paid tier
- Groq free-tier has 100K TPD limit; large documents consume ~10K tokens per call
- `pymupdf_layout` warning printed to stderr (cosmetic, does not affect output)
