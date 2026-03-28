from PIL import Image, ImageDraw

def create_icon():
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    draw.ellipse([4, 4, size-4, size-4], fill=(52, 152, 219, 255))
    
    monitor_x = 16
    monitor_y = 18
    monitor_width = 32
    monitor_height = 24
    
    draw.rectangle(
        [monitor_x, monitor_y, monitor_x + monitor_width, monitor_y + monitor_height],
        fill=(255, 255, 255, 255),
        outline=(255, 255, 255, 255),
        width=2
    )
    
    stand_x = monitor_x + monitor_width // 2 - 4
    stand_y = monitor_y + monitor_height
    stand_width = 8
    stand_height = 6
    
    draw.rectangle(
        [stand_x, stand_y, stand_x + stand_width, stand_y + stand_height],
        fill=(255, 255, 255, 255)
    )
    
    base_x = monitor_x + monitor_width // 2 - 8
    base_y = stand_y + stand_height
    base_width = 16
    base_height = 3
    
    draw.rectangle(
        [base_x, base_y, base_x + base_width, base_y + base_height],
        fill=(255, 255, 255, 255)
    )
    
    return image

if __name__ == "__main__":
    icon = create_icon()
    icon.save("icon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("图标文件 icon.ico 已创建")
