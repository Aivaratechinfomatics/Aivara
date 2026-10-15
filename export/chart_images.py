"""
export/chart_images.py — Plotly figure -> static PNG bytes (kaleido), sized
for slide placement.

This module never touches the network and never rebuilds a chart with a
different library — it re-renders the exact same Plotly figure object that
was already built for the on-screen dashboard (ui/components.py), so the
deck matches what the user saw.

Resolution target: 1920 × 1080 px source at scale=2 gives 3840 × 2160 raw
pixels, which is more than enough for a crisp 13.33" × 7.5" slide at 300 dpi.
We intentionally render charts wide so that cropping to the actual slide area
never loses resolution.
"""

from __future__ import annotations

import concurrent.futures
import io
import os

# Full-slide render target: 1920 × 1080 corresponds to the 16:9 slide at
# 144 dpi (1920 / 13.33 = 144). scale=2 doubles that to ~288 dpi — crisp
# enough for print-quality output.
FULL_WIDTH_PX = 1920
FULL_HEIGHT_PX = 1080
FULL_SCALE = 2

# Half-slide (chart sits beside a text panel)
HALF_WIDTH_PX = 1080
HALF_HEIGHT_PX = 720

# Tall chart (drivers waterfall)
TALL_WIDTH_PX = 900
TALL_HEIGHT_PX = 820

DEFAULT_SCALE = 2
KALEIDO_TIMEOUT_SECONDS: float = float(os.environ.get("AIVARA_KALEIDO_TIMEOUT", "15.0"))


def figure_to_png_bytes(
    fig,
    width: int = FULL_WIDTH_PX,
    height: int = FULL_HEIGHT_PX,
    scale: int = DEFAULT_SCALE,
    timeout: float = KALEIDO_TIMEOUT_SECONDS,
) -> bytes:
    """Render a Plotly figure to PNG bytes via the kaleido engine, fully
    offline. Wraps rendering in a timeout to survive kaleido hang modes."""

    def _render() -> bytes:
        return fig.to_image(format="png", width=width, height=height, scale=scale)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_render)
            return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as exc:
        raise TimeoutError(f"Plotly figure export timed out after {timeout:.1f} seconds.") from exc
    except Exception as exc:
        raise RuntimeError(
            "Could not export chart to PNG — is the 'kaleido' package installed? "
            f"Original error: {exc}"
        ) from exc


def figure_to_png_stream(fig, **kwargs) -> io.BytesIO:
    return io.BytesIO(figure_to_png_bytes(fig, **kwargs))
