from PIL import Image
import os

src = "robot.png"  # 你的这张图（png）
dst = "app.ico"  # 输出 ico

img = Image.open(src).convert("RGBA")

# 关键：裁掉四周留白，让主体更“占满”
w, h = img.size
# 你可以调这个比例：0.10~0.18 之间试
pad = int(min(w, h) * 0.09)
img2 = img.crop((pad, pad, w - pad, h - pad))

# 再强制变成正方形（居中）
w2, h2 = img2.size
side = min(w2, h2)
left = (w2 - side)//2
top  = (h2 - side)//2
img2 = img2.crop((left, top, left + side, top + side))

# 导出多尺寸 ico（标题栏用 16/24，任务栏用 32/48）
sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
img2.save(dst, format="ICO", sizes=sizes)

print("saved:", os.path.abspath(dst))
