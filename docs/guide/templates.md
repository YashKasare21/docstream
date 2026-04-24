# Templates

Docstream includes two production-ready LaTeX templates.

## Report Template

Single-column academic report using the `article` document class.

```python
result = docstream.convert("paper.pdf", template="report")
```

**Best for:**
- Academic reports
- Theses and dissertations
- Technical documents
- General research papers

**Features:**
- 12pt font, A4 paper
- Numbered sections
- Table of contents support
- Standard bibliography

## IEEE Template

Two-column conference paper using `IEEEtran` document class.

```python
result = docstream.convert("paper.pdf", template="ieee")
```

**Best for:**
- IEEE conference submissions
- Journal papers
- Technical papers with two-column layout

**Features:**
- IEEEtran document class
- Two-column layout
- Roman numeral section headers
- IEEE-style bibliography