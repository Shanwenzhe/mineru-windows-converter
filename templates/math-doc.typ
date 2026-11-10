// 数学文档通用模板（中文 + 公式）
// 用法：在文档开头写
//   #import "C:/Users/SHANWENZHE/.codex/templates/math-doc.typ": *
//   #show: doc.with(title: "标题", author: "作者")
// 或者把本文件复制到工作目录后用相对路径 import。

#let doc(title: none, author: none, date: datetime.today(), body) = {
  set document(title: if title != none { title } else { "" })
  set page(paper: "a4", margin: (x: 2.4cm, y: 2.5cm), numbering: "1")
  set text(
    font: ("New Computer Modern", "Noto Serif SC", "SimSun"),
    size: 11pt,
    lang: "zh",
    region: "cn",
  )
  set par(justify: true, leading: 0.85em, first-line-indent: (amount: 2em, all: true))
  show heading: set text(font: ("New Computer Modern", "Noto Sans SC", "SimHei"))
  show heading: set block(above: 1.4em, below: 0.9em)
  set heading(numbering: "1.1")
  show math.equation: set text(font: "New Computer Modern Math")
  set math.equation(numbering: "(1)")
  show raw: set text(font: ("Consolas", "Noto Sans SC"))

  if title != none {
    align(center)[
      #text(size: 18pt, weight: "bold", font: ("New Computer Modern", "Noto Sans SC"))[#title]
      #if author != none { v(0.4em); text(size: 11pt)[#author] }
      #v(0.2em)
      #text(size: 10pt, fill: luma(90))[#date.display("[year] 年 [month] 月 [day] 日")]
    ]
    v(1em)
  }
  body
}

// 定理类环境
#let _thmbox(kind, color) = (name: none, body) => block(
  width: 100%, inset: (x: 10pt, y: 8pt), radius: 3pt,
  stroke: (left: 2.5pt + color), fill: color.lighten(92%),
)[
  #set par(first-line-indent: 0em)
  #text(weight: "bold", font: ("New Computer Modern", "Noto Sans SC"))[#kind#if name != none [（#name）]]#h(0.6em)#body
]
#let definition = _thmbox("定义", rgb("#2b6cb0"))
#let theorem = _thmbox("定理", rgb("#c05621"))
#let lemma = _thmbox("引理", rgb("#c05621"))
#let example = _thmbox("例", rgb("#2f855a"))
#let remark = _thmbox("注", rgb("#718096"))
#let proof(body) = block(width: 100%)[
  #set par(first-line-indent: 0em)
  #text(style: "italic")[证明.]#h(0.5em)#body#h(1fr)$square$
]
