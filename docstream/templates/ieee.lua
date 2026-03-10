-- Pandoc Lua custom writer: IEEE two-column conference format
-- IEEEtran class, two-column layout

local function escape(text)
    if not text then return "" end
    text = text:gsub("\\", "\\textbackslash{}")
    text = text:gsub("%%", "\\%%")
    text = text:gsub("%$", "\\$")
    text = text:gsub("&",  "\\&")
    text = text:gsub("#",  "\\#")
    text = text:gsub("_",  "\\_")
    text = text:gsub("{",  "\\{")
    text = text:gsub("}",  "\\}")
    text = text:gsub("~",  "\\textasciitilde{}")
    text = text:gsub("%^", "\\^{}")
    return text
end

local function write_inlines(inlines)
    local parts = {}
    for _, il in ipairs(inlines) do
        if     il.t == "Str"       then table.insert(parts, escape(il.c))
        elseif il.t == "Space"     then table.insert(parts, " ")
        elseif il.t == "SoftBreak" then table.insert(parts, " ")
        elseif il.t == "LineBreak" then table.insert(parts, "\\\\\n")
        elseif il.t == "Strong"    then table.insert(parts, "\\textbf{" .. write_inlines(il.c) .. "}")
        elseif il.t == "Emph"      then table.insert(parts, "\\emph{"   .. write_inlines(il.c) .. "}")
        elseif il.t == "Code"      then table.insert(parts, "\\texttt{" .. escape(il.c[2])    .. "}")
        elseif type(il.c) == "string" then table.insert(parts, escape(il.c))
        end
    end
    return table.concat(parts)
end

local function write_block(block)
    if block.t == "Header" then
        local lvl  = block.c[1]
        local text = write_inlines(block.c[3])
        if     lvl == 1 then return "\\section{"       .. text .. "}\n"
        elseif lvl == 2 then return "\\subsection{"    .. text .. "}\n"
        elseif lvl == 3 then return "\\subsubsection{" .. text .. "}\n"
        else                  return "\\paragraph{"    .. text .. "}\n"
        end
    elseif block.t == "Para" then
        return write_inlines(block.c) .. "\n\n"
    elseif block.t == "Plain" then
        return write_inlines(block.c) .. "\n"
    elseif block.t == "BlockQuote" then
        local inner = {}
        for _, b in ipairs(block.c) do table.insert(inner, write_block(b)) end
        return "\\begin{quote}\n" .. table.concat(inner) .. "\\end{quote}\n\n"
    elseif block.t == "CodeBlock" then
        return "\\begin{verbatim}\n" .. block.c[2] .. "\n\\end{verbatim}\n\n"
    elseif block.t == "BulletList" then
        local items = {"\\begin{itemize}"}
        for _, item in ipairs(block.c) do
            local blocks = {}
            for _, b in ipairs(item) do table.insert(blocks, write_block(b)) end
            table.insert(items, "\\item " .. table.concat(blocks))
        end
        table.insert(items, "\\end{itemize}\n")
        return table.concat(items, "\n")
    elseif block.t == "HorizontalRule" then
        return "\\hrule\n\n"
    else
        return ""
    end
end

function Writer(doc, opts)
    local out  = {}
    local meta = doc.meta

    table.insert(out, "\\documentclass[conference,10pt]{IEEEtran}")
    table.insert(out, "\\usepackage[T1]{fontenc}")
    table.insert(out, "\\usepackage{cite}")
    table.insert(out, "\\usepackage{amsmath,amssymb}")
    table.insert(out, "\\usepackage{graphicx}")
    table.insert(out, "\\usepackage{booktabs}")
    table.insert(out, "\\usepackage{microtype}")

    local title  = meta.title  and pandoc.utils.stringify(meta.title)  or ""
    local author = meta.author and pandoc.utils.stringify(meta.author) or ""

    if title  ~= "" then table.insert(out, "\\title{"  .. escape(title)  .. "}") end
    if author ~= "" then table.insert(out, "\\author{\\IEEEauthorblockN{" .. escape(author) .. "}}") end

    table.insert(out, "\\begin{document}")
    if title ~= "" then table.insert(out, "\\maketitle") end

    if meta.abstract then
        local abs_text = pandoc.utils.stringify(meta.abstract)
        table.insert(out, "\\begin{abstract}")
        table.insert(out, escape(abs_text))
        table.insert(out, "\\end{abstract}")
    end

    for _, block in ipairs(doc.blocks) do
        table.insert(out, write_block(block))
    end

    table.insert(out, "\\end{document}")
    return table.concat(out, "\n")
end
