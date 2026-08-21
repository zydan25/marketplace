from pathlib import Path
from PIL import Image

source_icon = Path("/home/ubuntu/upload/S_20260817_142721_٠٠٠٠.jpg")
source_welcome = Path("/home/ubuntu/upload/S_20260817_142721_٠٠٠٠.jpg")
assets = Path("/home/ubuntu/true-discount-fashion/assets/images")

# The user selected the complete brand lockup as the launcher icon. A centered
# square crop keeps the mark, Arabic name, and FASHION line without distortion.
with Image.open(source_icon).convert("RGB") as original:
    top = (original.height - original.width) // 2
    icon = original.crop((0, top, original.width, top + original.width)).resize((1024, 1024), Image.Resampling.LANCZOS)
    for name in ("icon.png", "splash-icon.png", "favicon.png", "android-icon-foreground.png"):
        icon.save(assets / name, "PNG", optimize=True)

with Image.open(source_welcome).convert("RGB") as original:
    original.save(assets / "welcome-logo.png", "PNG", optimize=True)
