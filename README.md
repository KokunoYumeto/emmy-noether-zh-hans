# 埃米·诺特数学著作集：简体中文版

本仓库是埃米·诺特（Emmy Noether，1882—1935）数学著作集的简体中文译本，收录第1—43篇论文、M. Deuring记录的1929/30年冬季学期《超复量代数》讲义、H. Kapferer的论文及其与E. Noether合写的补充，以及书目、短讯与书评目录和参与编著的书籍目录。内容涵盖不变量、理想、域、代数与表示论，采用面向中国大陆读者的简体中文，以PDF和可编辑的LaTeX发布。

[**阅读基本正文PDF（426页）**](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/01-noether-zh-Hans-base.pdf) · [订正正文PDF（431页）](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/04-noether-zh-Hans-emendations.pdf) · [2026年11月15日版（r2）的全部文件](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/noether-zh-Hans-2026-11-15-r2)

## How this was made: AI's failure modes, and what we do about them

Everything here was produced by AI. The translation was made in a first pass mostly by GPT-5.6 Sol (OpenAI Codex,
reasoning effort ultra), by the user's account (July and August 2026). Its formulas were then brought into line with the German text, which Claude Opus 5.5 at
effort max compared page by page with Noether's printed originals (785 page checks, 26 October 2026), in automatic and
hand rounds by Claude Opus 5.5 at effort max (26-27 October; 2,570 lines in the last hand round), against the known
failures of AI translation of mathematics: renamed letters, formulas changed or dropped, statements narrowed, passages
reworked or garbled, sentences and displays dropped, broken layout. Every change passes a release filter, and every PDF
is checked for lines running into the margin (Claude Opus 5.5 at effort high, 15 November). No person has reviewed the
translation. What was done in each round, the measured figures and what is still open:
[How this was made](https://github.com/KokunoYumeto/emmy-noether#how-this-was-made-ais-failure-modes-and-what-we-do-about-them).

## 制作方式

中文正文由AI翻译，译者为OpenAI Codex模型（未记录具体是哪个模型）。本版正文继承2026年8月14日的简体中文版v1.0.0，其德文底本为AI依原刊转录的德文文本ED0011/v047（2026-08-08）。R9中文汇编及繁体字转换程序由OpenAI Codex——GPT-5.6 Sol（Ultra推理强度）于2026-08-12制作，转换采用opencc-python-reimplemented 0.1.7的s2t配置。本版的订正与排版由AI制作：2026-10-23至2026-10-24为OpenAI Codex——GPT-6 Astra（Ultra推理强度）；2026-10-26至2026-10-27为Claude Opus 5.5（Anthropic，max推理强度），并将公式与依Noether印刷页面读出的德文本文核对一致。

## 现状

上述著作均已收录。译文未经人工审阅，可能仍有错误。第24、31、32、34篇（以及第35、40篇的部分内容）沿用早期英译本，其公式在若干处与德文本文不同；第38篇中的哥特体𝔭可能印作p；在译文自行转述的段落中，个别公式可能仍沿用早期德文转录。欢迎通过[GitHub issues](https://github.com/KokunoYumeto/emmy-noether-zh-hans/issues)报告错误和提出修改意见。

## 内容与阅读方式

本版提供两种正文，每种都有PDF、单个LaTeX文件和排版源文件ZIP：

| 正文 | PDF | LaTeX | 源文件 |
|---|---|---|---|
| 基本正文：保留原刊读法，并在编者注中讨论有关读法 | [PDF，426页](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/01-noether-zh-Hans-base.pdf) | [LaTeX](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/02-noether-zh-Hans-base.tex) | [ZIP](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/03-noether-zh-Hans-base-sources.zip) |
| 订正正文：采用编者订正，每处订正均以编者注说明 | [PDF，431页](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/04-noether-zh-Hans-emendations.pdf) | [LaTeX](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/05-noether-zh-Hans-emendations.tex) | [ZIP](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/06-noether-zh-Hans-emendations-sources.zip) |

[SHA-256文件清单](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/07-SHA256SUMS.txt)。同样的文件也在[`editions/2026-10-24-r2/zh-Hans/reader-edition/`](editions/2026-10-24-r2/zh-Hans/reader-edition/)中。

PDF书签可导航至全部43篇编号论文及后续部分。每个LaTeX文件均含对应版本的完整正文。各ZIP包含同一正文、所需的Noto字体文件、字体署名和许可证、排版说明及脚本；排版使用XeLaTeX，并需安装说明中列出的系统字体和TeX包。直接下载的LaTeX文件须与包内的`fonts`目录放在一起。繁体字形式版由同一转换程序（[08-noether-chinese-script-code-2026-10-24-r2.zip](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/08-noether-chinese-script-code-2026-10-24-r2.zip)）从简体文本生成。

2026年8月的简体中文版v1.0.0至v1.0.3可在[GitHub发布页](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases)下载。德文本文、繁体字形式版、其他语种版本以及各版之间的已知差异见[中央页面](https://kokunoyumeto.github.io/emmy-noether/)。

## 作者与出处

- 原作者为Emmy Noether及各篇署名的共同作者：Werner Schmeidler（第17篇）、R. Brauer（第32篇）、R. Brauer与H. Hasse（第38篇）。1929/30年讲义由M. Deuring记录。第45号著作为H. Kapferer的论文，附有与E. Noether合写的补充。原刊信息、署名与文献引用见正文。
- 底本：[简体中文版v1.0.0（2026-08-14）](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/v1.0.0)，Manuscript Typesetting Project / OpenAI Codex；其德文底本为ED0011/v047（2026-08-08）。第1篇至第19篇第6节的早期中文文本见2026-06-12法文与简体中文汇编；后续版本为[v1.0.2](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/v1.0.2)和[v1.0.3](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/v1.0.3)。公式依据与原刊逐页核对的德文本文（[noether-de-2026-10-26](https://github.com/KokunoYumeto/modern-latex-manuscripts/releases/tag/noether-de-2026-10-26)）。
- [作者、出处与权利](editions/2026-10-24-r2/zh-Hans/reader-edition/RIGHTS.md) · [早期权利声明](editions/2026-10-24-r2/zh-Hans/reader-edition/NOTICE_HISTORIQUE.md)

## 权利

埃米·诺特于1935年去世，因此她的著作在欧盟以及保护期于作者去世后70年届满的所有地方均属公有领域。在美国，她于1931年或以后首次发表的论文自发表起95年内仍受保护（1931年的论文于2027年1月1日起不再受保护）。在发行者对AI完成的翻译、校正与排版享有权利的范围内，这些权利依[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.zh-hans)献入公有领域。M. Deuring记录的讲义、H. Kapferer的论文以及所列合著者的贡献不在本声明范围内；其权利仍归其作者或继承人。