import sys
import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = word if not current_line else f"{current_line} {word}"
        width = draw.textlength(test_line, font=font)
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return "\n".join(lines)


def round_corners(img, radius=40):
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    img.putalpha(mask)
    return img


def make_postcard(
    headline,
    template_path=Path(__file__).resolve().parent / "assets" / "template.png",
    out_path="postcard_final.png",
    font_path=None,
    corner_radius=40,
):
    font_path = font_path or os.getenv("POSTCARD_FONT")
    font_candidates = [font_path] if font_path else [
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for candidate in font_candidates:
        try:
            ImageFont.truetype(candidate, 20)
            font_path = candidate
            break
        except OSError:
            continue
    else:
        raise FileNotFoundError("No bold TrueType font found. Set POSTCARD_FONT to a font file path.")

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # ---------------------------
    # HEADLINE AREA
    # ---------------------------
    # Headline area scales with the template and stays above the footer icons.
    width, height = img.size
    text_box = (int(width * 0.03), int(height * 0.42), int(width * 0.97), int(height * 0.73))
    horizontal_padding = 25
    max_width = (text_box[2] - text_box[0]) - horizontal_padding
    max_height = text_box[3] - text_box[1]

    font_size = 100
    min_font_size = 20
    line_spacing = 10

    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size)
        wrapped_text = wrap_text(
            draw,
            headline,
            font,
            max_width,
        )
        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped_text,
            font=font,
            spacing=line_spacing,
        )
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= max_width and text_height <= max_height:
            break
        font_size -= 2
    else:
        raise ValueError("Headline is too long to fit the postcard. Shorten it or use a larger template.")

    # ---------------------------
    # SHADOW
    # ---------------------------
    shadow_offset = 3
    draw.multiline_text(
        (text_box[0] + shadow_offset, text_box[1] + shadow_offset),
        wrapped_text,
        font=font,
        fill=(0, 0, 0, 180),
        spacing=line_spacing,
        align="left",
    )

    # ---------------------------
    # MAIN TEXT
    # ---------------------------
    draw.multiline_text(
        (text_box[0], text_box[1]),
        wrapped_text,
        font=font,
        fill=(255, 255, 255),
        spacing=line_spacing,
        align="left",
    )

    img = round_corners(img, radius=corner_radius)
    img.save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        headline = sys.argv[1]
    elif os.path.exists("story_output.json"):
        with open("story_output.json", "r", encoding="utf-8") as f:
            headline = json.load(f)["headline"]
    else:
        headline = "Test headline goes here"
    make_postcard(headline)