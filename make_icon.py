from PIL import Image, ImageDraw, ImageFont

# Размер иконки
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Рисуем темный фон со скругленными углами (радиус 50)
draw.rounded_rectangle([10, 10, size-10, size-10], radius=50, fill=(30, 30, 30, 255), outline=(218, 165, 32, 255), width=6)

# Пытаемся найти системный шрифт (Segoe UI)
# Увеличили размер шрифта с 160 до 200 (ровно на 25%)
try:
    font = ImageFont.truetype("segoeui.ttf", 205)
except:
    font = ImageFont.load_default()

# Цвет букв (Золотой #DAA520)
gold_color = (218, 165, 32, 255)

# Первая буква P (Левее и Выше, полупрозрачная для глубины)
# Сдвинули немного, чтобы большая буква не прилипала к краю
draw.text((20, -40), "P", font=font, fill=(218, 165, 32, 180))

# Вторая буква P (Правее и Ниже, яркая)
draw.text((120, 10), "P", font=font, fill=gold_color)

# Сохраняем сразу в правильном формате .ico
img.save("app.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("Иконка app.ico успешно создана!")