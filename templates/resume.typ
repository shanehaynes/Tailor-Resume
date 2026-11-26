// Renders a resolved resume (docs/decisions/2026-10-04-resolved-selection.md).
// Knows nothing of the ledger. Input: --input resolved=/path/from/repo/root.yaml
// Layout levers come from `layout:`; everything else here is the template's
// fixed look (reference/measurements.md).

#let data = yaml(sys.inputs.at("resolved", default: "/build/resolved.yaml"))
#let L = data.at("layout", default: (:))
#let lv(key, default) = L.at(key, default: default)

// Levers (pt unless noted). Defaults: reference/measurements.md.
#let size = lv("font_size", 10.5) * 1pt
#let leading = lv("leading", 2.7) * 1pt         // between lines of one paragraph
#let bullet-gap = lv("bullet_gap", 0) * 1pt     // extra between bullets
#let role-gap = lv("role_gap", 1) * 1pt         // extra between a title line and its first bullet
#let entry-gap = lv("entry_gap", 6) * 1pt       // extra between orgs and between roles
#let section-gap = lv("section_gap", 10) * 1pt  // extra before a section heading
#let line-gap = lv("line_gap", 1) * 1pt         // extra between additional-information lines

// Fixed geometry.
#let inset = 6pt          // name, headings, bullets, and lines sit 6pt inside the margin
#let hang = 20pt          // bullet glyph -> bullet text
#let rule = 0.7pt
#let small = size * 8.5 / 10.5
#let note = size * 9 / 10.5

#set document(title: data.contact.name + " - Resume", author: data.contact.name, date: none)
#set page(paper: "us-letter", margin: (
  x: lv("margin_x", 0.6) * 1in,
  top: lv("margin_top", 0.6458) * 1in,
  bottom: lv("margin_bottom", 0.5) * 1in,
))
#set text(font: "Carlito", size: size, ligatures: false, hyphenate: false, fallback: false,
          kerning: false, lang: "en", top-edge: "ascender", bottom-edge: "descender")
#set par(justify: false, leading: leading, spacing: 0pt, linebreaks: "simple")
#set block(spacing: 0pt)
#set smartquote(enabled: false)
#let link-color = rgb(26, 13, 171)  // link blue
#show link: it => text(fill: link-color, underline(offset: 1.5pt, stroke: 0.5pt + link-color, it))
// Never break inside a hyphenated word ("cross-dock"): a split keyword
// defeats exact-match ATS search, the same reason hyphenation is off.
#show regex("\w+(-\w+)+"): it => box(it)

// Text with linked substrings: links: [{text, url}], in order of appearance.
#let rich(s, links) = {
  if links == none { return s }
  let out = ()
  let rest = s
  for l in links {
    let i = rest.position(l.text)
    assert(i != none, message: "link text not in line: " + l.text)
    out.push(rest.slice(0, i))
    out.push(link(l.url, l.text))
    rest = rest.slice(i + l.text.len())
  }
  out.push(rest)
  out.join()
}

// Marks for the fit checker (rc/fit.py): page position of each bullet's or
// line's start (top of first line) and end (bottom of last line).
#let mark(id, edge, kind: "bullet") = context {
  let p = here().position()
  [#metadata((id: id, kind: kind, edge: edge, page: p.page, x: p.x.pt(), y: p.y.pt()))<rc-mark>]
}

// Faux small caps: first letter of each word full size, the rest smaller.
#let caps(s) = upper(s).split(" ").map(w => [#w.first()#text(size: small, w.slice(1))]).join(" ")

#let heading(s) = block(inset: (x: inset), width: 100%, {
  caps(s)
  v(0.6pt)
  line(length: 100%, stroke: rule)
  v(5.6pt)
})

#let bullet(b) = block(inset: (x: inset), width: 100%, grid(
  columns: (hang, 1fr),
  text(size: note, baseline: size * 0.06, "•"),
  { mark(b.id, "start"); rich(b.text, b.at("links", default: none)); mark(b.id, "end") },
))

#let bullets(bs) = {
  for (i, b) in bs.enumerate() {
    if i > 0 { v(leading + bullet-gap) }
    bullet(b)
  }
}

#let row(left, right) = grid(columns: (1fr, auto), column-gutter: 8pt, left, right)

// detail: a string renders inline ("Title: detail"); a list renders the title
// alone, then one line per item (the two-line official degree).
#let role(r, rid) = {
  let detail = r.at("detail", default: none)
  let dates = strong(r.at("dates", default: ""))
  if type(detail) == str {
    row([#mark(rid, "start", kind: "title")#strong(r.title): #detail#mark(rid, "end", kind: "title")], dates)
  } else {
    row([#mark(rid, "start", kind: "title")#strong(r.title)#mark(rid, "end", kind: "title")], dates)
    for l in (if detail == none { () } else { detail }) { v(leading); block(l) }
  }
  let bs = r.at("bullets", default: ())
  if bs.len() > 0 { v(leading + role-gap); bullets(bs) }
}

#let entry(e) = {
  let eid = e.at("ref", default: e.org)
  let desc = e.at("descriptor", default: none)
  let left = [#strong(upper(e.org))#if desc != none [ #text(size: note, weight: "bold", style: "italic", desc)]]
  row(left, strong(e.at("location", default: "")))
  for (i, r) in e.roles.enumerate() {
    v(leading + if i > 0 { entry-gap } else { 0pt })
    role(r, eid + ":title" + str(i))
  }
}

#let section(s, first) = {
  if not first { v(leading + section-gap) }
  heading(s.heading)
  for (i, e) in s.at("entries", default: ()).enumerate() {
    v(if i > 0 { leading + entry-gap } else { 2pt })
    entry(e)
  }
  bullets(s.at("bullets", default: ()))
  for (i, l) in s.at("lines", default: ()).enumerate() {
    if i > 0 { v(leading + line-gap) }
    block(inset: (x: inset), width: 100%)[#mark(l.id, "start", kind: "line")#strong(l.label): #rich(l.text, l.at("links", default: none))#mark(l.id, "end", kind: "line")]
  }
}

// --- document ---------------------------------------------------------------
#let mx = lv("margin_x", 0.6) * 72
#metadata((
  page_width: 612, page_height: 792, margin_x: mx,
  margin_top: lv("margin_top", 0.6458) * 72, margin_bottom: lv("margin_bottom", 0.5) * 72,
  text_right: 612 - mx - inset.pt(),
))<rc-geometry>
#block(inset: (x: inset), {
  text(size: size * 18 / 10.5, weight: "bold", upper(data.contact.name))
  v(2.1pt)
  data.contact.items.map(it => rich(it.text, it.at("links", default: none))).join(" | ")
})
#v(12.7pt)
#for (i, s) in data.sections.enumerate() { section(s, i == 0) }
