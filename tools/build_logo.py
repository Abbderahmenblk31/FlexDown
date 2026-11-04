"""
Script to generate the official modern FlexDown application logo and multi-size ICO icon.
"""
from pathlib import Path
from PyQt6.QtGui import (
    QImage, QPainter, QColor, QLinearGradient, QRadialGradient,
    QPainterPath, QPen, QBrush
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PIL import Image


def generate_flexdown_logo():
    size = 512
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # 1. Background Squircle
    pad = 28
    radius = 110
    bg_rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)
    bg_path = QPainterPath()
    bg_path.addRoundedRect(bg_rect, radius, radius)

    # Dark cybernetic gradient fill
    bg_grad = QLinearGradient(0, pad, 0, size - pad)
    bg_grad.setColorAt(0.0, QColor(22, 30, 52))    # Midnight Blue
    bg_grad.setColorAt(0.5, QColor(14, 18, 33))    # Deep Navy
    bg_grad.setColorAt(1.0, QColor(8, 10, 20))     # Near Black
    p.fillPath(bg_path, QBrush(bg_grad))

    # Ambient radial glow inside squircle
    center_glow = QRadialGradient(size / 2, size / 2, 220)
    center_glow.setColorAt(0.0, QColor(0, 229, 255, 45))   # Cyan glow
    center_glow.setColorAt(0.6, QColor(233, 69, 96, 25))   # Coral glow
    center_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillPath(bg_path, QBrush(center_glow))

    # Glowing border gradient
    border_grad = QLinearGradient(pad, pad, size - pad, size - pad)
    border_grad.setColorAt(0.0, QColor(0, 245, 255, 230))   # Vibrant Cyan
    border_grad.setColorAt(0.4, QColor(59, 130, 246, 180))  # Royal Blue
    border_grad.setColorAt(0.8, QColor(168, 85, 247, 180))  # Electric Purple
    border_grad.setColorAt(1.0, QColor(233, 69, 96, 230))   # Flex Neon Coral

    border_pen = QPen(QBrush(border_grad), 7)
    p.setPen(border_pen)
    p.drawPath(bg_path)

    # 2. Main Speed Download Arrow
    # Arrow Body (Stem + Triangular Head with modern sleek angles)
    # Center X = 256
    cx = 256.0

    # Arrow Path
    arrow_path = QPainterPath()
    # Shaft top
    arrow_path.moveTo(cx - 36, 110)
    arrow_path.lineTo(cx + 36, 110)
    # Shaft down
    arrow_path.lineTo(cx + 36, 235)
    # Arrow head wings
    arrow_path.lineTo(cx + 95, 235)
    # Arrow tip
    arrow_path.lineTo(cx, 340)
    # Arrow left wing
    arrow_path.lineTo(cx - 95, 235)
    # Shaft left
    arrow_path.lineTo(cx - 36, 235)
    arrow_path.closeSubpath()

    # Arrow Gradient (Electric Cyan -> Blue -> Neon Coral)
    arrow_grad = QLinearGradient(0, 110, 0, 340)
    arrow_grad.setColorAt(0.0, QColor(0, 240, 255))    # Cyan
    arrow_grad.setColorAt(0.45, QColor(56, 125, 255))  # Electric Blue
    arrow_grad.setColorAt(0.85, QColor(233, 69, 96))   # Coral
    arrow_grad.setColorAt(1.0, QColor(255, 75, 43))    # Vivid Flame

    p.fillPath(arrow_path, QBrush(arrow_grad))

    # Sleek inner highlight on arrow
    arrow_highlight_pen = QPen(QColor(255, 255, 255, 140), 3)
    p.setPen(arrow_highlight_pen)
    p.drawPath(arrow_path)

    # 3. Modern Receiving Dock / Tray
    tray_path = QPainterPath()
    tray_top_y = 330
    tray_bot_y = 390
    tray_w_outer = 145
    _tray_w_inner = 100  # noqa: F841

    # Left hook
    tray_path.moveTo(cx - tray_w_outer, tray_top_y)
    tray_path.lineTo(cx - tray_w_outer, tray_bot_y)
    tray_path.lineTo(cx + tray_w_outer, tray_bot_y)
    tray_path.lineTo(cx + tray_w_outer, tray_top_y)

    # Lower bracket stroke
    tray_pen = QPen(QBrush(arrow_grad), 22, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(tray_pen)
    p.drawPath(tray_path)

    # Speed lines / Velocity accents
    accent_pen = QPen(QColor(0, 240, 255, 180), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(accent_pen)
    # Left pulse
    p.drawLine(QPointF(cx - 130, 185), QPointF(cx - 130, 225))
    p.drawLine(QPointF(cx - 150, 200), QPointF(cx - 150, 215))
    # Right pulse
    p.drawLine(QPointF(cx + 130, 185), QPointF(cx + 130, 225))
    p.drawLine(QPointF(cx + 150, 200), QPointF(cx + 150, 215))

    p.end()

    # Save PNG files
    out_dir = Path("resources/icons")
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "app.png"
    logo_path = out_dir / "logo.png"
    img.save(str(png_path), "PNG")
    img.save(str(logo_path), "PNG")

    # Generate multi-size ICO using Pillow
    pil_img = Image.open(str(png_path))
    ico_path = out_dir / "app.ico"
    pil_img.save(
        str(ico_path),
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )

    print(f"Generated successfully:\n - {png_path}\n - {logo_path}\n - {ico_path}")


if __name__ == "__main__":
    generate_flexdown_logo()
