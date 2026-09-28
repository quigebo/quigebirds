"""The stamp sheet: the admin's Stamps tab.

Every bird the station has ever heard is a stamp, numbered in the order it was
first heard. The work a plate was cut from is its issue, and each issue prints
in its own ink. Pure string builders like `admin`, so none of it needs a server
to test.
"""

from __future__ import annotations

import html
import zlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from .. import modes
from ..names import BIRDS, origin_of, source_of, variants_for
from ..source import Species
from .admin import _display_name

# Postage inks, dark enough to read as print on the paper tile.
INKS = ("#9b3434", "#2f4d8a", "#2f6b4f", "#5b3f7a", "#7a4b2a", "#3f5563", "#8a6418", "#1f6a6f")

# Wider than this is drawn as a landscape stamp, two columns across.
WIDE = 1.25


def plate(ctx: modes.Context, name: str) -> Path | None:
    """The plate a species' stamp shows: its first variant, never the collage's
    pick. `Picks` writes on every choice and the render loop forgets whatever
    left its window, so a gallery of the whole life list would reshuffle each
    visit. `name` comes off a query string, so nothing outside the style's own
    birds folder is answered."""
    variants = variants_for(name, ctx.images_dir, ctx.style)
    if not variants:
        return None
    first = variants[0]
    if first.resolve().parent != (ctx.images_dir / ctx.style / BIRDS).resolve():
        return None
    return first


def _ink(issue: str) -> str:
    return INKS[zlib.crc32(issue.encode()) % len(INKS)]


def _wide(path: Path) -> bool:
    with Image.open(path) as image:  # the header only
        w, h = image.size
    return w > h * WIDE


def _stamp(
    ctx: modes.Context, number: int, species: Species, date: Callable[[datetime], str]
) -> str:
    sci = species.scientific_name
    parts = ctx.namer.parts(sci)
    path = plate(ctx, sci)
    issue = (source_of(path) or ctx.style) if path else ""
    url = origin_of(path) if path else ""
    e = html.escape
    title = e(parts[0])
    latin = "" if parts[0] == sci else f"<em>{e(sci)}</em>"
    picture = (
        f'<img src="/plate?name={quote(sci)}" loading="lazy" alt="">'
        if path
        else '<span class="unissued">no plate</span>'
    )
    credit = e(_display_name(issue)) if issue else "no plate"
    if url:
        credit = f'<a href="{e(url)}" target="_blank" rel="noopener">{credit}</a>'
    classes = "stamp" + (" wide" if path and _wide(path) else "") + ("" if path else " blank")
    first = e(date(species.first_seen))
    return (
        f'<li class="{classes}" style="--ink:{_ink(issue)}" data-no="{number}"'
        f' data-name="{e(parts[0].lower())}" data-count="{species.count}" data-issue="{e(issue)}">'
        f'<button type="button" class="face" aria-label="No. {number}, {title}">'
        f'<span class="frame"><span class="top"><b>{number}</b>'
        f'<span class="issue">{e(_display_name(issue)) if issue else ""}</span></span>'
        f'<span class="art">{picture}</span>'
        f'<span class="name">{title}</span>{latin}</span>'
        f'<span class="postmark">{first}</span></button>'
        f'<template><div class="card">{picture}<div class="about">'
        f'<p class="issue">No. {number}{" · " + e(_display_name(issue)) if issue else ""}</p>'
        f"<h3>{title}</h3>{''.join(f'<p>{e(p)}</p>' for p in parts[1:])}{latin}"
        f"<dl><dt>First heard</dt><dd>{first}</dd>"
        f"<dt>Last heard</dt><dd>{e(date(species.last_seen))}</dd>"
        f"<dt>Detections</dt><dd>{species.count:,}</dd>"
        f"<dt>Plate</dt><dd>{credit}</dd></dl></div></div></template></li>"
    )


def sheet(ctx: modes.Context) -> str:
    """The whole sheet, earliest first. Raises `Unavailable` with the detector
    gone rather than showing an empty album."""
    heard = ctx.source.life_list()
    date = ctx.namer.date  # bound once: _stamp is called per bird
    stamps = "".join(_stamp(ctx, n, s, date) for n, s in enumerate(heard, 1))
    return stamps or '<li class="empty">No birds heard yet - the first one gets stamp No. 1.</li>'
