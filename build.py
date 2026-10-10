"""Build the resume pages and PDF from README.md.

Uses the Python packages of the active environment:
  - pypandoc_binary  Markdown -> HTML (ships its own pandoc binary)
  - weasyprint       HTML -> PDF

Run from the repository root:  python build.py   (or ./build.sh)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"
FOOTER = ROOT / "src" / "footer.md"
TEMP_HTML = ROOT / "resume_2_pdf.html"

OUTPUTS = {
    "resume": ROOT / "resume.html",
    "pdf": ROOT / "Ajay_Kumar_Dwivedi.pdf",
    "light": ROOT / "index.html",
    "dark": ROOT / "dark.html",
}


def require_packages():
    missing = []
    try:
        import pypandoc  # noqa: F401
    except ImportError:
        missing.append("pypandoc_binary")
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        missing.append("weasyprint")
    if missing:
        sys.exit(
            "Missing packages in the active environment: " + ", ".join(missing) + "\n"
            "Install them with:  pip install -r requirements-build.txt"
        )


def markdown_to_html(sources, css, out):
    import pypandoc

    print(f"Convert Markdown to {out.name} ...")
    pypandoc.convert_file(
        [str(p) for p in sources],
        "html",
        outputfile=str(out),
        extra_args=["-s", "-c", css],
        cworkdir=str(ROOT),
    )


def html_to_pdf(html, out):
    import weasyprint

    print(f"Convert temp Resume HTML to {out.name} ...")
    weasyprint.HTML(filename=str(html), base_url=str(ROOT)).write_pdf(str(out))


def main():
    require_packages()

    markdown_to_html([README], "css/design-resume.css", OUTPUTS["resume"])

    markdown_to_html([README], "css/design.css", TEMP_HTML)
    html_to_pdf(TEMP_HTML, OUTPUTS["pdf"])
    print("Removing temp Resume HTML")
    TEMP_HTML.unlink()

    markdown_to_html([README, FOOTER], "css/design-light.css", OUTPUTS["light"])
    markdown_to_html([README, FOOTER], "css/design-dark.css", OUTPUTS["dark"])

    print()
    print("Finish !")
    print("***************************************************")
    print('PDF written to "Ajay_Kumar_Dwivedi.pdf". Open "resume.html" to print it as well.')
    print("***************************************************")


if __name__ == "__main__":
    main()
