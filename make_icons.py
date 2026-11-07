from PIL import Image, ImageDraw, ImageFont
import os

OUT = r'D:\KimiData\kimi\Workspaces\竞赛软件开发\clue-pool-frontend\public\icons'
os.makedirs(OUT, exist_ok=True)

def make_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆角矩形蓝紫渐变底色（用纯色+高光近似）
    r = int(size * 0.22)
    d.rounded_rectangle([0, 0, size, size], radius=r, fill=(43, 108, 255, 255))
    # 顶部柔和高光（椭圆，不出圆角）
    hl = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    dh = ImageDraw.Draw(hl)
    dh.ellipse([int(size*0.08), int(size*0.04), int(size*0.92), int(size*0.55)], fill=(255, 255, 255, 45))
    img.paste(hl, (0, 0), hl)
    # 中心白色放大镜
    cx, cy = size // 2, int(size * 0.44)
    rad = int(size * 0.20)
    lw = max(2, int(size * 0.045))
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(255, 255, 255, 255), width=lw)
    # 手柄
    x1, y1 = cx + int(rad * 0.72), cy + int(rad * 0.72)
    x2, y2 = x1 + int(size * 0.14), y1 + int(size * 0.14)
    d.line([x1, y1, x2, y2], fill=(255, 255, 255, 255), width=lw)
    # 底部文字 线索池
    try:
        font = ImageFont.truetype('msyhbd.ttc', int(size * 0.13))
    except Exception:
        font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc', int(size * 0.13))
    text = '线索池'
    bb = d.textbbox((0, 0), text, font=font)
    d.text(((size - (bb[2] - bb[0])) / 2, size * 0.70), text, font=font, fill=(255, 255, 255, 255))
    return img

for s in (192, 512):
    make_icon(s).save(os.path.join(OUT, f'icon-{s}.png'))
print('icons done:', os.listdir(OUT))
