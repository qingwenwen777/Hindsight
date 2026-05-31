"""生成桌面应用图标 build/icon.ico（浅色底 + 蜡烛图，呼应 TradeAI 亮色主题）。

用 Pillow 直接绘制多分辨率图标，无需 SVG 渲染依赖。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "build" / "icon.ico"
OUT.parent.mkdir(parents=True, exist_ok=True)

# 以 256 为基准绘制，再缩放出多尺寸
SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 圆角浅色底（亮色主题）
radius = 56
d.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=(255, 255, 255, 255))
# 极淡描边，避免白底在浅色任务栏上糊掉
d.rounded_rectangle([1, 1, SIZE - 2, SIZE - 2], radius=radius - 1, outline=(226, 226, 229, 255), width=3)

# 蜡烛图：三根 K 线（影线 + 实体），强调色与涨跌色
accent = (41, 98, 255, 255)
up = (0, 137, 123, 255)
muted = (107, 114, 128, 255)

def candle(cx: int, wick_top: int, wick_bot: int, body_top: int, body_bot: int, color):
    half_w = 18
    # 影线
    d.line([(cx, wick_top), (cx, wick_bot)], fill=color, width=10)
    # 实体
    d.rounded_rectangle(
        [cx - half_w, body_top, cx + half_w, body_bot], radius=8, fill=color
    )

candle(78, 70, 200, 104, 168, muted)
candle(128, 48, 214, 84, 150, up)
candle(178, 92, 184, 116, 160, accent)

# 多分辨率写入 ico
sizes = [16, 24, 32, 48, 64, 128, 256]
img.save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
print(f"icon written: {OUT}")
