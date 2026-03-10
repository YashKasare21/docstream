-- Pandoc Lua custom writer: resume / CV template
-- article class, compact margins, no section numbers

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
    if not inlines then return "" end
    local parts = {}
    for _, il in ipairs(inlines) do
        if     il.t == "Str"          then table.insert(parts, escape(il.text or il.c or ""))
        elseif il.t == "Space"        then table.insert(parts, " ")
        elseif il.t == "SoftBreak"    then table.insert(parts, " ")
        elseif il.t == "LineBreak"    then table.insert(parts, "\\\\\n")
        elseif il.t == "Strong"       then table.insert(parts, "\\textbf{" .. write_inlines(il.content or il.c) .. "}")
        elseif il.t == "Emph"         then table.insert(parts, "\\emph{"   .. write_inlines(il.content or il.c) .. "}")
        elseif il.t == "Code"         then
            local text = il.text or (type(il.c) == "table" and il.c[2]) or tostring(il.c or "")
            table.insert(parts, "\\texttt{" .. escape(text) .. "}")
        elseif il.t == "Math"         then
            local text  = il.text or (type(il.c) == "table" and il.c[2]) or ""
            local mtype = il.mathtype or (type(il.c) == "table" and il.c[1]) or ""
            if (type(mtype) == "table" and mtype.t == "DisplayMath") or mtype == "DisplayMath" then
                table.insert(parts, "\\[" .. text .. "\\]")
            else
                table.insert(parts, "$" .. text .. "$")
            end
        elseif il.t == "Link"         then
            local inls   = il.content or (type(il.c) == "table" and il.c[2]) or {}
            local target = il.target  or (type(il.c) == "table" and il.c[3]) or {}
            local url    = type(target) == "table" and target[1] or (type(target) == "string" and target) or ""
            local txt    = write_inlines(inls)
            if txt ~= "" then table.insert(parts, txt)
            else table.insert(parts, escape(url)) end
        elseif il.t == "Cite"         then
            local inls = il.content or (type(il.c) == "table" and il.c[2]) or {}
            table.insert(parts, write_inlines(inls))
        elseif il.t == "Quoted"       then
            local inls = il.content or (type(il.c) == "table" and il.c[2]) or {}
            table.insert(parts, "``" .. write_inlines(inls) .. "''")
        elseif il.t == "Superscript"  then table.insert(parts, "\\textsuperscript{" .. write_inlines(il.content or il.c) .. "}")
        elseif il.t == "Subscript"    then table.insert(parts, "\\textsubscript{" .. write_inlines(il.content or il.c) .. "}")
        elseif il.t == "Strikeout"    then table.insert(parts, write_inlines(il.content or il.c))
        elseif il.t == "SmallCaps"    then table.insert(parts, "\\textsc{" .. write_inlines(il.content or il.c) .. "}")
        elseif il.t == "Span"         then
            local inls = il.content or (type(il.c) == "table" and il.c[2]) or {}
            table.insert(parts, write_inlines(inls))
        elseif il.t == "RawInline"    then
            local fmt  = il.format or (type(il.c) == "table" and il.c[1]) or ""
            local text = il.text   or (type(il.c) == "table" and il.c[2]) or ""
            if fmt == "tex" or fmt == "latex" then table.insert(parts, text) end
        elseif il.t == "Note"         then -- skip footnotes
        elseif il.t == "Image"        then -- skip inline images
        else
            if type(il.c) == "string" then table.insert(parts, escape(il.c))
            elseif type(il.c) == "table" then
                local ok, res = pcall(write_inlines, il.c)
                if ok and res ~= "" then table.insert(parts, res) end
            end
        end
    end
    return table.concat(parts)
end

local function write_block(block)
    if block.t == "Header" then
        local lvl  = block.c[1]
        local text = write_inlines(block.c[3])
        -- No section numbers for resume
        if     lvl == 1 then return "\\section*{"    .. text .. "}\n\\hrule\\vspace{2pt}\n"
        elseif lvl == 2 then return "\\subsection*{" .. text .. "}\n"
        else                  return "\\subsubsection*{" .. text .. "}\n"
        end
    elseif block.t == "Para" then
        return write_inlines(block.c) .. "\n\n"
    elseif block.t == "Plain" then
        return write_inlines(block.c) .. "\n"
    elseif block.t == "BlockQuote" then
        local inner = {}
        for _, b in ipairs(block.c) do table.insert(inner, write_block(b)) end
        return table.concat(inner)
    elseif block.t == "CodeBlock" then
        return "\\begin{verbatim}\n" .. block.c[2] .. "\n\\end{verbatim}\n\n"
    elseif block.t == "BulletList" then
        local items = {"\\begin{itemize}\\setlength{\\itemsep}{0pt}"}
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

    table.insert(out, "\\documentclass[10pt,a4paper]{article}")
    table.insert(out, "\\usepackage[top=0.6in,bottom=0.6in,left=0.75in,right=0.75in]{geometry}")
    table.insert(out, "\\usepackage[T1]{fontenc}")
    table.insert(out, "\\usepackage{lmodern}")
    table.insert(out, "\\usepackage{enumitem}")
    table.insert(out, "\\usepackage{hyperref}")
    table.insert(out, "\\usepackage{microtype}")
    table.insert(out, "\\setlength{\\parindent}{0pt}")
    table.insert(out, "\\pagestyle{empty}")

    local title  = meta.title  and pandoc.utils.stringify(meta.title)  or ""
    local author = meta.author and pandoc.utils.stringify(meta.author) or ""

    table.insert(out, "\\begin{document}")

    if author ~= "" then
        table.insert(out, "{\\Large\\bfseries " .. escape(author) .. "}\\\\[4pt]")
    elseif title ~= "" then
        table.insert(out, "{\\Large\\bfseries " .. escape(title)  .. "}\\\\[4pt]")
    end

    for _, block in ipairs(doc.blocks) do
        table.insert(out, write_block(block))
    end

    table.insert(out, "\\end{document}")
    return table.concat(out, "\n")
end
