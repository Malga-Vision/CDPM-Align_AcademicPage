"""Security and integrity checks for a MaLGa project page. Standard library only.

Run from the repository root:
    python tools/page_guard.py

The GitHub Pages workflow runs it before every deploy, so a page that fails is not
published. It looks for the usual ways a static academic page gets abused:

  * script injection: inline or third-party scripts, event-handler attributes,
    javascript: URLs, iframes, forms, <base>, meta refresh, a weakened CSP;
  * SEO spam: links to domains outside tools/allowed-domains.txt, links hidden
    from readers, doorway HTML pages, spam keywords, foreign URLs in sitemap.xml;
  * broken or oversized assets.

Exit code 0 when every check passes, 1 otherwise.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path.cwd()
TOOLS = Path(__file__).resolve().parent
MAX_FILE_MB = 25
WARN_FILE_MB = 15
ALLOWED_HTML = {"index.html", "404.html"}
ALLOWED_HTML_RE = re.compile(r"^google[0-9a-f]{16}\.html$")  # Search Console file verification
SKIP_DIRS = {".git", "_site", "node_modules", "tools", ".github"}
REQUIRED_CSP = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": "'self'",
    "object-src": "'none'",
    "base-uri": "'none'",
    "form-action": "'none'",
}
FORBIDDEN_TAGS = {"iframe", "object", "embed", "form", "base", "frame", "frameset", "applet", "portal"}
SPAM_WORDS = re.compile(
    r"\b(casino|gacor|slot\s?online|judi|togel|poker\s?online|sbobet|viagra|cialis|payday\s?loan|"
    r"escort|replica\s?watches|crypto\s?giveaway|essay\s?writing\s?service|buy\s?followers)\b",
    re.I,
)
TEXT_SUFFIXES = {".html", ".css", ".js", ".txt", ".xml", ".json", ".md", ".svg"}


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load_allowlist():
    path = ROOT / "tools" / "allowed-domains.txt"
    if not path.exists():
        path = TOOLS / "allowed-domains.txt"
    domains = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            domains.add(line)
    return domains


def domain_allowed(host, allowlist):
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in allowlist)


class PageParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "use", "path", "circle", "rect"}

    def __init__(self, report, allowlist):
        super().__init__(convert_charrefs=True)
        self.r, self.allow = report, allowlist
        self.stack = []            # (tag, hidden)
        self.hidden_depth = 0
        self.first_meta_seen = []  # order of head elements
        self.csp = None
        self.in_script = None
        self.script_buf = []
        self.local_refs = set()
        self.ids = set()
        self.fragments = set()

    # -- helpers
    def check_url(self, url, attr, tag):
        url = url.strip()
        if not url:
            return
        low = url.lower().replace("\t", "").replace("\n", "")
        if low.startswith(("javascript:", "vbscript:", "data:text/html")):
            self.r.error(f"<{tag} {attr}> uses a script URL: {url[:60]}")
            return
        if low.startswith("data:"):
            if tag != "img":
                self.r.error(f"<{tag} {attr}> uses a data: URL")
            return
        if low.startswith(("mailto:", "tel:")):
            return
        if low.startswith("#"):
            self.fragments.add(url[1:])
            return
        parts = urlsplit(url)
        if parts.scheme in ("http", "https") or url.startswith("//"):
            if parts.scheme == "http":
                self.r.error(f"insecure http:// link: {url}")
            if not domain_allowed(parts.hostname or "", self.allow):
                self.r.error(f"<{tag} {attr}> points to a domain not in tools/allowed-domains.txt: {url}")
            return
        if parts.scheme:
            self.r.error(f"<{tag} {attr}> uses an unexpected scheme: {url[:60]}")
            return
        path = unquote(parts.path)
        if path and not path.startswith("/"):
            self.local_refs.add(path)

    # -- parser hooks
    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        hidden = "hidden" in a or a.get("aria-hidden") == "true" or tag == "template"
        if tag not in self.VOID:
            self.stack.append((tag, hidden))
            if hidden:
                self.hidden_depth += 1
        if "id" in a:
            self.ids.add(a["id"])

        if tag in FORBIDDEN_TAGS:
            self.r.error(f"<{tag}> is not allowed")
        if "style" in a:
            self.r.error(f'inline style attribute on <{tag}> (move it to a stylesheet): style="{a["style"][:50]}"')
        for k in a:
            if k.startswith("on"):
                self.r.error(f"event-handler attribute {k} on <{tag}>")
        if tag == "style":
            self.r.error("<style> element (use static/css/page.css instead)")

        if tag == "meta":
            self.first_meta_seen.append(a.get("http-equiv", a.get("charset") and "charset" or a.get("name", "")).lower())
            equiv = a.get("http-equiv", "").lower()
            if equiv == "refresh":
                self.r.error("<meta http-equiv=refresh> redirect")
            if equiv == "content-security-policy":
                self.csp = a.get("content", "")

        if tag == "script":
            stype = a.get("type", "").lower()
            if "src" in a:
                src = a["src"]
                if urlsplit(src).scheme or src.startswith("//"):
                    self.r.error(f"third-party script: {src}")
                else:
                    self.local_refs.add(unquote(urlsplit(src).path))
                self.in_script = "external"
            elif stype == "application/ld+json":
                self.in_script = "ld+json"
            else:
                self.r.error(f"inline <script type='{stype or 'text/javascript'}'> (only JSON-LD may be inline)")
                self.in_script = "inline"
            self.script_buf = []

        if tag == "link" and "stylesheet" in a.get("rel", "").lower():
            href = a.get("href", "")
            if urlsplit(href).scheme or href.startswith("//"):
                self.r.error(f"third-party stylesheet: {href}")

        for attr in ("href", "src", "poster", "action", "formaction", "data"):
            if attr in a and tag != "script":
                self.check_url(a[attr], attr, tag)
        if "srcset" in a:
            for cand in a["srcset"].split(","):
                self.check_url(cand.strip().split(" ")[0], "srcset", tag)

        if tag == "a":
            if self.hidden_depth:
                self.r.error(f"link inside hidden content: {a.get('href', '')}")
            if a.get("target") == "_blank" and "noopener" not in a.get("rel", ""):
                self.r.error(f"target=_blank without rel=noopener: {a.get('href', '')}")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID and self.stack and self.stack[-1][0] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_script:
            if self.in_script == "ld+json":
                try:
                    json.loads("".join(self.script_buf))
                except json.JSONDecodeError as exc:
                    self.r.error(f"JSON-LD does not parse: {exc}")
            self.in_script = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, hid in self.stack[i:]:
                    if hid:
                        self.hidden_depth -= 1
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.in_script:
            self.script_buf.append(data)


def check_csp(csp, r):
    if csp is None:
        r.error("missing <meta http-equiv=Content-Security-Policy>")
        return
    directives = {}
    for part in csp.split(";"):
        bits = part.split()
        if bits:
            directives[bits[0].lower()] = bits[1:]
    for name, value in REQUIRED_CSP.items():
        if directives.get(name) != [value]:
            r.error(f"CSP {name} must be exactly {value} (found: {' '.join(directives.get(name, ['<missing>']))})")
    for name, values in directives.items():
        for v in values:
            if v in ("'unsafe-inline'", "'unsafe-eval'", "*", "http:", "https:", "'unsafe-hashes'"):
                r.error(f"CSP {name} allows {v}")


def check_index(r, allowlist):
    index = ROOT / "index.html"
    if not index.exists():
        r.error("index.html not found (run from the repository root)")
        return
    text = index.read_text(encoding="utf-8")
    parser = PageParser(r, allowlist)
    parser.feed(text)
    parser.close()
    check_csp(parser.csp, r)
    if parser.first_meta_seen[:2] != ["charset", "content-security-policy"]:
        r.error("the CSP meta must come right after <meta charset> so it applies to everything below it")
    for ref in sorted(parser.local_refs):
        if not (ROOT / ref).exists():
            r.error(f"broken local reference: {ref}")
    for frag in sorted(parser.fragments):
        if frag and frag not in parser.ids:
            r.error(f"link to #{frag}, but no element has that id")
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', text)
    is_template = bool(canonical) and canonical.group(1).rstrip("/").endswith("/malga-academic-page-template")
    for marker in ("ACRONYM", "Paper title", "VENUE YEAR", "Same text as the visible answer", "malga-academic-page-template/#"):
        if marker in text and not is_template:
            r.error(f"template placeholder left in index.html: {marker!r}")
    if not canonical:
        r.error('missing <link rel="canonical">')
    if "<!-- RELATED:START -->" not in text or "<!-- FOOTER:START -->" not in text:
        r.warn("shared RELATED/FOOTER markers missing: run tools/render_shared.py")


def check_files(r, allowlist):
    base_url = None
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        size_mb = path.stat().st_size / 1e6
        if size_mb > MAX_FILE_MB:
            r.error(f"{rel} is {size_mb:.1f} MB (limit {MAX_FILE_MB} MB)")
        elif size_mb > WARN_FILE_MB:
            r.warn(f"{rel} is {size_mb:.1f} MB")
        name = path.name.lower()
        if path.suffix.lower() in (".html", ".htm", ".php", ".shtml", ".phtml", ".asp", ".aspx", ".jsp", ".cgi"):
            if len(rel.parts) != 1 or not (name in ALLOWED_HTML or ALLOWED_HTML_RE.match(name)):
                r.error(f"unexpected page {rel}: only index.html and 404.html are published")
        if path.suffix.lower() in TEXT_SUFFIXES and size_mb < 5:
            content = path.read_text(encoding="utf-8", errors="ignore")
            m = SPAM_WORDS.search(content)
            if m:
                r.error(f"{rel} contains a spam keyword: {m.group(0)!r}")
            if path.suffix.lower() == ".svg" and re.search(r"<script|\son\w+\s*=|javascript:", content, re.I):
                r.error(f"{rel}: SVG contains script")
    sitemap = ROOT / "sitemap.xml"
    if sitemap.exists():
        locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sitemap.read_text(encoding="utf-8"))
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', (ROOT / "index.html").read_text(encoding="utf-8"))
        base_url = canonical.group(1) if canonical else None
        for loc in locs:
            if base_url and not loc.startswith(base_url):
                r.error(f"sitemap.xml lists a URL outside this page: {loc}")
    llms = ROOT / "llms.txt"
    if llms.exists():
        for url in re.findall(r"https?://[^\s)>\]]+", llms.read_text(encoding="utf-8")):
            if not domain_allowed(urlsplit(url).hostname or "", allowlist):
                r.error(f"llms.txt links a domain not in tools/allowed-domains.txt: {url}")


def main():
    r = Report()
    allowlist = load_allowlist()
    check_index(r, allowlist)
    check_files(r, allowlist)
    for w in r.warnings:
        print(f"warning: {w}")
    for e in r.errors:
        print(f"error: {e}")
    if r.errors:
        print(f"\npage guard: {len(r.errors)} problem(s) found")
        return 1
    print("page guard: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
