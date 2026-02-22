from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('templates', exist_ok=True)

# Шаблон 1 - Базовый (белый)
img1 = Image.new('RGBA', (800, 600), color=(255, 255, 255, 255))
draw = ImageDraw.Draw(img1)
draw.rectangle([10, 10, 790, 590], outline=(0, 102, 204), width=3)
img1.save('templates/template_1.png')

# Шаблон 2 - Премиум (светло-серый градиент)
img2 = Image.new('RGBA', (800, 600), color=(245, 245, 250, 255))
draw = ImageDraw.Draw(img2)
draw.rectangle([10, 10, 790, 590], outline=(255, 215, 0), width=5)  # Золотая рамка
img2.save('templates/template_2.png')

# Шаблон 3 - WB стиль (фиолетовый)
img3 = Image.new('RGBA', (800, 600), color=(76, 34, 128, 255))  # WB фиолетовый
draw = ImageDraw.Draw(img3)
draw.rectangle([10, 10, 790, 590], outline=(255, 255, 255), width=3)
img3.save('templates/template_3.png')

print("Шаблоны созданы в папке templates/")
