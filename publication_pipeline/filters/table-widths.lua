-- ReportKit Pandoc filter: give every table an explicit column-width
-- fraction so the LaTeX writer emits wrapping `p{width}` columns instead of
-- plain, non-wrapping `l`/`c`/`r` columns.
--
-- Pandoc's Markdown readers (both the pipe-table and simple-table forms
-- used throughout ReportKit manuscripts) parse an unadorned table -- no
-- explicit `:---:` width syntax, no grid table -- with every column's
-- width left at the default "auto" value. The LaTeX writer then emits a
-- plain-alignment `longtable` column for each one. A plain column never
-- wraps: its width is the natural width of its widest, unbroken line of
-- text, so an ordinary full-sentence table cell (the house style in every
-- ReportKit book/report manuscript) reliably produces an overfull \hbox
-- once the summed column widths exceed the text width. This filter runs
-- after Pandoc's Markdown reader and before its LaTeX writer, so it only
-- ever sees the already-parsed table -- it has no way to read the
-- original Markdown's header-dash column widths back out, but it does not
-- need to: distributing width by each column's own widest rendered cell
-- (a stable, deterministic proxy for how much horizontal room that column
-- actually needs) reproduces a reasonable approximation of the same
-- intent and, unlike the default, always wraps instead of overflowing.

local MIN_FRACTION = 0.12

local function cell_text_length(cell)
  -- `pandoc.utils.stringify` flattens a cell's inline/block content to
  -- plain text; the longest line within a multi-line cell is what actually
  -- constrains the column, not the cell's total character count.
  local text = pandoc.utils.stringify(cell.contents)
  local longest = 0
  for line in (text .. "\n"):gmatch("([^\n]*)\n") do
    if #line > longest then
      longest = #line
    end
  end
  return longest
end

function Table(tbl)
  local ncols = #tbl.colspecs
  if ncols == 0 then
    return tbl
  end

  -- An unsized ("auto") column's width comes back from the Lua API as a
  -- bare `nil` in the colspec pair, not a `ColWidth` value; any non-nil
  -- second element means the author (or a grid table) already sized it.
  local already_sized = false
  for _, colspec in ipairs(tbl.colspecs) do
    if colspec[2] ~= nil then
      already_sized = true
      break
    end
  end
  if already_sized then
    -- Respect an author (or a grid table) that already specified widths.
    return tbl
  end

  local widest = {}
  for i = 1, ncols do
    widest[i] = 0
  end

  local function scan_row(row)
    for i, cell in ipairs(row.cells) do
      if i <= ncols then
        local length = cell_text_length(cell)
        if length > widest[i] then
          widest[i] = length
        end
      end
    end
  end

  for _, head_row in ipairs(tbl.head.rows) do
    scan_row(head_row)
  end
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      scan_row(row)
    end
  end
  for _, foot_row in ipairs(tbl.foot.rows) do
    scan_row(foot_row)
  end

  local total = 0
  for i = 1, ncols do
    if widest[i] == 0 then
      widest[i] = 1
    end
    total = total + widest[i]
  end

  -- Raw proportional fractions first, then lift anything under the
  -- minimum and renormalize so the fractions still sum to 1.0. A column
  -- with a short header ("Owner") should not be squeezed unreadably thin
  -- just because its neighbors hold full sentences.
  local fractions = {}
  for i = 1, ncols do
    fractions[i] = widest[i] / total
  end
  local lifted_total = 0
  for i = 1, ncols do
    if fractions[i] < MIN_FRACTION then
      fractions[i] = MIN_FRACTION
    end
    lifted_total = lifted_total + fractions[i]
  end
  for i = 1, ncols do
    fractions[i] = fractions[i] / lifted_total
  end

  for i, colspec in ipairs(tbl.colspecs) do
    tbl.colspecs[i] = { colspec[1], fractions[i] }
  end
  return tbl
end
