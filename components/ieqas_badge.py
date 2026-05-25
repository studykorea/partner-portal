
from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Optional


def _safe(value: object) -> str:
    return html.escape(str(value or "").strip())


def _image_to_data_uri(logo_path: Optional[str]) -> str:
    """Return data URI for a local logo file. Empty string if missing/unreadable."""
    if not logo_path:
        return ""

    raw = str(logo_path).strip()
    path = Path(raw)

    candidates = [path]
    if not path.is_absolute():
        candidates.extend([
            Path.cwd() / raw,
            Path.cwd() / "assets" / raw,
            Path.cwd() / "uploads" / raw,
            Path.cwd() / "data" / raw,
            Path.cwd() / "static" / raw,
        ])

    found = None
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            found = candidate
            break

    if not found:
        return ""

    suffix = found.suffix.lower()
    mime = "image/png"
    if suffix in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif suffix == ".svg":
        mime = "image/svg+xml"
    elif suffix == ".webp":
        mime = "image/webp"

    try:
        encoded = base64.b64encode(found.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def _short_name(name: str, max_chars: int = 18) -> str:
    name = str(name or "").strip()
    if len(name) <= max_chars:
        return name
    words = name.split()
    if len(words) >= 2:
        short = " ".join(words[:2])
        if len(short) <= max_chars:
            return short
    return name[:max_chars - 1] + "…"


def show_ieqas_badge(
    university_name: str,
    logo_path: Optional[str] = None,
    valid_until: str = "",
    status: str = "Excellent Accredited Institution",
    size: int = 86,
) -> str:
    """
    Small reusable IEQAS-style badge component.

    Dynamic fields:
    - university_name
    - logo_path
    - valid_until
    - status
    """
    size = max(64, min(int(size or 86), 120))
    university_name_safe = _safe(university_name)
    status_safe = _safe(status or "Excellent Accredited Institution")
    valid_until_safe = _safe(valid_until or "—")
    logo_uri = _image_to_data_uri(logo_path)
    display_name = _safe(_short_name(university_name, 20))

    if logo_uri:
        logo_markup = f'<image href="{logo_uri}" x="40" y="47" width="40" height="25" preserveAspectRatio="xMidYMid meet" />'
    else:
        fallback_letter = _safe((university_name or "U")[:1].upper())
        logo_markup = (
            '<circle cx="60" cy="59" r="13" fill="#EEF3FF" stroke="#C9A13D" stroke-width="0.8" />'
            f'<text x="60" y="64" text-anchor="middle" font-size="13" font-weight="900" fill="#0B2E69">{fallback_letter}</text>'
        )

    # Important: all size controls are inline so the badge cannot become huge.
    return f"""
<span class="ieqas-mini-badge-v173" title="{university_name_safe} • {status_safe} • valid until {valid_until_safe}" style="display:inline-flex;align-items:center;justify-content:center;width:{size}px;height:{size}px;min-width:{size}px;max-width:{size}px;max-height:{size}px;background:transparent;vertical-align:middle;line-height:0;overflow:visible;">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" style="width:{size}px;height:{size}px;max-width:{size}px;max-height:{size}px;display:block;background:transparent;overflow:visible;" aria-label="{university_name_safe} IEQAS badge">
  <defs>
    <linearGradient id="ieqasGoldV173" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#FFF3BF"/>
      <stop offset="35%" stop-color="#E5CC73"/>
      <stop offset="68%" stop-color="#B8942F"/>
      <stop offset="100%" stop-color="#F7E5A4"/>
    </linearGradient>
    <linearGradient id="ieqasBlueV173" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#123D86"/>
      <stop offset="100%" stop-color="#06245E"/>
    </linearGradient>
    <path id="ieqasTopArcV173" d="M 18 60 A 42 42 0 0 1 102 60"/>
    <path id="ieqasBottomArcV173" d="M 102 60 A 42 42 0 0 1 18 60"/>
    <filter id="ieqasShadowV173" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#111827" flood-opacity="0.12"/>
    </filter>
  </defs>

  <circle cx="60" cy="60" r="58" fill="url(#ieqasGoldV173)" filter="url(#ieqasShadowV173)"/>
  <circle cx="60" cy="60" r="49" fill="#FFF9E7"/>
  <circle cx="60" cy="60" r="43" fill="#FFFFFF" stroke="#D8BF66" stroke-width="1"/>

  <text font-size="5.2" font-weight="900" letter-spacing="0.9" fill="#111111">
    <textPath href="#ieqasTopArcV173" startOffset="50%" text-anchor="middle">MINISTRY OF EDUCATION</textPath>
  </text>
  <text font-size="4.6" font-weight="900" letter-spacing="0.6" fill="#111111">
    <textPath href="#ieqasBottomArcV173" startOffset="50%" text-anchor="middle">REPUBLIC OF KOREA • IEQAS</textPath>
  </text>

  <g transform="translate(60,12) scale(.45)">
    <circle r="6.5" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
    <path d="M0,-5.8a5.8,5.8 0 1,1 0,11.6a2.9,2.9 0 1,0 0,-5.8z" fill="#C60C30"/>
    <path d="M0,-5.8a2.9,2.9 0 1,0 0,5.8a5.8,5.8 0 1,1 0,11.6z" fill="#0047A0"/>
  </g>
  <g transform="translate(102,60) scale(.38)">
    <circle r="6.5" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
    <path d="M0,-5.8a5.8,5.8 0 1,1 0,11.6a2.9,2.9 0 1,0 0,-5.8z" fill="#C60C30"/>
    <path d="M0,-5.8a2.9,2.9 0 1,0 0,5.8a5.8,5.8 0 1,1 0,11.6z" fill="#0047A0"/>
  </g>
  <g transform="translate(18,60) scale(.38)">
    <circle r="6.5" fill="#fff" stroke="#C8A64A" stroke-width="1"/>
    <path d="M0,-5.8a5.8,5.8 0 1,1 0,11.6a2.9,2.9 0 1,0 0,-5.8z" fill="#C60C30"/>
    <path d="M0,-5.8a2.9,2.9 0 1,0 0,5.8a5.8,5.8 0 1,1 0,11.6z" fill="#0047A0"/>
  </g>

  <text x="60" y="29" text-anchor="middle" font-size="4.7" font-weight="900" fill="#111111">Ministry of Education Designated</text>
  <text x="60" y="35" text-anchor="middle" font-size="4.1" font-weight="760" fill="#111111">International Education Quality Assurance System</text>

  <rect x="25" y="39" width="70" height="9.5" rx="1.3" fill="url(#ieqasBlueV173)"/>
  <text x="60" y="45.7" text-anchor="middle" font-size="4.8" font-weight="900" fill="#FFFFFF">{status_safe}</text>

  {logo_markup}
  <text x="60" y="79" text-anchor="middle" font-size="7.1" font-weight="950" fill="#0B2E69">ACCREDITED</text>
  <text x="60" y="87" text-anchor="middle" font-size="5.3" font-weight="860" fill="#0B2E69">{display_name}</text>

  <text x="60" y="98" text-anchor="middle" font-size="7.5" font-weight="950" fill="#111111">IEQAS</text>
  <text x="60" y="105" text-anchor="middle" font-size="3.9" font-weight="760" fill="#111111">Valid until {valid_until_safe}</text>
  <text x="60" y="111" text-anchor="middle" font-size="3.4" font-weight="700" fill="#111111">Ministry of Education, Republic of Korea</text>
</svg>
</span>
"""


IEQAS_BADGE_CSS = """
<style>
.ieqas-mini-badge-v173,
.ieqas-mini-badge-v173 svg {
    background: transparent !important;
}
.ieqas-component-wrap,
.ieqas-component-svg {
    background: transparent !important;
}
</style>
"""
