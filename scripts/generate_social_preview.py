"""Generate social preview image (1200x630) for Twitter/X cards and OG sharing."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def generate_social_preview(output_path: str = "assets/social-preview.png") -> None:
    W, H = 1200, 630
    BG_COLOR = (26, 26, 46)  # #1a1a2e — dark theme background
    ACCENT_GREEN = (0, 200, 83)  # BBB green accent
    ACCENT_BLUE = (30, 144, 255)  # secondary accent

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Gradient bar at top
    for x in range(W):
        ratio = x / W
        r = int(ACCENT_GREEN[0] * (1 - ratio) + ACCENT_BLUE[0] * ratio)
        g = int(ACCENT_GREEN[1] * (1 - ratio) + ACCENT_BLUE[1] * ratio)
        b = int(ACCENT_GREEN[2] * (1 - ratio) + ACCENT_BLUE[2] * ratio)
        draw.line([(x, 0), (x, 5)], fill=(r, g, b))

    # Bottom accent bar
    for x in range(W):
        ratio = x / W
        r = int(ACCENT_BLUE[0] * (1 - ratio) + ACCENT_GREEN[0] * ratio)
        g = int(ACCENT_BLUE[1] * (1 - ratio) + ACCENT_GREEN[1] * ratio)
        b = int(ACCENT_BLUE[2] * (1 - ratio) + ACCENT_GREEN[2] * ratio)
        draw.line([(x, H - 5), (x, H)], fill=(r, g, b))

    # Try to load a nice font, fall back to default
    def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        for fp in font_paths:
            if Path(fp).exists():
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    font_title = get_font(72)
    font_subtitle = get_font(36)
    font_divider = get_font(26)
    font_footer = get_font(22)

    # Title: "BBB 26"
    title = "BBB 26"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, 120), title, fill=(255, 255, 255), font=font_title)

    # Subtitle: "Painel de Reações"
    subtitle = "Painel de Reações"
    bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    sw = bbox[2] - bbox[0]
    draw.text(((W - sw) / 2, 220), subtitle, fill=(180, 180, 200), font=font_subtitle)

    # Decorative divider line
    div_y = 290
    div_w = 400
    for x in range(int((W - div_w) / 2), int((W + div_w) / 2)):
        ratio = (x - (W - div_w) / 2) / div_w
        r = int(ACCENT_GREEN[0] * (1 - ratio) + ACCENT_BLUE[0] * ratio)
        g = int(ACCENT_GREEN[1] * (1 - ratio) + ACCENT_BLUE[1] * ratio)
        b = int(ACCENT_GREEN[2] * (1 - ratio) + ACCENT_BLUE[2] * ratio)
        draw.point((x, div_y), fill=(r, g, b))
        draw.point((x, div_y + 1), fill=(r, g, b))

    # Category labels as styled text
    categories = [
        ("Queridometro", ACCENT_GREEN),
        ("Paredoes", (255, 200, 60)),
        ("Provas", (100, 180, 255)),
        ("Cartola", (255, 120, 80)),
    ]
    total_w = 0
    gap = 40
    for label, _ in categories:
        bbox = draw.textbbox((0, 0), label, font=font_divider)
        total_w += bbox[2] - bbox[0]
    total_w += gap * (len(categories) - 1)

    cx = (W - total_w) / 2
    for label, color in categories:
        bbox = draw.textbbox((0, 0), label, font=font_divider)
        lw = bbox[2] - bbox[0]
        draw.text((cx, 320), label, fill=color, font=font_divider)
        cx += lw + gap

    # Tagline
    tagline = "Analise estrategica completa do Big Brother Brasil 2026"
    bbox = draw.textbbox((0, 0), tagline, font=font_footer)
    tgw = bbox[2] - bbox[0]
    draw.text(((W - tgw) / 2, 410), tagline, fill=(120, 120, 150), font=font_footer)

    # URL footer
    url = "ferazambuja.github.io/BBB26"
    bbox = draw.textbbox((0, 0), url, font=font_footer)
    uw = bbox[2] - bbox[0]
    draw.text(((W - uw) / 2, 520), url, fill=ACCENT_GREEN, font=font_footer)

    # Decorative corner elements
    corner_size = 30
    draw.line([(20, 20), (20 + corner_size, 20)], fill=ACCENT_GREEN, width=2)
    draw.line([(20, 20), (20, 20 + corner_size)], fill=ACCENT_GREEN, width=2)
    draw.line([(W - 20, 20), (W - 20 - corner_size, 20)], fill=ACCENT_GREEN, width=2)
    draw.line([(W - 20, 20), (W - 20, 20 + corner_size)], fill=ACCENT_GREEN, width=2)
    draw.line([(20, H - 20), (20 + corner_size, H - 20)], fill=ACCENT_BLUE, width=2)
    draw.line([(20, H - 20), (20, H - 20 - corner_size)], fill=ACCENT_BLUE, width=2)
    draw.line([(W - 20, H - 20), (W - 20 - corner_size, H - 20)], fill=ACCENT_BLUE, width=2)
    draw.line([(W - 20, H - 20), (W - 20, H - 20 - corner_size)], fill=ACCENT_BLUE, width=2)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90)
    print(f"Social preview saved: {out} ({out.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    generate_social_preview()
