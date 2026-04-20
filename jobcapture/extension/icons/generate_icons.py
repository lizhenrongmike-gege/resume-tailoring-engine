"""Generate JobCapture extension icons."""
from PIL import Image, ImageDraw, ImageFont
import math

def create_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background — indigo gradient feel
    margin = int(size * 0.08)
    radius = int(size * 0.22)

    # Draw rounded rect background
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(67, 56, 202),  # #4338ca indigo
    )

    # Add a subtle lighter overlay on top portion for depth
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [margin, margin, size - margin, int(size * 0.55)],
        radius=radius,
        fill=(99, 102, 241, 40),  # subtle lighter indigo
    )
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Draw a briefcase/capture icon
    cx, cy = size // 2, int(size * 0.52)

    # Briefcase body
    bw = int(size * 0.52)  # width
    bh = int(size * 0.36)  # height
    br = int(size * 0.06)  # corner radius
    draw.rounded_rectangle(
        [cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
        radius=br,
        fill=None,
        outline="white",
        width=max(2, int(size * 0.04)),
    )

    # Briefcase handle
    hw = int(size * 0.24)
    hh = int(size * 0.14)
    draw.rounded_rectangle(
        [cx - hw // 2, cy - bh // 2 - hh, cx + hw // 2, cy - bh // 2 + max(1, int(size * 0.02))],
        radius=max(2, int(size * 0.04)),
        fill=None,
        outline="white",
        width=max(2, int(size * 0.04)),
    )

    # Crosshair/capture circle in center of briefcase
    cr = int(size * 0.09)
    draw.ellipse(
        [cx - cr, cy - cr, cx + cr, cy + cr],
        fill=None,
        outline="white",
        width=max(1, int(size * 0.03)),
    )
    # Small dot in center
    dot = max(1, int(size * 0.04))
    draw.ellipse(
        [cx - dot, cy - dot, cx + dot, cy + dot],
        fill="white",
    )

    return img

for s in [16, 48, 128]:
    icon = create_icon(s)
    icon.save(f"/Users/lizhenrong/Downloads/resume_tailoring_skill/jobcapture/extension/icons/icon{s}.png")
    print(f"Created icon{s}.png")
