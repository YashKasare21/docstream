# Contributing to DocStream

Thank you for your interest in contributing to DocStream! This guide will help you get started with contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) for package management
- Git for version control
- LaTeX distribution (optional, for PDF compilation testing)

### Development Setup

1. **Fork the repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/yourusername/docstream.git
   cd docstream
   ```

2. **Set up the development environment**
   ```bash
   # Create virtual environment
   uv venv
   
   # Install dependencies
   uv sync --dev
   ```

3. **Configure environment variables**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env and add your API keys
   # GEMINI_API_KEY=your_gemini_api_key
   # GROQ_API_KEY=your_groq_api_key
   ```

4. **Verify setup**
   ```bash
   # Run tests
   make test
   
   # Run linting
   make lint
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description
```

### 2. Make Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. Run Quality Checks

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
make typecheck

# Run tests
make test

# Run all checks
make check
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat: add new template system"

# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create Pull Request

- Go to the GitHub repository
- Click "New Pull Request"
- Select your branch
- Fill out the PR template
- Submit the PR

## Code Style

### Python Style

We use [ruff](https://docs.astral.sh/ruff/) for code formatting and linting. The configuration is in `pyproject.toml`.

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .
```

### Type Hints

All code should include proper type hints using the standard `typing` module:

```python
from typing import List, Optional, Dict, Any
from docstream.models import DocumentAST

def process_document(
    file_path: str, 
    options: Optional[Dict[str, Any]] = None
) -> DocumentAST:
    """Process a document file."""
    pass
```

### Docstrings

All public functions and classes should have docstrings following the Google style:

```python
def extract_content(file_path: str) -> RawContent:
    """Extract content from a document file.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        RawContent object with extracted content
        
    Raises:
        ExtractionError: If extraction fails
        FileNotFoundError: If file doesn't exist
    """
    pass
```

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_extractor.py        # Extractor tests
├── test_structurer.py       # Structurer tests
├── test_renderer.py         # Renderer tests
├── test_models.py           # Model tests
├── test_templates.py        # Template tests
└── integration/             # Integration tests
    ├── test_pdf_to_latex.py
    └── test_latex_to_pdf.py
```

### Writing Tests

```python
import pytest
from docstream import DocStream
from docstream.models import DocumentAST, Section

class TestExtractor:
    def test_extract_pdf_content(self, sample_pdf_path):
        """Test PDF content extraction."""
        ds = DocStream()
        result = ds.extract_content(sample_pdf_path)
        
        assert result is not None
        assert len(result.blocks) > 0
    
    def test_extract_invalid_file(self):
        """Test extraction with invalid file."""
        ds = DocStream()
        
        with pytest.raises(ExtractionError):
            ds.extract_content("nonexistent.pdf")
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/test_extractor.py

# Run with coverage
uv run pytest --cov=docstream --cov-report=html

# Run integration tests
uv run pytest tests/integration/
```

### Test Fixtures

Use fixtures for common test setup:

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF file for testing."""
    return Path(__file__).parent / "fixtures" / "sample.pdf"

@pytest.fixture
def docstream_instance():
    """DocStream instance for testing."""
    return DocStream(debug=True)
```

## Documentation

### Documentation Structure

```
docs/
├── index.md                 # Main documentation
├── quickstart.md           # Getting started guide
├── architecture.md         # Architecture overview
├── templates.md            # Template system
├── api-reference.md        # API documentation
└── contributing.md         # This file
```

### Writing Documentation

- Use Markdown format
- Include code examples
- Add proper section headers
- Update API reference for new functions

### Building Documentation

```bash
# Build documentation
make docs

# Serve documentation locally
make docs-serve
```

## Template Development

### Creating Templates

Templates are written in Lua and follow a specific structure:

```lua
-- templates/my_template.lua
local template = {
    name = "My Template",
    description = "A custom template",
    dependencies = {"geometry", "fancyhdr"}
}

function template.render(document)
    -- Template implementation
    return latex_content
end

return template
```

### Template Testing

```python
def test_custom_template():
    """Test custom template rendering."""
    ds = DocStream()
    
    # Create test document
    doc = create_test_document()
    
    # Render with custom template
    result = ds.render_template(doc, "my_template.lua")
    
    # Assert expected content
    assert "\\documentclass{article}" in result
```

## Release Process

### Version Management

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version numbers**
   - `pyproject.toml`
   - `docstream/__init__.py`

2. **Update changelog**
   - Add new version section
   - List all changes

3. **Run full test suite**
   ```bash
   make check
   ```

4. **Create release tag**
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

5. **GitHub Actions will automatically:**
   - Run CI tests
   - Build package
   - Publish to PyPI

## Bug Reports

### Reporting Bugs

1. Check existing issues first
2. Use the bug report template
3. Include:
   - Environment details
   - Steps to reproduce
   - Expected vs actual behavior
   - Code examples
   - Error messages

### Bug Report Template

```markdown
## Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g. Ubuntu 20.04]
- Python: [e.g. 3.11.0]
- DocStream: [e.g. 0.1.0]

## Additional Context
Any other relevant information
```

## Feature Requests

### Requesting Features

1. Check existing issues and discussions
2. Use the feature request template
3. Include:
   - Use case description
   - Proposed solution
   - Alternatives considered
   - Implementation ideas (optional)

### Feature Request Template

```markdown
## Description
Clear description of the feature

## Use Case
Why this feature is needed

## Proposed Solution
How the feature should work

## Alternatives
Other approaches considered

## Additional Context
Any other relevant information
```

## Code Review Process

### Review Guidelines

1. **Functionality**: Does the code work as intended?
2. **Style**: Does it follow the project's style guidelines?
3. **Tests**: Are there adequate tests?
4. **Documentation**: Is the code well documented?
5. **Performance**: Are there any performance concerns?

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or clearly documented)
- [ ] Error handling is appropriate
- [ ] Security considerations are addressed

## Community Guidelines

### Code of Conduct

1. **Be respectful**: Treat everyone with respect
2. **Be inclusive**: Welcome contributors from all backgrounds
3. **Be constructive**: Provide helpful feedback
4. **Be patient**: Help newcomers learn the process

### Communication

- Use GitHub issues for bug reports and feature requests
- Use GitHub discussions for general questions
- Be clear and concise in your communications
- Provide context when asking for help

## Getting Help

### Resources

- [Documentation](https://docstream.readthedocs.io/)
- [GitHub Issues](https://github.com/yourusername/docstream/issues)
- [GitHub Discussions](https://github.com/yourusername/docstream/discussions)

### Contact

- Create an issue for bug reports
- Start a discussion for questions
- Mention maintainers for urgent issues

## Recognition

### Contributors

All contributors are recognized in:

- README.md contributors section
- GitHub contributors graph
- Release notes for significant contributions

### Types of Contributions

- **Code**: New features, bug fixes, optimizations
- **Documentation**: Improving docs, examples, tutorials
- **Templates**: Creating new document templates
- **Testing**: Writing tests, improving test coverage
- **Community**: Helping others, answering questions

Thank you for contributing to DocStream! 🎉
