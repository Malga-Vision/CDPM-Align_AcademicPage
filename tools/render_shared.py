"""Render the blocks every MaLGa project page shares: "Related work from our lab" and the footer.

The blocks live between marker comments in index.html:
    <!-- RELATED:START --> ... <!-- RELATED:END -->
    <!-- FOOTER:START -->  ... <!-- FOOTER:END -->

Usage:
    python tools/render_shared.py path/to/index.html --page-repo <Repo> [--code-repo <Repo>]

--page-repo is this page's repository name in the Malga-Vision org; it selects the
"you are here" entry of the related list and the "page source" link in the footer.
Edit tools/projects.json to add a new paper, then re-run on every page.
"""

import argparse
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "https://malga-vision.github.io"
GITHUB = "https://github.com"
TEMPLATE_REPO = "malga-academic-page-template"


def external(href, text):
    return f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer">{html.escape(text)}</a>'


def render_related(projects, org, page_repo):
    items = []
    for p in projects:
        title = html.escape(p["title"])
        venue = html.escape(p["venue"])
        if p["page_repo"] == page_repo:
            items.append(
                '          <li aria-current="page">\n'
                f'            <span class="related__venue">{venue}</span>\n'
                f'            <span class="related__title">{title}</span><span class="related__here">this page</span>\n'
                "          </li>"
            )
            continue
        links = []
        if p.get("code_repo"):
            links.append(f'<a href="{GITHUB}/{org}/{p["code_repo"]}" target="_blank" rel="noopener noreferrer">Code</a>')
        extra = f"\n            <p>{' '.join(links)}</p>" if links else ""
        items.append(
            "          <li>\n"
            f'            <span class="related__venue">{venue}</span>\n'
            f'            <a class="related__title" href="{SITE}/{p["page_repo"]}/">{title}</a>{extra}\n'
            "          </li>"
        )
    return (
        '    <section class="section" id="related">\n'
        '      <div class="wrap">\n'
        '        <h2 class="section__title">Related work from our lab</h2>\n'
        '        <ol class="related">\n'
        + "\n".join(items)
        + "\n        </ol>\n      </div>\n    </section>"
    )


def render_footer(org, page_repo, code_repo):
    paper_links = []
    if code_repo:
        paper_links.append(f"<li>{external(f'{GITHUB}/{org}/{code_repo}', 'Code')}</li>")
    paper_links.append('<li><a href="#cite">How to cite</a></li>')
    paper_links.append(f"<li>{external(f'{GITHUB}/{org}/{page_repo}', 'Source of this page')}</li>")
    joined = "\n            ".join(paper_links)
    return f"""  <footer class="site-footer">
    <div class="wrap">
      <div class="site-footer__grid">
        <div>
          <a class="site-footer__logo" href="https://malga.unige.it/" target="_blank" rel="noopener noreferrer">
            <img src="static/malga/img/malga-unige-white.svg" width="236" height="74" alt="MaLGa and University of Genoa">
          </a>
          <p>Machine Learning Genoa Center (MaLGa)<br>DIBRIS, University of Genoa, Italy</p>
        </div>
        <div>
          <h2>This paper</h2>
          <ul>
            {joined}
          </ul>
        </div>
        <div>
          <h2>MaLGa</h2>
          <ul>
            <li>{external('https://malga.unige.it/', 'malga.unige.it')}</li>
            <li>{external(f'{GITHUB}/{org}', f'{org} on GitHub')}</li>
          </ul>
        </div>
      </div>
      <div class="site-footer__legal">
        <span>&copy; The authors. Figures and text are from the paper.</span>
        <span>Built with the {external(f'{GITHUB}/{org}/{TEMPLATE_REPO}', 'MaLGa academic page template')}.</span>
      </div>
    </div>
  </footer>"""


def replace_block(text, name, block):
    pattern = re.compile(rf"<!-- {name}:START -->.*?<!-- {name}:END -->", re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker <!-- {name}:START --> ... <!-- {name}:END --> not found")
    return pattern.sub(lambda _: f"<!-- {name}:START -->\n{block}\n<!-- {name}:END -->", text, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("index", type=Path)
    parser.add_argument("--page-repo", required=True)
    parser.add_argument("--code-repo")
    parser.add_argument("--projects", type=Path, default=HERE / "projects.json")
    args = parser.parse_args()

    data = json.loads(args.projects.read_text(encoding="utf-8"))
    text = args.index.read_text(encoding="utf-8")
    text = replace_block(text, "RELATED", render_related(data["projects"], data["org"], args.page_repo))
    text = replace_block(text, "FOOTER", render_footer(data["org"], args.page_repo, args.code_repo))
    args.index.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {args.index}")


if __name__ == "__main__":
    main()
