# Build the reader

`make_reader.py` is the public, self-contained build entry point. It reads only
this `source` directory: the pinned `reader.tex`, `cover.tex`, six bundled Noto
font files, and three bundled ToUnicode CMaps. It does not read the original
producer workspace, frozen handoff, or any machine-local project path.

Requirements:

- Python 3.11 or newer with `pypdf` 6.x;
- XeLaTeX with the packages named by `reader.tex` and `cover.tex`;
- Poppler commands `pdffonts`, `pdftotext`, and `pdftoppm` on `PATH`.

From the repository root, run:

```powershell
python source/make_reader.py `
  --output build/00_NOETHER_zh-Hans_COMPLETE_READER.pdf `
  --receipt build/reader.build.json `
  --qa-dir build/qa
```

On POSIX shells, use the same arguments on one line or replace the PowerShell
continuation marks with backslashes.

The script fails closed. It verifies every source/font/CMap hash; stages only
three exact font-family declarations so all text fonts resolve to the bundled
files; performs three serial XeLaTeX passes for the 424-page body; injects
missing ToUnicode maps only for the six allowlisted classic-math subsets;
requires two byte-identical injection runs; and checks that content streams,
page boxes, annotations, destinations, outlines, and embedded font programs are
preserved. It then compiles the one-page DOI cover, prepends it with the
body-clone/insert method that preserves links and destinations, and requires two
byte-identical merges. Both Poppler and pypdf must report zero disallowed C0,
U+FFFD, and NUL extraction characters.

The result is a 425-page PDF plus a JSON build receipt. With `--qa-dir`, the
script also renders the cover, first body page, and final body page at 180 dpi;
open those three PNGs before distributing a locally rebuilt copy. Existing
outputs are not overwritten unless `--force` is supplied. Scratch is confined
to `.noether-zh-work` beside the requested output and removed only after an
owner-marker safety check; an already-existing scratch directory is never
overwritten or deleted. A failed build preserves that scratch directory for
diagnosis; inspect it, then remove it before retrying.

The published version 1.0.0 release PDF remains the hash-pinned archival
artifact. A rebuild is expected to preserve the verified logical and visual
content, but byte identity across different XeLaTeX, font-engine, Poppler, or
pypdf versions is not promised; the receipt records the exact tool versions and
output hashes.
