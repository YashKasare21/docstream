-- Report Template for Technical Documents
-- Suitable for technical reports, documentation, and internal papers

local template = {
    name = "Report Template",
    description = "Technical report template with standard formatting",
    version = "1.0.0",
    author = "DocStream Team",
    dependencies = {"geometry", "fancyhdr", "hyperref", "graphicx", "booktabs", "times"}
}

function template.render(document)
    local latex = {}
    
    -- Document class and packages
    table.insert(latex, "\\documentclass[11pt,a4paper]{report}")
    
    -- Page geometry
    table.insert(latex, "\\usepackage[margin=1in,top=1in,bottom=1in]{geometry}")
    
    -- Fonts and text
    table.insert(latex, "\\usepackage{times}")
    table.insert(latex, "\\usepackage[T1]{fontenc}")
    
    -- Headers and footers
    table.insert(latex, "\\usepackage{fancyhdr}")
    table.insert(latex, "\\pagestyle{fancy}")
    table.insert(latex, "\\fancyhf{}")
    table.insert(latex, "\\fancyhead[L]{" .. (document.metadata.title or "Document") .. "}")
    table.insert(latex, "\\fancyhead[R]{\\today}")
    table.insert(latex, "\\fancyfoot[C]{\\thepage}")
    
    -- Hyperlinks
    table.insert(latex, "\\usepackage{hyperref}")
    table.insert(latex, "\\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}")
    
    -- Graphics and tables
    table.insert(latex, "\\usepackage{graphicx}")
    table.insert(latex, "\\usepackage{booktabs}")
    table.insert(latex, "\\usepackage{float}")
    
    -- Math and symbols
    table.insert(latex, "\\usepackage{amsmath}")
    table.insert(latex, "\\usepackage{amssymb}")
    
    -- Lists and formatting
    table.insert(latex, "\\usepackage{enumitem}")
    table.insert(latex, "\\usepackage{verbatim}")
    
    -- Document information
    table.insert(latex, "\\title{" .. escape_latex(document.metadata.title or "Technical Report") .. "}")
    
    if document.metadata.author then
        table.insert(latex, "\\author{" .. escape_latex(document.metadata.author) .. "}")
    end
    
    table.insert(latex, "\\date{" .. (document.metadata.date or "\\today") .. "}")
    
    table.insert(latex, "\\begin{document}")
    
    -- Title page
    table.insert(latex, "\\maketitle")
    
    -- Table of contents
    table.insert(latex, "\\tableofcontents")
    table.insert(latex, "\\newpage")
    
    -- Abstract
    if document.metadata.abstract then
        table.insert(latex, "\\begin{abstract}")
        table.insert(latex, escape_latex(document.metadata.abstract))
        table.insert(latex, "\\end{abstract}")
        table.insert(latex, "\\newpage")
    end
    
    -- Main content
    for _, section in ipairs(document.sections) do
        table.insert(latex, render_section(section))
    end
    
    -- Appendices (if any)
    if document.metadata.appendices then
        table.insert(latex, "\\appendix")
        for _, appendix in ipairs(document.metadata.appendices) do
            table.insert(latex, "\\chapter{" .. escape_latex(appendix.title) .. "}")
            table.insert(latex, escape_latex(appendix.content))
        end
    end
    
    -- Bibliography
    table.insert(latex, "\\begin{thebibliography}{99}")
    table.insert(latex, "\\end{thebibliography}")
    
    table.insert(latex, "\\end{document}")
    
    return table.concat(latex, "\n")
end

function template.render_section(section)
    local content = {}
    
    -- Section heading with appropriate level
    if section.level == 1 then
        table.insert(content, "\\chapter{" .. escape_latex(section.title) .. "}")
    elseif section.level == 2 then
        table.insert(content, "\\section{" .. escape_latex(section.title) .. "}")
    elseif section.level == 3 then
        table.insert(content, "\\subsection{" .. escape_latex(section.title) .. "}")
    elseif section.level == 4 then
        table.insert(content, "\\subsubsection{" .. escape_latex(section.title) .. "}")
    else
        table.insert(content, "\\paragraph{" .. escape_latex(section.title) .. "}")
    end
    
    -- Add label for cross-referencing
    local label = string.gsub(section.title, "%s+", "_")
    label = string.gsub(label, "[^%w_]", "")
    table.insert(content, "\\label{sec:" .. label .. "}")
    
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
        if block.level == 5 then
            return "\\subparagraph{" .. escape_latex(block.content) .. "}\n\n"
        else
            return escape_latex(block.content) .. "\n\n"
        end
    elseif block.type == "list" then
        return render_list(block)
    elseif block.type == "code" then
        return render_code(block)
    elseif block.type == "quote" then
        return "\\begin{quote}\n" .. escape_latex(block.content) .. "\n\\end{quote}\n\n"
    elseif block.type == "table" then
        return render_table(block)
    elseif block.type == "image" then
        return render_image(block)
    else
        return escape_latex(block.content) .. "\n\n"
    end
end

function template.render_list(block)
    local content = {}
    
    if block.ordered then
        table.insert(content, "\\begin{enumerate}[label=\\arabic*.]")
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
    
    if block.language and block.language ~= "" then
        table.insert(content, "\\textbf{" .. block.language .. " Code:}")
    end
    
    table.insert(content, "\\begin{verbatim}")
    table.insert(content, block.content)
    table.insert(content, "\\end{verbatim}")
    
    return table.concat(content, "\n") .. "\n\n"
end

function template.render_table(block)
    local content = {}
    table.insert(content, "\\begin{table}[H]")
    table.insert(content, "\\centering")
    
    if block.caption then
        table.insert(content, "\\caption{" .. escape_latex(block.caption) .. "}")
    end
    
    table.insert(content, "\\begin{tabular}{" .. string.rep("l", #block.headers) .. "}")
    table.insert(content, "\\toprule")
    
    -- Headers
    local header_row = {}
    for _, header in ipairs(block.headers or {}) do
        table.insert(header_row, escape_latex(header))
    end
    table.insert(content, table.concat(header_row, " & ") .. " \\\\")
    table.insert(content, "\\midrule")
    
    -- Data rows
    for _, row in ipairs(block.rows or {}) do
        local row_content = {}
        for _, cell in ipairs(row) do
            table.insert(row_content, escape_latex(cell))
        end
        table.insert(content, table.concat(row_content, " & ") .. " \\\\")
    end
    
    table.insert(content, "\\bottomrule")
    table.insert(content, "\\end{tabular}")
    table.insert(content, "\\end{table}")
    
    return table.concat(content, "\n") .. "\n\n"
end

function template.render_image(block)
    local content = {}
    table.insert(content, "\\begin{figure}[H]")
    table.insert(content, "\\centering")
    
    local width = "\\textwidth"
    if block.width then
        width = block.width
    end
    
    table.insert(content, "\\includegraphics[width=" .. width .. "]{" .. block.src .. "}")
    
    if block.caption then
        table.insert(content, "\\caption{" .. escape_latex(block.caption) .. "}")
    end
    
    table.insert(content, "\\end{figure}")
    
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
