"""Generate high-resolution application icons for CodeLens AI."""

from pathlib import Path
from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

PNG_PATH = ASSETS_DIR / "icon.png"
ICO_PATH = ASSETS_DIR / "icon.ico"


def create_icon(size: int = 256) -> Image.Image:
    # 32-bit RGBA canvas
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rectangle (Matte graphite with subtle gradient)
    pad = int(size * 0.06)
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=(12, 17, 26, 255),
        outline=(56, 189, 248, 200),
        width=int(size * 0.03),
    )

    # Inner glowing border
    inner_pad = pad + int(size * 0.03)
    draw.rounded_rectangle(
        [inner_pad, inner_pad, size - inner_pad, size - inner_pad],
        radius=radius - int(size * 0.03),
        outline=(56, 189, 248, 60),
        width=int(size * 0.015),
    )

    # Code brackets < / > in vibrant cyan & emerald
    c_x, c_y = size // 2, size // 2
    sw = int(size * 0.065)

    # Left bracket <
    l_points = [
        (c_x - int(size * 0.16), c_y - int(size * 0.22)),
        (c_x - int(size * 0.32), c_y),
        (c_x - int(size * 0.16), c_y + int(size * 0.22)),
    ]
    draw.line([l_points[0], l_points[1]], fill=(56, 189, 248, 255), width=sw, joint="curve")
    draw.line([l_points[1], l_points[2]], fill=(56, 189, 248, 255), width=sw, joint="curve")

    # Slash /
    s_p1 = (c_x + int(size * 0.06), c_y - int(size * 0.26))
    s_p2 = (c_x - int(size * 0.06), c_y + int(size * 0.26))
    draw.line([s_p1, s_p2], fill=(45, 212, 191, 255), width=sw)

    # Right bracket >
    r_points = [
        (c_x + int(size * 0.16), c_y - int(size * 0.22)),
        (c_x + int(size * 0.32), c_y),
        (c_x + int(size * 0.16), c_y + int(size * 0.22)),
    ]
    draw.line([r_points[0], r_points[1]], fill=(56, 189, 248, 255), width=sw, joint="curve")
    draw.line([r_points[1], r_points[2]], fill=(56, 189, 248, 255), width=sw, joint="curve")

    # Core AI pulse dot
    dot_r = int(size * 0.035)
    draw.ellipse(
        [c_x - dot_r, c_y - dot_r, c_x + dot_r, c_y + dot_r],
        fill=(16, 185, 129, 255),
        outline=(255, 255, 255, 220),
        width=int(size * 0.01),
    )

    return img


def main() -> None:
    img256 = create_icon(256)
    img256.save(PNG_PATH, format="PNG")
    print(f"Generated {PNG_PATH}")

    # Generate multi-resolution .ico
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img256.save(ICO_PATH, format="ICO", sizes=sizes)
    print(f"Generated {ICO_PATH}")


if __name__ == "__main__":
    main()
