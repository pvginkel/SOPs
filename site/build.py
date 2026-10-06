#!/usr/bin/env python3
"""Build the Homelab QRH: the SOPs in sops/ plus a mirror of Ansible's runbooks, as a static site.

    python site/build.py --ansible ../Ansible --out _site

Every link is relative, so the output works from GitHub Pages, from any other path, and
unzipped on a laptop (file://) alike.
"""

from __future__ import annotations

import argparse
import html
import json
import posixpath
import re
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from string import Template

import yaml
from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.admon import admon_plugin
from mdit_py_plugins.anchors import anchors_plugin

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
GITHUB = "https://github.com/pvginkel"
OFFLINE_ZIP = "qrh-offline.zip"
SEARCH_INDEX = "search-index.js"

# Section order is QRH order: the red tab first.
KINDS = {
    "emergency": ("Emergency", "E"),
    "abnormal": ("Abnormal", "A"),
    "normal": ("Normal", "N"),
    "periodic": ("Periodic", "P"),
}

GITHUB_BLOB = re.compile(
    r"^https://github\.com/pvginkel/(?P<repo>[\w.-]+)/blob/[^/]+/(?P<path>[^#?]+)(?P<frag>#.*)?$"
)
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


class BuildError(Exception):
    pass


@dataclass
class Repo:
    name: str
    root: Path
    sha: str
    date: str


@dataclass
class Page:
    out: str  # path in the site, e.g. "sops/pve-host-shutdown.html"
    repo: Repo
    path: str  # path in its repo, e.g. "sops/pve-host-shutdown.md"
    kind: str  # a KINDS key, "runbook" or "home"
    title: str
    body: str  # Markdown, front matter stripped
    meta: dict = field(default_factory=dict)
    code: str = ""  # E1, N2, ...
    html: str = ""

    @property
    def root(self) -> str:
        return "../" * self.out.count("/")

    @property
    def source_url(self) -> str:
        return f"{GITHUB}/{self.repo.name}/blob/main/{self.path}"

    @property
    def strict(self) -> bool:
        """Broken links fail the build on our own pages; on the mirror they are Ansible's to fix."""
        return self.kind != "runbook"


# --- Markdown ---------------------------------------------------------------------------------


def checklist_rule(state: StateCore) -> None:
    """`[ ] text` list items become tickable steps; `challenge :: response` gets a dotted leader."""
    tokens = state.tokens
    for i, tok in enumerate(tokens):
        if tok.type != "inline" or i < 2 or tokens[i - 2].type != "list_item_open":
            continue
        children = tok.children or []
        if not children or children[0].type != "text":
            continue
        m = re.match(r"\[([ xX])\] ", children[0].content)
        if not m:
            continue
        children[0].content = children[0].content[m.end() :]
        tokens[i - 2].attrJoin("class", "step")
        ticked = " checked" if m[1] != " " else ""
        head = [_html(f'<input type="checkbox" class="tick" aria-label="Done"{ticked}>')]
        for j, child in enumerate(children):
            if child.type == "text" and " :: " in child.content:
                before, after = child.content.split(" :: ", 1)
                child.content = before
                rest = Token("text", "", 0, content=after)
                children[j + 1 : j + 1] = [
                    _html('</span><span class="leader"></span><span class="response">'),
                    rest,
                ]
                head.append(_html('<span class="cr"><span class="challenge">'))
                children.append(_html("</span></span>"))
                break
        tok.children = head + children


def _html(content: str) -> Token:
    return Token("html_inline", "", 0, content=content)


def link_rule(state: StateCore) -> None:
    page: Page = state.env["page"]
    resolve = state.env["resolve"]
    for tok in state.tokens:
        for child in tok.children or []:
            attr = {"link_open": "href", "image": "src"}.get(child.type)
            if attr and child.attrGet(attr):
                child.attrSet(attr, resolve(page, str(child.attrGet(attr))))


def markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    md.use(anchors_plugin, min_level=1, max_level=6, permalink=True, permalinkSymbol="#")
    md.use(admon_plugin)
    md.core.ruler.push("qrh_checklist", checklist_rule)
    md.core.ruler.push("qrh_links", link_rule)
    return md


# --- Sources ----------------------------------------------------------------------------------


def git_repo(name: str, root: Path) -> Repo:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        sha, date = git("log", "-1", "--format=%h %cs").split()
    except (subprocess.CalledProcessError, ValueError):
        sha, date = "uncommitted", datetime.now(UTC).strftime("%Y-%m-%d")
    return Repo(name, root, sha, date)


def front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise BuildError(f"{path}: no front matter")
    return yaml.safe_load(m[1]) or {}, text[m.end() :]


def load_sops(repo: Repo) -> list[Page]:
    pages = []
    for path in sorted((repo.root / "sops").glob("*.md")):
        meta, body = front_matter(path)
        missing = [k for k in ("title", "kind", "project", "when") if not meta.get(k)]
        if missing:
            raise BuildError(f"{path}: front matter lacks {', '.join(missing)}")
        if meta["kind"] not in KINDS:
            raise BuildError(f"{path}: kind {meta['kind']!r} is not one of {', '.join(KINDS)}")
        pages.append(
            Page(
                out=f"sops/{path.stem}.html",
                repo=repo,
                path=f"sops/{path.name}",
                kind=meta["kind"],
                title=str(meta["title"]),
                body=body,
                meta=meta,
            )
        )
    kinds = list(KINDS)
    pages.sort(key=lambda p: (kinds.index(p.kind), p.meta.get("order", 100), p.title.lower()))
    counters: dict[str, int] = {}
    for p in pages:
        counters[p.kind] = counters.get(p.kind, 0) + 1
        p.code = f"{KINDS[p.kind][1]}{counters[p.kind]}"
    return pages


def load_runbooks(repo: Repo) -> list[Page]:
    pages = []
    for path in sorted((repo.root / "docs/runbooks").glob("*.md")):
        body = path.read_text(encoding="utf-8")
        m = re.search(r"^# (.+)$", body, re.MULTILINE)
        pages.append(
            Page(
                out=f"runbooks/{path.stem}.html",
                repo=repo,
                path=f"docs/runbooks/{path.name}",
                kind="runbook",
                title=re.sub(r"[`*]", "", m[1]).strip() if m else path.stem,
                body=body,
            )
        )
    pages.sort(key=lambda p: p.title.lower())
    return pages


# --- Links ------------------------------------------------------------------------------------


class Resolver:
    """Maps a link as written in a source file to its href on the site.

    A link to a file that has a page here, relative or as a github.com/pvginkel blob URL, goes to
    that page. Any other link into a repo goes to GitHub. The rest is left as written, and the
    link check judges it.
    """

    def __init__(self, pages: list[Page]):
        self.by_source = {(p.repo.name, p.path): p for p in pages}

    def __call__(self, page: Page, href: str) -> str:
        m = GITHUB_BLOB.match(href)
        if m:
            target = self.by_source.get((m["repo"], m["path"]))
            return page.root + target.out + (m["frag"] or "") if target else href
        if SCHEME.match(href) or href.startswith(("#", "/")):
            return href
        path, _, frag = href.partition("#")
        frag = f"#{frag}" if frag else ""
        target = posixpath.normpath(posixpath.join(posixpath.dirname(page.path), path))
        if target.startswith("../"):
            repo, _, rest = target[3:].partition("/")
            return f"{GITHUB}/{repo}/blob/main/{rest}{frag}" if rest else f"{GITHUB}/{repo}"
        known = self.by_source.get((page.repo.name, target))
        if known:
            return page.root + known.out + frag
        on_disk = page.repo.root / target
        if on_disk.exists():
            kind = "tree" if on_disk.is_dir() else "blob"
            return f"{GITHUB}/{page.repo.name}/{kind}/main/{target}{frag}"
        return href


def check_links(pages: list[Page], assets: set[str]) -> list[str]:
    ids = {p.out: set(re.findall(r'\sid="([^"]+)"', p.html)) for p in pages}
    errors, warnings = [], []
    for p in pages:
        for href in re.findall(r'\shref="([^"]+)"', p.html):
            href = html.unescape(href)
            if SCHEME.match(href):
                continue
            path, _, frag = href.partition("#")
            out = posixpath.normpath(posixpath.join(posixpath.dirname(p.out), path)) if path else p.out
            if out in ids:
                problem = f"no #{frag} in {out}" if frag and frag not in ids[out] else None
            else:
                problem = None if out in assets else f"no page {out}"
            if problem:
                (errors if p.strict else warnings).append(f"{p.repo.name}/{p.path}: {href}: {problem}")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    return errors


# --- HTML -------------------------------------------------------------------------------------


Inline = Callable[[Page, str], str]


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def nav(pages: list[Page], current: Page) -> str:
    def link(p: Page) -> str:
        cls = ' class="current" aria-current="page"' if p is current else ""
        code = f'<span class="code">{p.code}</span>' if p.code else ""
        return f'<li><a href="{current.root}{p.out}"{cls}>{code}<span>{esc(p.title)}</span></a></li>'

    parts = []
    for kind, (label, _) in KINDS.items():
        group = [p for p in pages if p.kind == kind]
        if group:
            items = "".join(link(p) for p in group)
            parts.append(f'<section class="navsec k-{kind}"><h2>{label}</h2><ul>{items}</ul></section>')
    runbooks = [p for p in pages if p.kind == "runbook"]
    if runbooks:
        opened = " open" if current.kind == "runbook" else ""
        items = "".join(link(p) for p in runbooks)
        parts.append(
            f'<details class="navsec k-runbook"{opened}><summary><h2>Ansible runbooks'
            f' <span class="count">{len(runbooks)}</span></h2></summary><ul>{items}</ul></details>'
        )
    return "".join(parts)


def sop_article(p: Page, inline: Inline) -> str:
    label = KINDS[p.kind][0]
    when = inline(p, str(p.meta["when"]))
    return f"""<article class="card k-{p.kind}">
<div class="tab"><span>{label}</span><span class="code">{p.code}</span></div>
<h1>{esc(p.title)}</h1>
<dl class="when"><dt>When</dt><dd>{when}</dd></dl>
<div class="meta"><span class="chip">{esc(str(p.meta["project"]))}</span>
<a href="{p.source_url}">Edit on GitHub</a></div>
<div class="progress" hidden><span class="count"></span><button type="button" class="reset">Reset</button></div>
<div class="body">
{p.html}
</div>
<div class="end">End of procedure</div>
</article>"""


def runbook_article(p: Page) -> str:
    return f"""<article class="card k-runbook">
<div class="tab"><span>Ansible runbook</span><span class="code">mirror</span></div>
<p class="mirror">Read-only copy of <a href="{p.source_url}">pvginkel/Ansible
<code>{p.path}</code></a> as of <code>{p.repo.sha}</code> ({p.repo.date}).
The source is authoritative: change it there.</p>
<div class="body">
{p.html}
</div>
</article>"""


def home_article(home: Page, pages: list[Page], inline: Inline) -> str:
    sections = []
    for kind, (label, _) in KINDS.items():
        rows = []
        for p in (p for p in pages if p.kind == kind):
            when = inline(p, str(p.meta["when"]))
            rows.append(
                f'<li><a href="{p.out}"><span class="code">{p.code}</span>'
                f'<span class="title">{esc(p.title)}</span><span class="leader"></span>'
                f'<span class="chip">{esc(str(p.meta["project"]))}</span></a>'
                f'<div class="row-when">{when}</div></li>'
            )
        if rows:
            sections.append(
                f'<section class="indexsec k-{kind}"><h2 class="tabhead">{label}</h2>'
                f'<ul class="rows">{"".join(rows)}</ul></section>'
            )
    runbooks = [p for p in pages if p.kind == "runbook"]
    if runbooks:
        items = "".join(f'<li><a href="{p.out}">{esc(p.title)}</a></li>' for p in runbooks)
        repo = runbooks[0].repo
        sections.append(
            f'<section class="indexsec k-runbook"><h2 class="tabhead">Ansible runbooks</h2>'
            f'<p class="mirror">Mirrored from <a href="{GITHUB}/Ansible/tree/main/docs/runbooks">'
            f"pvginkel/Ansible <code>docs/runbooks</code></a> as of <code>{repo.sha}</code>"
            f' ({repo.date}).</p><ul class="cols">{items}</ul></section>'
        )
    return f"""<section class="hero">
<div class="hero-badge">QRH</div>
<h1>Homelab<br>Quick Reference Handbook</h1>
<p class="tagline">Read it before you need it. Follow it when you do.</p>
</section>
<div class="body intro">
{home.html}
</div>
{"".join(sections)}"""


def search_entries(p: Page) -> list[dict]:
    """One entry per h2 section, so a hit lands on the section rather than the top of a long page."""
    entries = []
    chunks = re.split(r"(?=<h2[\s>])", p.html)
    for chunk in chunks:
        m = re.match(r'<h2[^>]*\sid="([^"]+)"[^>]*>(.*?)</h2>', chunk, re.DOTALL)
        heading = _text(m[2]).rstrip("#").strip() if m else ""
        text = _text(chunk[m.end() :] if m else chunk)
        if not text and not heading:
            continue
        entries.append(
            {
                "t": p.title,
                "h": heading,
                "u": p.out + (f"#{m[1]}" if m else ""),
                "k": p.kind,
                "c": p.code,
                "x": text,
            }
        )
    return entries


def _text(fragment: str) -> str:
    fragment = re.sub(r'<a class="header-anchor".*?</a>', "", fragment, flags=re.DOTALL)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


# --- Main -------------------------------------------------------------------------------------


def build(ansible_root: Path, out: Path) -> None:
    sops_repo = git_repo("SOPs", ROOT)
    ansible_repo = git_repo("Ansible", ansible_root)
    if not (ansible_root / "docs/runbooks").is_dir():
        raise BuildError(f"{ansible_root}: no docs/runbooks — pass an Ansible checkout with --ansible")

    sops = load_sops(sops_repo)
    runbooks = load_runbooks(ansible_repo)
    home_body = (SITE / "home.md").read_text(encoding="utf-8")
    home = Page(
        out="index.html", repo=sops_repo, path="site/home.md", kind="home", title="Home", body=home_body
    )
    pages = sops + runbooks + [home]

    md = markdown()
    resolve = Resolver(pages)
    for p in pages:
        p.html = md.render(p.body, {"page": p, "resolve": resolve})

    def inline(p: Page, text: str) -> str:
        return md.renderInline(text, {"page": p, "resolve": resolve})

    template = Template((SITE / "page.html").read_text(encoding="utf-8"))
    built = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE / "static", out / "static")
    for p in pages:
        if p.kind == "home":
            content, main_class = home_article(p, sops + runbooks, inline), "home"
        elif p.kind == "runbook":
            content, main_class = runbook_article(p), "runbook"
        else:
            content, main_class = sop_article(p, inline), "sop"
        footer = (
            f'Built {built} from <a href="{GITHUB}/SOPs">pvginkel/SOPs</a> <code>{sops_repo.sha}</code>'
            f' and <a href="{GITHUB}/Ansible">pvginkel/Ansible</a> <code>{ansible_repo.sha}</code>.'
            f' <a href="{p.root}{OFFLINE_ZIP}">Offline copy</a>: unzip, open <code>index.html</code>.'
        )
        target = out / p.out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            template.substitute(
                title=esc(p.title if p.kind != "home" else "Homelab Quick Reference Handbook"),
                root=p.root,
                nav=nav(sops + runbooks, p),
                main_class=main_class,
                content=content,
                footer=footer,
            ),
            encoding="utf-8",
        )

    assets = {OFFLINE_ZIP, SEARCH_INDEX} | {
        f.relative_to(out).as_posix() for f in (out / "static").rglob("*") if f.is_file()
    }
    errors = check_links(pages, assets)
    if errors:
        raise BuildError("broken links:\n  " + "\n  ".join(errors))

    index = [e for p in pages if p.kind != "home" for e in search_entries(p)]
    (out / SEARCH_INDEX).write_text(
        "window.QRH_INDEX = " + json.dumps(index, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (out / ".nojekyll").touch()
    files = sorted(f for f in out.rglob("*") if f.is_file())
    with zipfile.ZipFile(out / OFFLINE_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f"homelab-qrh/{f.relative_to(out).as_posix()}")
    print(f"built {len(sops)} SOPs and {len(runbooks)} runbooks into {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ansible", type=Path, required=True, help="an Ansible checkout")
    parser.add_argument("--out", type=Path, default=ROOT / "_site", help="output directory")
    args = parser.parse_args()
    try:
        build(args.ansible.resolve(), args.out.resolve())
    except BuildError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
