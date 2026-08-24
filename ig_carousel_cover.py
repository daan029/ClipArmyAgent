"""
Klipje-branded Instagram carousel cover slide.

Standard "swipe to see" first-slide template: full-bleed background photo,
a circular context inset photo, a divider with the Klipje logo badge, and a
black caption band with a bold Dutch headline + "SWIPE OM TE ZIEN" hint.

Usage:
    python ig_carousel_cover.py --background photo.jpg --headline "DIT MUSEUM IN AMSTERDAM ZIT VOL MET GEKKE RUIMTES" --out cover.jpg
    python ig_carousel_cover.py --background photo.jpg --inset location.jpg --headline "..." --out cover.jpg
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CANVAS_SIZE = (1080, 1350)  # 4:5 IG feed portrait
PHOTO_HEIGHT = 1050
BAND_HEIGHT = CANVAS_SIZE[1] - PHOTO_HEIGHT

KLIPJE_NAVY = (9, 43, 78)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

REPO_ROOT = Path(__file__).parent
DEFAULT_LOGO = REPO_ROOT / "assets" / "klipje_logo.png"

HEADLINE_FONT_PATH = r"C:\Windows\Fonts\impact.ttf"
SUBTEXT_FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"


def _fit_cover(im: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_ratio = im.width / im.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
    im = im.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return im.crop((left, top, left + target_w, top + target_h))


def _circle_crop(im: Image.Image, diameter: int) -> Image.Image:
    im = _fit_cover(im, diameter, diameter)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter, diameter), fill=255)
    out = Image.new("RGBA", (diameter, diameter))
    out.paste(im, (0, 0), mask)
    return out


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.upper().split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_slide(
    background_path: str,
    headline: str,
    out_path: str,
    inset_path: str | None = None,
    subtext: str = "SWIPE OM TE ZIEN",
    logo_path: str = str(DEFAULT_LOGO),
) -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, BLACK)

    photo = _fit_cover(Image.open(background_path).convert("RGB"), CANVAS_SIZE[0], PHOTO_HEIGHT)
    canvas.paste(photo, (0, 0))

    draw = ImageDraw.Draw(canvas)

    if inset_path:
        diameter = 340
        border = 10
        inset = _circle_crop(Image.open(inset_path).convert("RGB"), diameter - 2 * border)
        cx, cy = 60, 90
        shadow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((cx - 6, cy - 6, cx + diameter + 6, cy + diameter + 6), fill=(0, 0, 0, 140))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        canvas.paste(shadow, (0, 0), shadow)
        draw.ellipse((cx, cy, cx + diameter, cy + diameter), fill=WHITE)
        canvas.paste(inset, (cx + border, cy + border), inset)

    # divider
    divider_y = PHOTO_HEIGHT
    draw.line((0, divider_y, CANVAS_SIZE[0], divider_y), fill=(60, 60, 60), width=2)

    # black caption band (drawn before the badge so the badge sits on top, not behind it)
    draw.rectangle((0, PHOTO_HEIGHT, CANVAS_SIZE[0], CANVAS_SIZE[1]), fill=BLACK)

    # logo badge, mostly above the divider so it doesn't sink into the band
    badge_d = 84
    logo = Image.open(logo_path).convert("RGBA")
    logo = _fit_cover(logo.convert("RGB"), badge_d - 12, badge_d - 12).convert("RGBA")
    mask = Image.new("L", logo.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, *logo.size), fill=255)
    bx = CANVAS_SIZE[0] // 2 - badge_d // 2
    by = int(divider_y - badge_d * 0.68)
    draw.ellipse((bx, by, bx + badge_d, by + badge_d), fill=WHITE, outline=KLIPJE_NAVY, width=4)
    canvas.paste(logo, (bx + 6, by + 6), mask)

    pad_x = 56
    max_text_w = CANVAS_SIZE[0] - 2 * pad_x

    sub_font = ImageFont.truetype(SUBTEXT_FONT_PATH, 26)
    text_top = by + badge_d + 22
    text_bottom = CANVAS_SIZE[1] - 74  # leave room for the subtext row
    available_h = text_bottom - text_top

    for size in (64, 58, 52, 46, 40, 36):
        headline_font = ImageFont.truetype(HEADLINE_FONT_PATH, size)
        lines = _wrap_text(draw, headline, headline_font, max_text_w)
        line_h = int(size * 1.05)
        if line_h * len(lines) <= available_h or size == 36:
            break

    text_y = text_top
    for line in lines:
        line_w = draw.textlength(line, font=headline_font)
        line_x = (CANVAS_SIZE[0] - line_w) / 2
        draw.text((line_x, text_y), line, font=headline_font, fill=WHITE)
        text_y += line_h

    # subtext + swipe hint, bottom of band
    tracked = " ".join(subtext.upper())
    sub_w = draw.textlength(tracked, font=sub_font)
    sub_x = (CANVAS_SIZE[0] - sub_w) / 2
    sub_y = CANVAS_SIZE[1] - 56
    draw.text((sub_x, sub_y), tracked, font=sub_font, fill=WHITE)

    arrow_x = sub_x + sub_w + 18
    arrow_y = sub_y + 10
    draw.polygon(
        [(arrow_x, arrow_y - 8), (arrow_x, arrow_y + 8), (arrow_x + 10, arrow_y)],
        fill=KLIPJE_NAVY,
    )

    canvas.convert("RGB").save(out_path, quality=95)


def main():
    ap = argparse.ArgumentParser(description="Render a Klipje-branded IG carousel cover slide.")
    ap.add_argument("--background", required=True)
    ap.add_argument("--inset")
    ap.add_argument("--headline", required=True)
    ap.add_argument("--subtext", default="SWIPE OM TE ZIEN")
    ap.add_argument("--logo", default=str(DEFAULT_LOGO))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    render_slide(args.background, args.headline, args.out, inset_path=args.inset, subtext=args.subtext, logo_path=args.logo)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
