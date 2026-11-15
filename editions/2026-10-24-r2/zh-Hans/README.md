# 埃米·诺特数学著作集：简体中文版

收录第1—43篇论文、M. Deuring记录的1929/30年冬季学期《超复量代数》讲义、H. Kapferer论文及与E. Noether合作的补充、书目、短讯与书评目录以及参与编著的书籍目录。内容涵盖不变量、理想、域、代数与表示论，采用面向中国大陆读者的简体中文。

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

## 阅读与可编辑源文件

### 基本正文——425页

1. [阅读PDF](reader-edition/01-noether-zh-Hans-base.pdf)
2. [下载完整LaTeX正文](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/02-noether-zh-Hans-base.tex)
3. [下载完整排版源文件](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/03-noether-zh-Hans-base-sources.zip)

### 订正正文与编者注——430页

1. [阅读PDF](reader-edition/04-noether-zh-Hans-emendations.pdf)
2. [下载完整LaTeX正文](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/05-noether-zh-Hans-emendations.tex)
3. [下载完整排版源文件](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/06-noether-zh-Hans-emendations-sources.zip)

两种正文均包含上述范围，PDF书签可导航至全部43篇编号论文及后续部分。基本正文保留编者注所讨论的原刊读法；订正版另以编者注说明有关订正及依据。这些注释并非整部著作的穷尽式批判校本。

每个直接下载的LaTeX文件均含对应版本的完整正文。各ZIP包含同一正文、所需的Noto字体文件、字体署名和许可证、排版说明及脚本；排版使用XeLaTeX，并需安装说明中列出的系统字体和TeX包。直接下载的LaTeX文件须与包内的`fonts`目录放在一起。[SHA-256文件清单](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/07-SHA256SUMS.txt)

## 作者、翻译与出处

原作者为Emmy Noether及各篇署名的共同作者；讲义由M. Deuring记录。中文正文由AI翻译。早期制作方为Manuscript Typesetting Project / OpenAI Codex；现存出处资料不足以确定其准确模型。R9中文汇编及繁体字转换程序由OpenAI Codex——GPT-5.6 Sol，Ultra推理强度于2026-08-12制作；转换采用opencc-python-reimplemented 0.1.7的s2t配置。2026-10-23—2026-10-24由AI制作的订正与排版：OpenAI Codex——GPT-6 Astra，Ultra推理强度；2026-10-26至2026-10-27：Claude Opus 5.5（Anthropic）（公式已与依Noether印刷页面读出的德文本文核对）。这不表示出版者亲自翻译，亦不表示经过独立学术审阅。

本版继承[简体中文版v1.0.0（2026-08-14）](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/v1.0.0)的正文；其德文底本为ED0011/v047（2026-08-08）。早期中文文本见2026-06-12汇编，后续历史记录包括[v1.0.2](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/v1.0.2)与[v1.0.3](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/tag/v1.0.3)。原刊信息、署名与文献引用见正文。

## 权利

埃米·诺特于1935年去世，因此她的著作在欧盟以及保护期于作者去世后70年届满的所有地方均属公有领域。在美国，她于1931年或以后首次发表的论文自发表起95年内仍受保护（1931年的论文于2027年1月1日起不再受保护）。在发行者对AI完成的翻译、校正与排版享有权利的范围内，这些权利依[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.zh-hans)献入公有领域。M. Deuring记录的讲义、H. Kapferer的论文以及所列合著者的贡献不在本声明范围内；其权利仍归其作者或继承人。

早期真实权利声明仍在其实际授权范围内适用；所附Noto字体适用SIL Open Font License 1.1。

[作者、出处与权利](reader-edition/RIGHTS.md) · [早期权利声明](https://github.com/KokunoYumeto/emmy-noether-zh-hans/blob/main/editions/2026-10-24-r2/zh-Hans/reader-edition/NOTICE_HISTORIQUE.md) · [历史版本](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases)


## 中文译本与程序

一个中文译本，提供简体正文和程序生成的繁体字形式；两种字形均持续维护。[方法、作者模型与日期、可直接浏览的代码](https://github.com/KokunoYumeto/emmy-noether-zh-hans/blob/main/methods/chinese-script-2026-10-24-r2/README.md)。完整源文件ZIP中的`code/`也包含转换函数、指定版本重建设置及两种字形的排版脚本。[单独下载代码](https://github.com/KokunoYumeto/emmy-noether-zh-hans/releases/download/noether-zh-Hans-2026-11-15-r2/08-noether-chinese-script-code-2026-10-24-r2.zip)。
