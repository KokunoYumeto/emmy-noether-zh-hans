# Build

The source archive contains `reader.tex`, the six pinned Noto fonts, three
ToUnicode CMaps, and the exact r10b build/accessibility scripts. Compile the
body with XeLaTeX using the frozen scripts and then run `make_reader.py` to
prepend the DOI cover. The release receipt records the exact Python, pypdf,
XeLaTeX, Poppler, and CMap identities used for version 1.0.0.

The primary release reader is not produced by editing the 424-page body. It is
one cover page followed by that body, with all 424 body content streams and page
boxes checked for equality.
