
from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Optional


def _safe(value: object) -> str:
    return html.escape(str(value or "").strip())


def _image_to_data_uri(logo_path: Optional[str]) -> str:
    if not logo_path:
        return ""

    path = Path(str(logo_path))
    if not path.exists():
        for candidate in [
            Path.cwd() / str(logo_path),
            Path.cwd() / "assets" / str(logo_path),
            Path.cwd() / "uploads" / str(logo_path),
            Path.cwd() / "data" / str(logo_path),
        ]:
            if candidate.exists():
                path = candidate
                break

    if not path.exists() or not path.is_file():
        return ""

    suffix = path.suffix.lower()
    mime = "image/png"
    if suffix in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    elif suffix == ".webp":
        mime = "image/webp"

    try:
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def _split_university_name(name: str, max_chars: int = 24) -> list[str]:
    clean = str(name or "").strip()
    if not clean:
        return ["University"]

    words = clean.split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == 1:
                break

    if current and len(lines) < 2:
        lines.append(current)

    if not lines:
        lines = [clean[:max_chars]]

    return lines[:2]


def show_ieqas_badge(
    university_name: str,
    logo_path: Optional[str] = None,
    valid_until: str = "",
    status: str = "Excellent Accredited Institution",
    size: int = 190,
) -> str:
    university_name_safe = _safe(university_name)
    valid_until_safe = _safe(valid_until or "—")
    status_safe = _safe(status or "Excellent Accredited Institution")

    logo_data_uri = _image_to_data_uri(logo_path)
    lines = _split_university_name(university_name)
    line1 = _safe(lines[0])
    line2 = _safe(lines[1]) if len(lines) > 1 else ""

    if logo_data_uri:
        logo_markup = f'<image href="{logo_data_uri}" x="68" y="80" width="64" height="42" preserveAspectRatio="xMidYMid meet" />'
    else:
        fallback_letter = _safe((university_name or "U")[:1].upper())
        logo_markup = (
            '<circle cx="100" cy="101" r="22" fill="#EEF3FF" stroke="#D6B85A" stroke-width="1.2" />'
            f'<text x="100" y="108" text-anchor="middle" font-size="20" font-weight="900" fill="#0B2E69">{fallback_letter}</text>'
        )

    svg = f"""
    <div class="ieqas-component-wrap" style="--ieqas-size:{int(size)}px;">
      <svg class="ieqas-component-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{university_name_safe} IEQAS badge">
        <defs>
          <linearGradient id="ieqasGold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#FFF2BF"/>
            <stop offset="30%" stop-color="#E7CD75"/>
            <stop offset="62%" stop-color="#C7A13D"/>
            <stop offset="100%" stop-color="#F9E9A9"/>
          </linearGradient>
          <linearGradient id="ieqasBlue" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#123C82"/>
            <stop offset="100%" stop-color="#061F55"/>
          </linearGradient>
          <path id="ieqasTopArc" d="M 24 100 A 76 76 0 0 1 176 100" />
          <path id="ieqasBottomArc" d="M 176 100 A 76 76 0 0 1 24 100" />
          <filter id="ieqasSoftShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#111827" flood-opacity="0.12"/>
          </filter>
        </defs>

        <circle cx="100" cy="100" r="97" fill="url(#ieqasGold)" filter="url(#ieqasSoftShadow)" />
        <circle cx="100" cy="100" r="82" fill="#FFF9E6" opacity="0.96" />
        <circle cx="100" cy="100" r="73" fill="#FFFFFF" stroke="#DEC16A" stroke-width="1.4" />

        <text font-size="9.4" font-weight="800" letter-spacing="1.25" fill="#111111">
          <textPath href="#ieqasTopArc" startOffset="50%" text-anchor="middle">MINISTRY OF EDUCATION • MINISTRY OF EDUCATION</textPath>
        </text>
        <text font-size="8.2" font-weight="800" letter-spacing="1.05" fill="#111111">
          <textPath href="#ieqasBottomArc" startOffset="50%" text-anchor="middle">MINISTRY OF EDUCATION • REPUBLIC OF KOREA • IEQAS</textPath>
        </text>

        <g class="ieqas-taegeuk-marks">
          <g transform="translate(100,18) scale(.78)">
            <circle r="7.2" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
            <path d="M0,-6.2a6.2,6.2 0 1,1 0,12.4a3.1,3.1 0 1,0 0,-6.2z" fill="#C60C30"/>
            <path d="M0,-6.2a3.1,3.1 0 1,0 0,6.2a6.2,6.2 0 1,1 0,12.4z" fill="#0047A0"/>
          </g>
          <g transform="translate(166,55) scale(.65)">
            <circle r="7.2" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
            <path d="M0,-6.2a6.2,6.2 0 1,1 0,12.4a3.1,3.1 0 1,0 0,-6.2z" fill="#C60C30"/>
            <path d="M0,-6.2a3.1,3.1 0 1,0 0,6.2a6.2,6.2 0 1,1 0,12.4z" fill="#0047A0"/>
          </g>
          <g transform="translate(166,145) scale(.65)">
            <circle r="7.2" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
            <path d="M0,-6.2a6.2,6.2 0 1,1 0,12.4a3.1,3.1 0 1,0 0,-6.2z" fill="#C60C30"/>
            <path d="M0,-6.2a3.1,3.1 0 1,0 0,6.2a6.2,6.2 0 1,1 0,12.4z" fill="#0047A0"/>
          </g>
          <g transform="translate(34,55) scale(.65)">
            <circle r="7.2" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
            <path d="M0,-6.2a6.2,6.2 0 1,1 0,12.4a3.1,3.1 0 1,0 0,-6.2z" fill="#C60C30"/>
            <path d="M0,-6.2a3.1,3.1 0 1,0 0,6.2a6.2,6.2 0 1,1 0,12.4z" fill="#0047A0"/>
          </g>
          <g transform="translate(34,145) scale(.65)">
            <circle r="7.2" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
            <path d="M0,-6.2a6.2,6.2 0 1,1 0,12.4a3.1,3.1 0 1,0 0,-6.2z" fill="#C60C30"/>
            <path d="M0,-6.2a3.1,3.1 0 1,0 0,6.2a6.2,6.2 0 1,1 0,12.4z" fill="#0047A0"/>
          </g>
        </g>

        <text x="100" y="43" text-anchor="middle" font-size="8.6" font-weight="800" fill="#111111">Ministry of Education Designated</text>
        <text x="100" y="53" text-anchor="middle" font-size="7.4" font-weight="760" fill="#111111">International Education Quality Assurance System</text>

        <rect x="39" y="60" width="122" height="17" rx="2.2" fill="url(#ieqasBlue)" />
        <text x="100" y="72" text-anchor="middle" font-size="9.1" font-weight="900" fill="#FFFFFF">{status_safe}</text>

        {logo_markup}
        <text x="100" y="132" text-anchor="middle" font-size="13.5" font-weight="950" fill="#0B2E69">ACCREDITED INSTITUTION</text>
        <text x="100" y="144" text-anchor="middle" font-size="8.4" font-weight="820" fill="#0B2E69">{line1}</text>
        <text x="100" y="154" text-anchor="middle" font-size="8.4" font-weight="820" fill="#0B2E69">{line2}</text>

        <text x="100" y="169" text-anchor="middle" font-size="13" font-weight="950" fill="#111111">IEQAS</text>
        <text x="100" y="180" text-anchor="middle" font-size="5.9" font-weight="740" fill="#111111">Institution accreditation valid until {valid_until_safe}</text>
        <text x="100" y="188" text-anchor="middle" font-size="5.9" font-weight="740" fill="#111111">Ministry of Education, Republic of Korea</text>
      </svg>
    </div>
    """

    return svg


IEQAS_BADGE_CSS = """
<style>
.ieqas-component-wrap {
    width: var(--ieqas-size, 190px);
    height: var(--ieqas-size, 190px);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent !important;
    vertical-align: middle;
}
.ieqas-component-svg {
    width: 100%;
    height: 100%;
    display: block;
    background: transparent !important;
    overflow: visible;
}
@media (max-width: 768px) {
    .ieqas-component-wrap {
        width: min(var(--ieqas-size, 190px), 34vw);
        height: min(var(--ieqas-size, 190px), 34vw);
    }
}
</style>
"""
