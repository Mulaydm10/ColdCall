"""Excursion chart as a standalone SVG, using nothing but the standard library.

Why not matplotlib
------------------
The spec called for a matplotlib PNG. This renders SVG by hand instead, for three reasons
that all point the same way:

1. ``src/coldcall`` is uploaded into the Daytona sandbox and must import against a stock
   interpreter (``ADR-0002``). Adding matplotlib means a pip install inside the jail.
2. The sandbox exec timeout is 60 s and its network has been flaky enough that the harness
   docs warn about it. Spending that budget on a wheel download, to draw one chart, is the
   kind of avoidable failure that happens during a live demo and not before it.
3. SVG is text. It survives the sandbox file-download endpoint unchanged, embeds directly
   in the generative-UI incident board, and scales cleanly on a projector.

The output is deliberately self-contained: no external fonts, no CSS, no scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from coldcall.mkt import Reading, _as_readings

__all__ = ["ChartTheme", "excursion_svg"]


@dataclass(frozen=True, slots=True)
class ChartTheme:
    """Colours and geometry. Defaults are tuned for a dark projector, high contrast."""

    width: int = 900
    height: int = 380
    pad_left: int = 62
    pad_right: int = 20
    pad_top: int = 46
    pad_bottom: int = 46
    background: str = "#0f1117"
    grid: str = "#2a2f3a"
    text: str = "#e6e8ee"
    muted: str = "#9aa3b2"
    in_band: str = "#1f6f4a"
    allowed_band: str = "#6b5a1f"
    trace: str = "#7fd1ff"
    breach: str = "#ff5c5c"


def _nice_bounds(lo: float, hi: float) -> tuple[float, float]:
    """Pad a range to whole degrees so the axis labels are readable, never inverted."""
    if hi - lo < 1e-9:
        lo, hi = lo - 1.0, hi + 1.0
    span = hi - lo
    pad = max(0.5, span * 0.12)
    return lo - pad, hi + pad


def excursion_svg(
    readings: object,
    label_lower_c: float,
    label_upper_c: float,
    excursion_lower_c: float | None = None,
    excursion_upper_c: float | None = None,
    title: str = "Shipment temperature vs labelled envelope",
    subtitle: str = "",
) -> str:
    """Render the temperature trace against its labelled and permitted-excursion bands.

    Args:
        readings: ``Reading`` objects or bare °C numbers. Durations are respected, so a
            logger gap widens the corresponding segment rather than vanishing.
        label_lower_c / label_upper_c: the labelled storage range (the green band).
        excursion_lower_c / excursion_upper_c: the permitted excursion range from the label,
            if the label states one (the amber band). Omit when it does not.
        title / subtitle: header text. Both are XML-escaped; callers may pass raw values.

    Returns:
        A complete ``<svg>`` document as a string.
    """
    series: list[Reading] = _as_readings(readings)
    t = ChartTheme()

    # X axis is elapsed minutes, so an uneven sampling interval plots honestly.
    elapsed: list[float] = []
    running = 0.0
    for r in series:
        elapsed.append(running)
        running += r.minutes
    total_minutes = running if running > 0 else 1.0

    temps = [r.celsius for r in series]
    lo_extra = [excursion_lower_c] if excursion_lower_c is not None else []
    hi_extra = [excursion_upper_c] if excursion_upper_c is not None else []
    band_lo = min([*temps, label_lower_c, *lo_extra])
    band_hi = max([*temps, label_upper_c, *hi_extra])
    y_lo, y_hi = _nice_bounds(band_lo, band_hi)

    plot_w = t.width - t.pad_left - t.pad_right
    plot_h = t.height - t.pad_top - t.pad_bottom

    def px(minutes: float) -> float:
        return t.pad_left + plot_w * (minutes / total_minutes)

    def py(celsius: float) -> float:
        frac = (celsius - y_lo) / (y_hi - y_lo)
        return t.pad_top + plot_h * (1.0 - frac)

    def band(lo: float, hi: float, fill: str, opacity: float) -> str:
        top, bottom = py(min(hi, y_hi)), py(max(lo, y_lo))
        return (
            f'<rect x="{t.pad_left:.1f}" y="{top:.1f}" width="{plot_w:.1f}" '
            f'height="{max(0.0, bottom - top):.1f}" fill="{fill}" opacity="{opacity}"/>'
        )

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {t.width} {t.height}" '
        f'width="{t.width}" height="{t.height}" role="img">',
        f'<rect width="{t.width}" height="{t.height}" fill="{t.background}"/>',
        f'<text x="{t.pad_left}" y="24" fill="{t.text}" font-family="system-ui,sans-serif" '
        f'font-size="15" font-weight="600">{escape(title)}</text>',
    ]
    if subtitle:
        out.append(
            f'<text x="{t.pad_left}" y="40" fill="{t.muted}" font-family="system-ui,sans-serif" '
            f'font-size="11">{escape(subtitle)}</text>'
        )

    # Bands, widest first so the labelled range paints on top of the permitted range.
    if excursion_lower_c is not None and excursion_upper_c is not None:
        out.append(band(excursion_lower_c, excursion_upper_c, t.allowed_band, 0.35))
    out.append(band(label_lower_c, label_upper_c, t.in_band, 0.30))

    # Horizontal gridlines on whole degrees, thinned so a wide range stays legible.
    step = max(1, int((y_hi - y_lo) / 6))
    tick = int(y_lo) - (int(y_lo) % step)
    while tick <= y_hi:
        if tick >= y_lo:
            y = py(tick)
            out.append(
                f'<line x1="{t.pad_left}" y1="{y:.1f}" x2="{t.pad_left + plot_w}" y2="{y:.1f}" '
                f'stroke="{t.grid}" stroke-width="1"/>'
                f'<text x="{t.pad_left - 8}" y="{y + 4:.1f}" fill="{t.muted}" text-anchor="end" '
                f'font-family="system-ui,sans-serif" font-size="10">{tick} °C</text>'
            )
        tick += step

    # The trace, split into in-range and out-of-range polylines so breaches read at a glance.
    def segments(out_of_range: bool) -> list[list[tuple[float, float]]]:
        runs: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for minutes, temp in zip(elapsed, temps, strict=True):
            breached = temp > label_upper_c or temp < label_lower_c
            if breached == out_of_range:
                current.append((px(minutes), py(temp)))
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)
        return runs

    for colour, width, is_breach in ((t.trace, 1.6, False), (t.breach, 2.6, True)):
        for run in segments(is_breach):
            if len(run) == 1:
                # A polyline of one point renders nothing, which silently hid the single
                # most demo-relevant case: one isolated reading outside the envelope. Draw
                # it as a dot so a spike between two in-range samples is visible.
                x, y = run[0]
                out.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{width + 0.6:.1f}" '
                    f'fill="{colour}"/>'
                )
                continue
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in run)
            out.append(
                f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'
            )

    # X axis: elapsed hours, five ticks.
    total_hours = total_minutes / 60.0
    for i in range(6):
        frac = i / 5
        x = t.pad_left + plot_w * frac
        out.append(
            f'<text x="{x:.1f}" y="{t.height - t.pad_bottom + 18}" fill="{t.muted}" '
            f'text-anchor="middle" font-family="system-ui,sans-serif" font-size="10">'
            f'{total_hours * frac:.1f} h</text>'
        )

    legend = [
        (t.in_band, f"labelled {label_lower_c:g}–{label_upper_c:g} °C"),
        (t.breach, "out of labelled range"),
    ]
    if excursion_lower_c is not None and excursion_upper_c is not None:
        legend.insert(
            1,
            (t.allowed_band, f"excursion permitted {excursion_lower_c:g}–{excursion_upper_c:g} °C"),
        )

    lx = t.pad_left
    for colour, text in legend:
        out.append(
            f'<rect x="{lx}" y="{t.height - 16}" width="10" height="10" fill="{colour}" rx="2"/>'
            f'<text x="{lx + 15}" y="{t.height - 7}" fill="{t.muted}" '
            f'font-family="system-ui,sans-serif" font-size="10">{escape(text)}</text>'
        )
        lx += 22 + int(6.0 * len(text))

    out.append("</svg>")
    return "".join(out)
