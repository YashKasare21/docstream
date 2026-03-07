-- Resume Template for Professional CVs
-- Modern resume template suitable for job applications

local template = {
    name = "Resume Template",
    description = "Professional resume template for job applications",
    version = "1.0.0",
    author = "DocStream Team",
    dependencies = {"geometry", "hyperref", "xcolor", "fontawesome5", "titlesec"}
}

function template.render(document)
    local latex = {}
    
    -- Document class and packages
    table.insert(latex, "\\documentclass[11pt,a4paper,sans]{moderncv}")
    
    -- ModernCV theme and color
    table.insert(latex, "\\moderncvstyle{classic}")
    table.insert(latex, "\\moderncvcolor{blue}")
    
    -- Page geometry
    table.insert(latex, "\\usepackage[scale=0.75]{geometry}")
    
    -- Font packages
    table.insert(latex, "\\usepackage[utf8]{inputenc}")
    table.insert(latex, "\\usepackage[T1]{fontenc}")
    
    -- Hyperlinks
    table.insert(latex, "\\usepackage{hyperref}")
    table.insert(latex, "\\hypersetup{colorlinks=true,urlcolor=blue}")
    
    -- Additional packages
    table.insert(latex, "\\usepackage{xcolor}")
    table.insert(latex, "\\usepackage{titlesec}")
    
    -- Custom commands
    table.insert(latex, "\\name{" .. (document.metadata.first_name or "") .. "}{" .. (document.metadata.last_name or "") .. "}")
    
    if document.metadata.address then
        table.insert(latex, "\\address{" .. escape_latex(document.metadata.address) .. "}")
    end
    
    if document.metadata.phone then
        table.insert(latex, "\\phone{" .. escape_latex(document.metadata.phone) .. "}")
    end
    
    if document.metadata.email then
        table.insert(latex, "\\email{" .. escape_latex(document.metadata.email) .. "}")
    end
    
    if document.metadata.website then
        table.insert(latex, "\\homepage{" .. escape_latex(document.metadata.website) .. "}")
    end
    
    if document.metadata.linkedin then
        table.insert(latex, "\\social[linkedin]{" .. escape_latex(document.metadata.linkedin) .. "}")
    end
    
    if document.metadata.github then
        table.insert(latex, "\\social[github]{" .. escape_latex(document.metadata.github) .. "}")
    end
    
    table.insert(latex, "\\begin{document}")
    table.insert(latex, "\\makecvtitle")
    
    -- Main content
    for _, section in ipairs(document.sections) do
        table.insert(latex, render_section(section))
    end
    
    table.insert(latex, "\\end{document}")
    
    return table.concat(latex, "\n")
end

function template.render_section(section)
    local content = {}
    
    -- Section heading
    local section_title = escape_latex(section.title)
    table.insert(content, "\\section{" .. section_title .. "}")
    
    -- Section content
    for _, block in ipairs(section.blocks) do
        table.insert(content, render_block(block))
    end
    
    return table.concat(content, "\n")
end

function template.render_block(block)
    if block.type == "text" then
        return escape_latex(block.content) .. "\n\n"
    elseif block.type == "experience" then
        return render_experience(block)
    elseif block.type == "education" then
        return render_education(block)
    elseif block.type == "skills" then
        return render_skills(block)
    elseif block.type == "list" then
        return render_list(block)
    elseif block.type == "heading" then
        return "\\textbf{" .. escape_latex(block.content) .. "}\n\n"
    else
        return escape_latex(block.content) .. "\n\n"
    end
end

function template.render_experience(block)
    local content = {}
    
    -- Company and position
    local company = block.company or ""
    local position = block.position or ""
    local location = block.location or ""
    local start_date = block.start_date or ""
    local end_date = block.end_date or ""
    
    table.insert(content, "\\cventry{" .. escape_latex(start_date .. " -- " .. end_date) .. "}{" .. escape_latex(position) .. "}{" .. escape_latex(company) .. "}{" .. escape_latex(location) .. "}{}{}")
    
    -- Description/achievements
    if block.description then
        table.insert(content, escape_latex(block.description))
    end
    
    -- Bullet points for achievements
    if block.achievements and #block.achievements > 0 then
        for _, achievement in ipairs(block.achievements) do
            table.insert(content, "\\item " .. escape_latex(achievement))
        end
    end
    
    return table.concat(content, "\n") .. "\n\n"
end

function template.render_education(block)
    local content = {}
    
    local institution = block.institution or ""
    local degree = block.degree or ""
    local location = block.location or ""
    local start_date = block.start_date or ""
    local end_date = block.end_date or ""
    local gpa = block.gpa or ""
    
    table.insert(content, "\\cventry{" .. escape_latex(start_date .. " -- " .. end_date) .. "}{" .. escape_latex(degree) .. "}{" .. escape_latex(institution) .. "}{" .. escape_latex(location) .. "}{" .. escape_latex(gpa) .. "}{}")
    
    if block.details then
        table.insert(content, escape_latex(block.details))
    end
    
    return table.concat(content, "\n") .. "\n\n"
end

function template.render_skills(block)
    local content = {}
    
    if block.skill_categories then
        for category, skills in pairs(block.skill_categories) do
            table.insert(content, "\\textbf{" .. escape_latex(category) .. "}: " .. escape_latex(table.concat(skills, ", ")) .. "\\\\")
        end
    elseif block.skills then
        table.insert(content, escape_latex(table.concat(block.skills, ", ")))
    end
    
    return table.concat(content, "\n") .. "\n\n"
end

function template.render_list(block)
    local content = {}
    
    table.insert(content, "\\begin{itemize}")
    
    for _, item in ipairs(block.items or {}) do
        table.insert(content, "\\item " .. escape_latex(item))
    end
    
    table.insert(content, "\\end{itemize}")
    
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
