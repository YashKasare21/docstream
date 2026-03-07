# Template System

DocStream's template system provides flexible and powerful document formatting capabilities using Lua templates for LaTeX generation.

## Built-in Templates

### IEEE Template

**Purpose**: Academic papers and conference proceedings
**Use Case**: Research papers, technical articles, academic publications

**Features:**
- IEEE two-column layout
- Automatic figure and table numbering
- Bibliography support
- Abstract and keywords sections

```python
from docstream import DocStream, TemplateType

ds = DocStream()
result = ds.pdf_to_latex("paper.pdf", template=TemplateType.IEEE)
```

### Report Template

**Purpose**: Technical reports and documentation
**Use Case**: Internal reports, documentation, technical specifications

**Features:**
- Single-column layout
- Title page with metadata
- Table of contents
- Section and subsection hierarchy

```python
result = ds.pdf_to_latex("report.pdf", template=TemplateType.REPORT)
```

### Resume Template

**Purpose**: Professional resumes and CVs
**Use Case**: Job applications, professional profiles

**Features:**
- Modern resume layout
- Contact information section
- Work experience formatting
- Skills and education sections

```python
result = ds.pdf_to_latex("resume.pdf", template=TemplateType.RESUME)
```

## Template Structure

### Lua Template Format

Templates are written in Lua and follow a specific structure:

```lua
-- template_name.lua
local template = {}

function template.render(document)
    -- Document is a DocumentAST object
    local latex = {}
    
    -- Preamble
    table.insert(latex, "\\documentclass{article}")
    table.insert(latex, "\\usepackage{...}")
    
    -- Document content
    for _, section in ipairs(document.sections) do
        table.insert(latex, render_section(section))
    end
    
    return table.concat(latex, "\n")
end

function template.render_section(section)
    -- Render individual sections
    local content = {}
    
    if section.level == 1 then
        table.insert(content, "\\section{" .. section.title .. "}")
    elseif section.level == 2 then
        table.insert(content, "\\subsection{" .. section.title .. "}")
    end
    
    -- Add section content
    for _, block in ipairs(section.blocks) do
        table.insert(content, render_block(block))
    end
    
    return table.concat(content, "\n")
end

function template.render_block(block)
    -- Render different block types
    if block.type == "text" then
        return block.content
    elseif block.type == "heading" then
        return "\\" .. block.level .. "section{" .. block.content .. "}"
    end
end

return template
```

### Template Metadata

Templates can include metadata for configuration:

```lua
-- template_name.lua
local template = {
    name = "Custom Template",
    description = "A custom template for specific documents",
    version = "1.0.0",
    author = "Your Name",
    dependencies = {"geometry", "hyperref"},
    options = {
        font_size = {type = "number", default = 11},
        margin = {type = "string", default = "1in"},
        columns = {type = "number", default = 1}
    }
}
```

## Custom Templates

### Creating Custom Templates

1. Create a new Lua file in the templates directory:

```bash
# In your project
mkdir templates
touch templates/custom_template.lua
```

2. Implement the template functions:

```lua
-- templates/custom_template.lua
local template = {
    name = "Custom Template",
    description = "My custom document template",
    dependencies = {"geometry", "fancyhdr"}
}

function template.render(document)
    local latex = {}
    
    -- Document class and packages
    table.insert(latex, "\\documentclass{article}")
    table.insert(latex, "\\usepackage[margin=1in]{geometry}")
    table.insert(latex, "\\usepackage{fancyhdr}")
    
    -- Custom header/footer
    table.insert(latex, "\\pagestyle{fancy}")
    table.insert(latex, "\\fancyhf{}")
    table.insert(latex, "\\rhead{" .. (document.metadata.title or "Document") .. "}")
    table.insert(latex, "\\cfoot{\\thepage}")
    
    -- Document content
    table.insert(latex, "\\begin{document}")
    
    -- Title
    if document.metadata.title then
        table.insert(latex, "\\title{" .. document.metadata.title .. "}")
        table.insert(latex, "\\maketitle")
    end
    
    -- Sections
    for _, section in ipairs(document.sections) do
        table.insert(latex, template.render_section(section))
    end
    
    table.insert(latex, "\\end{document}")
    
    return table.concat(latex, "\n")
end

function template.render_section(section)
    local content = {}
    local section_cmd = "\\section"
    
    if section.level == 1 then
        section_cmd = "\\section"
    elseif section.level == 2 then
        section_cmd = "\\subsection"
    elseif section.level == 3 then
        section_cmd = "\\subsubsection"
    end
    
    table.insert(content, section_cmd .. "{" .. section.title .. "}")
    
    for _, block in ipairs(section.blocks) do
        table.insert(content, template.render_block(block))
    end
    
    return table.concat(content, "\n")
end

function template.render_block(block)
    if block.type == "text" then
        return block.content
    elseif block.type == "code" then
        return "\\begin{verbatim}\n" .. block.content .. "\n\\end{verbatim}"
    elseif block.type == "list" then
        local list_content = {}
        for _, item in ipairs(block.items) do
            table.insert(list_content, "\\item " .. item)
        end
        return "\\begin{itemize}\n" .. table.concat(list_content, "\n") .. "\n\\end{itemize}"
    end
    return ""
end

return template
```

### Using Custom Templates

```python
from docstream import DocStream

ds = DocStream()

# Use custom template
result = ds.pdf_to_latex("document.pdf", template="path/to/custom_template.lua")
```

### Template Options

Pass options to customize template behavior:

```python
options = {
    "font_size": 12,
    "margin": "1.5in",
    "columns": 2
}

result = ds.pdf_to_latex("document.pdf", 
                        template="custom_template.lua", 
                        options=options)
```

## Template Development

### Testing Templates

Create test documents to validate template output:

```python
def test_custom_template():
    from docstream.models import DocumentAST, Section, TextBlock
    
    # Create test document
    doc = DocumentAST(
        sections=[
            Section(
                title="Test Section",
                level=1,
                blocks=[TextBlock(content="This is a test.")]
            )
        ]
    )
    
    # Test template rendering
    ds = DocStream()
    result = ds.render_template(doc, "custom_template.lua")
    
    assert "\\section{Test Section}" in result
    assert "This is a test." in result
```

### Template Debugging

Enable debug mode to see intermediate steps:

```python
ds = DocStream(debug=True)
result = ds.pdf_to_latex("document.pdf", template="custom_template.lua")
# Debug information will be printed
```

### Best Practices

1. **Modular Design**: Break complex templates into smaller functions
2. **Error Handling**: Add validation for required fields
3. **Documentation**: Include clear comments and metadata
4. **Testing**: Test with various document structures
5. **Performance**: Optimize for large documents

## Advanced Features

### Conditional Rendering

```lua
function template.render_section(section)
    local content = {}
    
    -- Only render sections with content
    if #section.blocks > 0 then
        table.insert(content, "\\section{" .. section.title .. "}")
        -- ... rest of rendering
    end
    
    return table.concat(content, "\n")
end
```

### Custom Commands

```lua
function template.render_block(block)
    if block.type == "highlight" then
        return "\\textcolor{blue}{" .. block.content .. "}"
    end
    -- ... other block types
end
```

### Template Inheritance

```lua
-- base_template.lua
local base = {}

function base.render_preamble(document)
    return "\\documentclass{article}\n\\usepackage{geometry}"
end

-- custom_template.lua
local custom = {}
setmetatable(custom, {__index = require("base_template")})

function custom.render(document)
    local latex = {}
    table.insert(latex, custom.render_preamble(document))
    -- ... custom rendering
    return table.concat(latex, "\n")
end
```

## Template Registry

### Registering Templates

```python
from docstream.templates import TemplateRegistry

registry = TemplateRegistry()
registry.register("my_template", "/path/to/my_template.lua")
```

### Discovering Templates

```python
# List available templates
templates = ds.list_templates()
print(templates)  # ["ieee", "report", "resume", "my_template"]

# Get template info
info = ds.get_template_info("ieee")
print(info.name, info.description)
```

## Troubleshooting

### Common Template Issues

1. **Syntax Errors**: Check Lua syntax with `luac -l template.lua`
2. **Missing Dependencies**: Ensure all LaTeX packages are available
3. **Encoding Issues**: Use UTF-8 encoding for all template files
4. **Path Issues**: Use absolute paths for custom templates

### Debug Mode

Enable debug mode for detailed error information:

```python
ds = DocStream(debug=True)
```

### Template Validation

Validate templates before use:

```python
is_valid = ds.validate_template("template.lua")
if not is_valid:
    print("Template validation failed")
```
