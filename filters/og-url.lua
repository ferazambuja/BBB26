-- Inject og:url meta tag from site-url + input file path
function Meta(meta)
  local base = "https://ferazambuja.github.io/BBB26/"
  local input = quarto.doc.input_file
  if input then
    local page = input:match("([^/]+)$"):gsub("%.qmd$", ".html")
    if page == "index.html" then
      page = ""
    end
    local url = base .. page
    local raw_block = pandoc.RawBlock("html",
      '<meta property="og:url" content="' .. url .. '">')
    local header = meta["header-includes"]
    if header == nil then
      meta["header-includes"] = pandoc.MetaBlocks({raw_block})
    else
      header[#header + 1] = raw_block
    end
  end
  return meta
end
