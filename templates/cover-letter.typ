// Renders a resolved cover letter (rc/cover.py). Same face, header, and pinned
// settings as resume.typ so the pair reads as one document set.
// Input: --input resolved=/path/from/repo/root.yaml

#let data = yaml(sys.inputs.at("resolved", default: "/build/cover.resolved.yaml"))
#let size = data.at("font_size", default: 11) * 1pt

#set document(title: data.contact.name + " - Cover Letter", author: data.contact.name, date: none)
#set page(paper: "us-letter", margin: (x: 1in, top: 0.75in, bottom: 0.75in))
#set text(font: "Carlito", size: size, ligatures: false, hyphenate: false, fallback: false,
          kerning: false, lang: "en", top-edge: "ascender", bottom-edge: "descender")
#set par(justify: false, leading: 0.42em, spacing: 0.95em, linebreaks: "simple")
#set smartquote(enabled: false)
#let link-color = rgb(26, 13, 171)
#show link: it => text(fill: link-color, underline(offset: 1.5pt, stroke: 0.5pt + link-color, it))
#show regex("\w+(-\w+)+"): it => box(it)

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

#text(size: size * 18 / 11, weight: "bold", upper(data.contact.name))
#v(-0.4em)
#text(size: size * 10.5 / 11, data.contact.items.map(it => rich(it.text, it.at("links", default: none))).join(" | "))
#v(0.6em)
#line(length: 100%, stroke: 0.7pt)
#v(0.8em)

#data.date

#for l in data.at("recipient", default: ()) [#l \ ]

#for p in data.paragraphs [
  #par(p)
]
