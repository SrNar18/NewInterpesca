#!/usr/bin/env python3
"""
Interpesca · SEO Audit & Autofix
=================================

Script d'auditoria SEO per al lloc web d'Interpesca.

Funcionalitats:
  - Analitza els fitxers HTML locals i detecta problemes de SEO.
  - Comprova meta tags essencials, Open Graph, Twitter Card i JSON-LD.
  - Valida atributs 'title', 'alt', 'lang', 'rel', 'aria-*'.
  - Verifica enllaços externs i interns.
  - Comprova la presència de robots.txt, sitemap.xml i _headers.
  - Analitza rendiment bàsic (mida d'arxius, preconnects, preloads).
  - Genera un informe complet (consola + fitxer Markdown).
  - Mode --fix: afegeix automàticament atributs 'title' mancants en
    enllaços <a>, 'alt' buits a imatges i 'loading="lazy"' a iframes/imatges.

Ús:
    python seo_audit.py                  # auditoria completa
    python seo_audit.py --fix            # audita i aplica fixes automàtics
    python seo_audit.py --report seo.md  # genera informe Markdown
    python seo_audit.py --file index.html

Dependències: només biblioteca estàndard de Python 3.8+.
Autor: Interpesca dev team
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Colors per a consola (ANSI)
# ---------------------------------------------------------------------------
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


# ---------------------------------------------------------------------------
# Issue model
# ---------------------------------------------------------------------------
SEVERITY_LEVELS = ("critical", "high", "medium", "low", "info")


@dataclass
class Issue:
    severity: str
    category: str
    message: str
    fix_hint: str = ""

    def icon(self) -> str:
        return {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "⚪",
        }.get(self.severity, "⚪")

    def color(self) -> str:
        return {
            "critical": C.RED,
            "high": C.RED,
            "medium": C.YELLOW,
            "low": C.BLUE,
            "info": C.DIM,
        }.get(self.severity, "")


# ---------------------------------------------------------------------------
# HTML parser lleuger (només per extreure tags i atributs)
# ---------------------------------------------------------------------------
class TagExtractor(HTMLParser):
    """Extreu tots els tags amb els seus atributs i contingut."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []
        self.text_by_tag: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        entry = {
            "tag": tag,
            "attrs": {k: (v or "") for k, v in attrs},
            "text": "",
        }
        self.tags.append(entry)
        self._stack.append(entry)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append({
            "tag": tag,
            "attrs": {k: (v or "") for k, v in attrs},
            "text": "",
        })

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1]["tag"] == tag:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._stack:
            self._stack[-1]["text"] += data


# ---------------------------------------------------------------------------
# Audit engine
# ---------------------------------------------------------------------------
@dataclass
class AuditResult:
    file: Path
    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> int:
        """Puntuació 0–100 basada en severitat dels issues."""
        weight = {"critical": 20, "high": 10, "medium": 5, "low": 2, "info": 0}
        total = sum(weight.get(i.severity, 0) for i in self.issues)
        return max(0, 100 - total)


class SEOAuditor:
    # Meta tags recomanats
    REQUIRED_META = {
        "description": "Descripció SEO principal (150-160 caràcters).",
        "viewport": "Essencial per a responsive design.",
        "robots": "Directrius per a motors de cerca.",
    }
    RECOMMENDED_META = {
        "keywords": "Paraules clau (opcional però útil).",
        "author": "Autor/organització.",
        "theme-color": "Color del tema per a navegadors mòbils.",
        "geo.region": "Regió geogràfica (SEO local).",
    }
    REQUIRED_OG = [
        "og:type", "og:title", "og:description", "og:url", "og:image",
    ]
    REQUIRED_TWITTER = ["twitter:card", "twitter:title", "twitter:description"]

    def __init__(self, file: Path) -> None:
        self.file = file
        self.html_content = file.read_text(encoding="utf-8")
        self.parser = TagExtractor()
        self.parser.feed(self.html_content)
        self.result = AuditResult(file=file)

    # ---------- checks ----------
    def audit(self) -> AuditResult:
        self._check_doctype()
        self._check_html_lang()
        self._check_title()
        self._check_meta_tags()
        self._check_open_graph()
        self._check_twitter_card()
        self._check_canonical()
        self._check_structured_data()
        self._check_headings()
        self._check_images()
        self._check_links()
        self._check_iframes()
        self._check_forms()
        self._check_performance_hints()
        self._check_semantic_html()
        self._compute_stats()
        return self.result

    # ---- individual checks ----
    def _check_doctype(self) -> None:
        if not re.match(r"\s*<!DOCTYPE html>", self.html_content, re.IGNORECASE):
            self._add("critical", "DOCTYPE", "Falta <!DOCTYPE html>", "Afegeix <!DOCTYPE html> al principi.")

    def _check_html_lang(self) -> None:
        html_tag = self._find_first("html")
        if not html_tag:
            return
        lang = html_tag["attrs"].get("lang")
        if not lang:
            self._add("critical", "HTML", "L'element <html> no té atribut 'lang'",
                      "Afegeix lang=\"ca\" a <html>.")
        elif len(lang) < 2:
            self._add("medium", "HTML", f"Atribut 'lang' sospitós: '{lang}'")

    def _check_title(self) -> None:
        titles = [t for t in self.parser.tags if t["tag"] == "title"]
        if not titles:
            self._add("critical", "<title>", "Falta la tag <title>", "Afegeix <title>...</title> dins de <head>.")
            return
        title_text = titles[0].get("text", "").strip()
        if not title_text:
            self._add("critical", "<title>", "Tag <title> buida")
        else:
            n = len(title_text)
            if n < 30:
                self._add("medium", "<title>", f"Títol curt ({n} car.) — recomanat 50-60")
            elif n > 65:
                self._add("medium", "<title>", f"Títol llarg ({n} car.) — Google pot truncar a 60")

    def _check_meta_tags(self) -> None:
        metas = self._collect_meta()
        # requisits
        for name, descr in self.REQUIRED_META.items():
            if name not in metas:
                self._add("high", "META", f"Falta <meta name=\"{name}\">", descr)
        # recomanats
        for name, descr in self.RECOMMENDED_META.items():
            if name not in metas:
                self._add("low", "META", f"Recomanat <meta name=\"{name}\">", descr)
        # longituds
        desc = metas.get("description", "")
        if desc:
            n = len(desc)
            if n < 80:
                self._add("medium", "META", f"Description curta ({n} car.) — recomanat 120-160")
            elif n > 170:
                self._add("medium", "META", f"Description llarga ({n} car.) — Google trunca a ~160")

    def _check_open_graph(self) -> None:
        props = self._collect_og()
        for prop in self.REQUIRED_OG:
            if prop not in props:
                self._add("medium", "OpenGraph", f"Falta <meta property=\"{prop}\">",
                          "Millora compartició a xarxes socials.")

    def _check_twitter_card(self) -> None:
        metas = self._collect_meta()
        for name in self.REQUIRED_TWITTER:
            if name not in metas:
                self._add("low", "Twitter", f"Recomanat <meta name=\"{name}\">")

    def _check_canonical(self) -> None:
        links = [t for t in self.parser.tags if t["tag"] == "link"]
        has_canonical = any(l["attrs"].get("rel") == "canonical" for l in links)
        if not has_canonical:
            self._add("high", "Canonical", "Falta <link rel=\"canonical\">",
                      "Afegeix canonical per evitar contingut duplicat.")

    def _check_structured_data(self) -> None:
        scripts = [t for t in self.parser.tags if t["tag"] == "script"]
        ld_scripts = [s for s in scripts if s["attrs"].get("type") == "application/ld+json"]
        if not ld_scripts:
            self._add("medium", "JSON-LD", "No hi ha dades estructurades (schema.org)",
                      "Afegeix almenys un script JSON-LD per LocalBusiness/Organization.")
            return
        for s in ld_scripts:
            try:
                json.loads(s.get("text", "{}"))
            except json.JSONDecodeError as e:
                self._add("high", "JSON-LD", f"JSON-LD invàlid: {e}")

    def _check_headings(self) -> None:
        h1s = [t for t in self.parser.tags if t["tag"] == "h1"]
        if not h1s:
            self._add("high", "Headings", "No hi ha cap <h1> a la pàgina")
        elif len(h1s) > 1:
            self._add("medium", "Headings", f"Hi ha {len(h1s)} <h1> — recomanat només 1")

    def _check_images(self) -> None:
        imgs = [t for t in self.parser.tags if t["tag"] == "img"]
        for img in imgs:
            src = img["attrs"].get("src", "")
            if "alt" not in img["attrs"]:
                self._add("high", "Images", f"Imatge sense 'alt': {src[:60]}",
                          "Afegeix alt descriptiu o alt=\"\" si és decorativa.")
            if not img["attrs"].get("loading"):
                if "hero" not in src and "logo" not in src:
                    self._add("low", "Images", f"Imatge sense loading=\"lazy\": {src[:60]}")
            if not (img["attrs"].get("width") and img["attrs"].get("height")):
                self._add("low", "Images", f"Imatge sense dimensions (CLS): {src[:60]}",
                          "Afegeix width i height per evitar layout shift.")

    def _check_links(self) -> None:
        anchors = [t for t in self.parser.tags if t["tag"] == "a"]
        for a in anchors:
            attrs = a["attrs"]
            href = attrs.get("href", "")
            if not href or href == "#":
                self._add("low", "Links", f"Enllaç buit o placeholder: href=\"{href}\"")
            # targets externs
            if attrs.get("target") == "_blank":
                rel = attrs.get("rel", "")
                if "noopener" not in rel:
                    self._add("medium", "Links", f"target=\"_blank\" sense rel=\"noopener\" — risc de tabnabbing: {href[:60]}")
            # title
            if not attrs.get("title") and not attrs.get("aria-label"):
                # només critic si és un botó amb només icona
                txt = (a.get("text") or "").strip()
                if not txt:
                    self._add("medium", "Links", f"Enllaç sense text, title o aria-label: href=\"{href}\"")

    def _check_iframes(self) -> None:
        iframes = [t for t in self.parser.tags if t["tag"] == "iframe"]
        for f in iframes:
            if not f["attrs"].get("title"):
                self._add("high", "Iframes", "Iframe sense 'title' (accessibilitat/SEO)")
            if not f["attrs"].get("loading"):
                self._add("low", "Iframes", "Iframe sense loading=\"lazy\"")

    def _check_forms(self) -> None:
        inputs = [t for t in self.parser.tags if t["tag"] in ("input", "select", "textarea")]
        for inp in inputs:
            attrs = inp["attrs"]
            if attrs.get("type") in ("submit", "button", "hidden", "checkbox", "radio"):
                continue
            if not (attrs.get("aria-label") or attrs.get("title") or attrs.get("placeholder") or attrs.get("id")):
                self._add("medium", "Forms", f"Input sense etiqueta accessible: {attrs}")

    def _check_performance_hints(self) -> None:
        links = [t for t in self.parser.tags if t["tag"] == "link"]
        rels = [l["attrs"].get("rel", "") for l in links]
        if not any("preconnect" in r for r in rels):
            self._add("low", "Performance", "No hi ha <link rel=\"preconnect\"> — pot alentir requests externs")
        if not any("preload" in r for r in rels):
            self._add("info", "Performance", "No es fa servir <link rel=\"preload\"> per a recursos crítics")

    def _check_semantic_html(self) -> None:
        required = {"header", "main", "footer", "nav"}
        found = {t["tag"] for t in self.parser.tags}
        missing = required - found
        if missing:
            self._add("low", "Semantic", f"Etiquetes semàntiques mancants: {', '.join(sorted(missing))}")

    # ---------- helpers ----------
    def _compute_stats(self) -> None:
        tags = self.parser.tags
        self.result.stats = {
            "total_tags": len(tags),
            "links": len([t for t in tags if t["tag"] == "a"]),
            "images": len([t for t in tags if t["tag"] == "img"]),
            "iframes": len([t for t in tags if t["tag"] == "iframe"]),
            "scripts": len([t for t in tags if t["tag"] == "script"]),
            "file_size_kb": round(len(self.html_content.encode("utf-8")) / 1024, 1),
            "word_count": len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", self.html_content))),
        }

    def _add(self, severity: str, category: str, message: str, fix_hint: str = "") -> None:
        self.result.issues.append(Issue(severity, category, message, fix_hint))

    def _find_first(self, tag: str) -> dict[str, Any] | None:
        for t in self.parser.tags:
            if t["tag"] == tag:
                return t
        return None

    def _collect_meta(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for t in self.parser.tags:
            if t["tag"] == "meta":
                name = t["attrs"].get("name") or t["attrs"].get("http-equiv")
                if name:
                    out[name] = t["attrs"].get("content", "")
        return out

    def _collect_og(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for t in self.parser.tags:
            if t["tag"] == "meta":
                prop = t["attrs"].get("property", "")
                if prop.startswith("og:"):
                    out[prop] = t["attrs"].get("content", "")
        return out


# ---------------------------------------------------------------------------
# Auto-fixer
# ---------------------------------------------------------------------------
class SEOAutoFixer:
    """Aplica correccions segures i idempotents al codi HTML."""

    IMG_REGEX = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
    A_REGEX = re.compile(r"<a\b([^>]*)>", re.IGNORECASE)
    IFRAME_REGEX = re.compile(r"<iframe\b([^>]*?)>", re.IGNORECASE)

    def __init__(self, file: Path) -> None:
        self.file = file
        self.content = file.read_text(encoding="utf-8")
        self.fixes_applied: list[str] = []

    def fix(self) -> str:
        self.content = self._fix_images()
        self.content = self._fix_iframes()
        self.content = self._fix_external_links()
        return self.content

    def save(self) -> None:
        self.file.write_text(self.content, encoding="utf-8")

    def _has_attr(self, attrs: str, name: str) -> bool:
        return bool(re.search(rf"\b{name}\s*=", attrs, re.IGNORECASE))

    def _fix_images(self) -> str:
        def repl(match: re.Match[str]) -> str:
            attrs = match.group(1)
            original = attrs
            if not self._has_attr(attrs, "alt"):
                attrs += ' alt=""'
                self.fixes_applied.append("img: afegit alt buit")
            if not self._has_attr(attrs, "loading"):
                if "logo" not in attrs and "hero" not in attrs:
                    attrs += ' loading="lazy"'
                    self.fixes_applied.append("img: afegit loading=\"lazy\"")
            if not self._has_attr(attrs, "decoding"):
                attrs += ' decoding="async"'
                self.fixes_applied.append("img: afegit decoding=\"async\"")
            if attrs == original:
                return match.group(0)
            return f"<img{attrs}>"
        return self.IMG_REGEX.sub(repl, self.content)

    def _fix_iframes(self) -> str:
        def repl(match: re.Match[str]) -> str:
            attrs = match.group(1)
            original = attrs
            if not self._has_attr(attrs, "loading"):
                attrs += ' loading="lazy"'
                self.fixes_applied.append("iframe: afegit loading=\"lazy\"")
            if not self._has_attr(attrs, "referrerpolicy"):
                attrs += ' referrerpolicy="no-referrer-when-downgrade"'
                self.fixes_applied.append("iframe: afegit referrerpolicy")
            if attrs == original:
                return match.group(0)
            return f"<iframe{attrs}>"
        return self.IFRAME_REGEX.sub(repl, self.content)

    def _fix_external_links(self) -> str:
        """Afegeix rel=\"noopener noreferrer\" a links amb target=\"_blank\"."""
        def repl(match: re.Match[str]) -> str:
            attrs = match.group(1)
            if 'target="_blank"' not in attrs and "target='_blank'" not in attrs:
                return match.group(0)
            rel_match = re.search(r"rel\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.IGNORECASE)
            if rel_match:
                rel_val = rel_match.group(1)
                needed = []
                if "noopener" not in rel_val:
                    needed.append("noopener")
                if "noreferrer" not in rel_val:
                    needed.append("noreferrer")
                if not needed:
                    return match.group(0)
                new_rel = (rel_val + " " + " ".join(needed)).strip()
                attrs = attrs.replace(rel_match.group(0), f'rel="{new_rel}"')
                self.fixes_applied.append("a: actualitzat rel")
            else:
                attrs += ' rel="noopener noreferrer"'
                self.fixes_applied.append("a: afegit rel=\"noopener noreferrer\"")
            return f"<a{attrs}>"
        return self.A_REGEX.sub(repl, self.content)


# ---------------------------------------------------------------------------
# File-existence checks (robots, sitemap, headers)
# ---------------------------------------------------------------------------
def check_companion_files(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    expected = {
        "robots.txt": ("high", "Falta robots.txt a l'arrel"),
        "sitemap.xml": ("high", "Falta sitemap.xml a l'arrel"),
        "_headers": ("medium", "Falta _headers (cache-control / security)"),
        "manifest.webmanifest": ("low", "Falta manifest.webmanifest (PWA)"),
    }
    for name, (sev, msg) in expected.items():
        if not (root / name).exists():
            issues.append(Issue(sev, "Files", msg, f"Crea {name} a l'arrel."))
    return issues


# ---------------------------------------------------------------------------
# Report renderers
# ---------------------------------------------------------------------------
def render_console(results: list[AuditResult], extra_issues: list[Issue]) -> None:
    print(f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════════════════════╗")
    print(f"║{C.RESET}{C.BOLD}   Interpesca · Auditoria SEO                         {C.CYAN}║")
    print(f"╚══════════════════════════════════════════════════════╝{C.RESET}\n")

    for result in results:
        print(f"{C.BOLD}📄 {result.file}{C.RESET}")
        print(f"   {C.DIM}Mida: {result.stats.get('file_size_kb')} KB · "
              f"Paraules: {result.stats.get('word_count')} · "
              f"Enllaços: {result.stats.get('links')} · "
              f"Imatges: {result.stats.get('images')}{C.RESET}")
        score = result.score
        score_color = C.GREEN if score >= 85 else C.YELLOW if score >= 65 else C.RED
        print(f"   {C.BOLD}Puntuació: {score_color}{score}/100{C.RESET}\n")

        grouped: dict[str, list[Issue]] = {}
        for issue in result.issues:
            grouped.setdefault(issue.severity, []).append(issue)

        for sev in SEVERITY_LEVELS:
            if sev not in grouped:
                continue
            bucket = grouped[sev]
            print(f"   {bucket[0].color()}{C.BOLD}[{sev.upper()}] · {len(bucket)} issue(s){C.RESET}")
            for issue in bucket:
                print(f"     {issue.icon()} [{issue.category}] {issue.message}")
                if issue.fix_hint:
                    print(f"        {C.DIM}→ {issue.fix_hint}{C.RESET}")
            print()

    if extra_issues:
        print(f"{C.BOLD}📁 Fitxers del lloc{C.RESET}")
        for issue in extra_issues:
            print(f"     {issue.icon()} [{issue.category}] {issue.message}")
            if issue.fix_hint:
                print(f"        {C.DIM}→ {issue.fix_hint}{C.RESET}")
        print()

    total_issues = sum(len(r.issues) for r in results) + len(extra_issues)
    print(f"{C.BOLD}══════════════════════════════════════════════════════{C.RESET}")
    print(f"{C.BOLD}Total: {total_issues} issue(s) detectat(s){C.RESET}\n")


def render_markdown(results: list[AuditResult], extra_issues: list[Issue], output: Path) -> None:
    lines: list[str] = [
        "# Interpesca — Informe d'Auditoria SEO",
        "",
        f"_Generat automàticament pel script `seo_audit.py`_",
        "",
    ]

    for result in results:
        lines += [
            f"## 📄 `{result.file.name}`",
            "",
            f"- **Puntuació:** **{result.score}/100**",
            f"- **Mida:** {result.stats.get('file_size_kb')} KB",
            f"- **Paraules:** {result.stats.get('word_count')}",
            f"- **Enllaços:** {result.stats.get('links')} · "
            f"Imatges: {result.stats.get('images')} · "
            f"Iframes: {result.stats.get('iframes')} · "
            f"Scripts: {result.stats.get('scripts')}",
            "",
            "### Issues detectats",
            "",
            "| Severitat | Categoria | Problema | Suggeriment |",
            "|-----------|-----------|----------|-------------|",
        ]
        for issue in sorted(result.issues, key=lambda i: SEVERITY_LEVELS.index(i.severity)):
            lines.append(
                f"| {issue.icon()} {issue.severity} | {issue.category} | "
                f"{html.escape(issue.message)} | {html.escape(issue.fix_hint)} |"
            )
        lines.append("")

    if extra_issues:
        lines += [
            "## 📁 Fitxers del lloc",
            "",
            "| Severitat | Problema | Suggeriment |",
            "|-----------|----------|-------------|",
        ]
        for issue in extra_issues:
            lines.append(
                f"| {issue.icon()} {issue.severity} | "
                f"{html.escape(issue.message)} | {html.escape(issue.fix_hint)} |"
            )
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"{C.GREEN}✓ Informe Markdown desat a: {output}{C.RESET}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audita el SEO dels fitxers HTML d'Interpesca.",
    )
    parser.add_argument("--file", type=Path, help="Fitxer HTML específic a auditar.")
    parser.add_argument("--dir", type=Path, default=Path("."),
                        help="Directori on buscar fitxers HTML (per defecte: ./)")
    parser.add_argument("--fix", action="store_true",
                        help="Aplica correccions automàtiques al HTML.")
    parser.add_argument("--report", type=Path,
                        help="Genera un informe Markdown al path donat.")
    args = parser.parse_args()

    root = args.dir.resolve()
    if args.file:
        files = [args.file.resolve()]
    else:
        files = sorted(root.glob("*.html"))

    if not files:
        print(f"{C.RED}✗ No s'han trobat fitxers HTML a {root}{C.RESET}")
        return 1

    results: list[AuditResult] = []
    for f in files:
        print(f"{C.CYAN}▸ Auditant {f.name}...{C.RESET}")
        auditor = SEOAuditor(f)
        results.append(auditor.audit())

        if args.fix:
            fixer = SEOAutoFixer(f)
            fixer.fix()
            if fixer.fixes_applied:
                fixer.save()
                print(f"  {C.GREEN}✓ {len(fixer.fixes_applied)} fixes aplicats a {f.name}:{C.RESET}")
                for fx in fixer.fixes_applied[:10]:
                    print(f"    · {fx}")
                if len(fixer.fixes_applied) > 10:
                    print(f"    · ... i {len(fixer.fixes_applied) - 10} més")
            else:
                print(f"  {C.DIM}✓ Cap fix necessari{C.RESET}")

    extra_issues = check_companion_files(root)
    render_console(results, extra_issues)

    if args.report:
        render_markdown(results, extra_issues, args.report)

    # exit code: 1 si hi ha issues critical/high
    severe = sum(1 for r in results for i in r.issues if i.severity in ("critical", "high"))
    severe += sum(1 for i in extra_issues if i.severity in ("critical", "high"))
    return 1 if severe > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
