-- IEEE Template for Academic Papers
-- Compatible with IEEE conference and journal formats

local template = {
    name = "IEEE Template",
    description = "IEEE academic paper template for conferences and journals",
    version = "1.0.0",
    author = "DocStream Team",
    dependencies = {"IEEEconf", "graphicx", "amsmath", "url", "booktabs"}
}

function template.render(document)
    local latex = {}
    
    -- Document class and packages
    table.insert(latex, "\\documentclass[conference]{IEEEconf}")
    table.insert(latex, "\\IEEEoverridecommandlockouts")
    table.insert(latex, "\\IEEEoverridecommandlockouts")
    table.insert(latex, "\\IEEEstartofpreamble")
    
    -- Required packages
    table.insert(latex, "\\usepackage{cite}")
    table.insert(latex, "\\usepackage{amsmath,amssymb,amsfonts}")
    table.insert(latex, "\\usepackage{algorithmic}")
    table.insert(latex, "\\usepackage{graphicx}")
    table.insert(latex, "\\usepackage{textcomp}")
    table.insert(latex, "\\usepackage{xcolor}")
    table.insert(latex, "\\usepackage{url}")
    table.insert(latex, "\\usepackage{booktabs}")
    
    -- Document setup
    table.insert(latex, "\\def\\IEEEbibitemsep{1pt}")
    table.insert(latex, "\\IEEEoverridecommandlockouts")
    table.insert(latex, "\\IEEEstartofpreamble")
    
    -- Title and authors
    if document.metadata.title then
        table.insert(latex, "\\title{" .. escape_latex(document.metadata.title) .. "}")
    end
    
    if document.metadata.author then
        table.insert(latex, "\\author{\\IEEEauthorblockN{" .. escape_latex(document.metadata.author) .. "}}")
    end
    
    table.insert(latex, "\\IEEEendofpreamble")
    table.insert(latex, "\\begin{document}")
    
    -- Title
    table.insert(latex, "\\maketitle")
    
    -- Abstract
    if document.metadata.abstract then
        table.insert(latex, "\\begin{abstract}")
        table.insert(latex, escape_latex(document.metadata.abstract))
        table.insert(latex, "\\end{abstract}")
    end
    
    -- Keywords
    if document.metadata.keywords and #document.metadata.keywords > 0 then
        table.insert(latex, "\\begin{IEEEkeywords}")
        table.insert(latex, table.concat(document.metadata.keywords, ", "))
        table.insert(latex, "\\end{IEEEkeywords}")
    end
    
    -- Main content
    for _, section in ipairs(document.sections) do
        table.insert(latex, render_section(section))
    end
    
    -- References
    table.insert(latex, "\\begin{thebibliography}{99}")
    table.insert(latex, "\\end{thebibliography}")
    
    table.insert(latex, "\\end{document}")
    
    return table.concat(latex, "\n")
end

function template.render_section(section)
    local content = {}
    
    -- Section heading
    if section.level == 1 then
        table.insert(content, "\\section{" .. escape_latex(section.title) .. "}")
    elseif section.level == 2 then
        table.insert(content, "\\subsection{" .. escape_latex(section.title) .. "}")
    elseif section.level == 3 then
        table.insert(content, "\\subsubsection{" .. escape_latex(section.title) .. "}")
    else
        table.insert(content, "\\paragraph{" .. escape_latex(section.title) .. "}")
    end
    
    -- Section content
    for _, block in ipairs(section.blocks) do
        table.insert(content, render_block(block))
    end
    
    return table.concat(content, "\n")
end

function template.render_block(block)
    if block.type == "text" then
        return escape_latex(block.content) .. "\n\n"
    elseif block.type == "heading" then
        if block.level == 4 then
            return "\\paragraph{" .. escape_latex(block.content) .. "}\n\n"
        else
            return escape_latex(block.content) .. "\n\n"
        end
    elseif block.type == "list" then
        return render_list(block)
    elseif block.type == "code" then
        return render_code(block)
    elseif block.type == "quote" then
        return "\\begin{quote}\n" .. escape_latex(block.content) .. "\n\\end{quote}\n\n"
    else
        return escape_latex(block.content) .. "\n\n"
    end
end

function template.render_list(block)
    local content = {}
    
    if block.ordered then
        table.insert(content, "\\begin{enumerate}")
    else
        table.insert(content, "\\begin{itemize}")
    end
    
    for _, item in ipairs(block.items or {}) do
        table.insert(content, "\\item " .. escape_latex(item))
    end
    
    if block.ordered then
        table.insert(content, "\\end{enumerate}")
    else
        table.insert(content, "\\end{itemize}")
    end
    
    return table.concat(content, "\n") .. "\n\n"
end

function template.render_code(block)
    local content = {}
    table.insert(content, "\\begin{verbatim}")
    table.insert(content, block.content)
    table.insert(content, "\\end{verbatim}")
    return table.concat(content, "\n") .. "\n\n"
end

function template.escape_latex(text)
    if not text then return "" end
    
    local latex_special_chars = {
        ["&"] = "\\&",
        ["%"] = "\\%",
        ["$"] = "\\$",
        ["#"] = "\\#",
        ["_"] = "\\_",
        ["{"] = "\\{",
        ["}"] = "\\}",
        ["~"] = "\\textasciitilde{}",
        ["^"] = "\\^{}",
        ["\\"] = "\\textbackslash{}",
    }
    
    for char, escaped in pairs(latex_special_chars) do
        text = string.gsub(text, char, escaped)
    end
    
    return text
end

return template
