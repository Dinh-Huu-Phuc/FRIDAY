from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesktopColors:
    canvas: str = "#02060d"
    canvas_deep: str = "#01040a"
    surface: str = "#07111a"
    surface_raised: str = "#0a1722"
    surface_soft: str = "#0c1b27"
    border: str = "#173247"
    border_bright: str = "#266a89"
    text: str = "#e9f7ff"
    text_soft: str = "#a3bac8"
    text_muted: str = "#668092"
    cyan: str = "#50e8ff"
    blue: str = "#318dff"
    violet: str = "#a85cff"
    magenta: str = "#f052d4"
    amber: str = "#ff9a62"
    success: str = "#44efa0"
    warning: str = "#f5c66c"
    danger: str = "#ff7682"


COLORS = DesktopColors()
