import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageFont, ImageDraw

input_folder = 'images'
output_image_folder = 'images_gen'
output_txt_folder = 'labels_gen'

os.makedirs(output_image_folder, exist_ok=True)
os.makedirs(output_txt_folder, exist_ok=True)

image_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

# 加载字体
font_path = "Minecraftia-Regular.ttf"
font_size1 = 10  # 第一行文字字体大小
font_size2 = 8   # 第二行文字字体大小
font1 = ImageFont.truetype(font_path, font_size1)
font2 = ImageFont.truetype(font_path, font_size2)

target_width = 500  # 目标宽度

def process_image(i):
    try:
        # 随机选择拼接方式：'horizontal' 为左右拼接，'vertical' 为上下拼接
        mode = random.choice(['horizontal', 'vertical'])
        
        # 随机选择两张图片
        selected_images = random.sample(image_files, 2)
        img1 = Image.open(selected_images[0])
        img2 = Image.open(selected_images[1])
        
        if mode == 'horizontal':
            # ----------------------------
            # 左右拼接（水平）：先用原分辨率拼接（顶部对齐），再整体缩放到500宽
            # ----------------------------
            # 获取原始尺寸
            width1, height1 = img1.size
            width2, height2 = img2.size
            
            # 拼接画布尺寸：宽度为两图宽度之和，高度取两图中较高者
            canvas_width = width1 + width2
            canvas_height = max(height1, height2)
            combined = Image.new('RGB', (canvas_width, canvas_height), color='black')
            combined.paste(img1, (0, 0))
            combined.paste(img2, (width1, 0))  # 顶部对齐
            
            # 计算 YOLO 标注（基于原始拼接画布）
            left_center_x = (width1 / 2) / canvas_width
            left_center_y = (height1 / 2) / canvas_height
            left_w_norm = width1 / canvas_width
            left_h_norm = height1 / canvas_height
            yolo1 = f"1 {left_center_x:.6f} {left_center_y:.6f} {left_w_norm:.6f} {left_h_norm:.6f}"
            
            right_center_x = (width1 + width2 / 2) / canvas_width
            right_center_y = (height2 / 2) / canvas_height
            right_w_norm = width2 / canvas_width
            right_h_norm = height2 / canvas_height
            yolo2 = f"2 {right_center_x:.6f} {right_center_y:.6f} {right_w_norm:.6f} {right_h_norm:.6f}"
            
            # 整体等比缩放到目标宽度500
            scale_ratio = target_width / canvas_width
            target_height = int(canvas_height * scale_ratio)
            final_image = combined.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 后续的绘制（文字、圆形）在缩放后的图像上进行，
            # 圆形 YOLO 标注基于最终图像尺寸计算
            
        else:
            # ----------------------------
            # 上下拼接（垂直）：分别缩放到500宽，再上下拼接
            # ----------------------------
            new_width = target_width
            new_height1 = int(img1.size[1] * (new_width / img1.size[0]))
            new_height2 = int(img2.size[1] * (new_width / img2.size[0]))
            img1_resized = img1.resize((new_width, new_height1), Image.Resampling.LANCZOS)
            img2_resized = img2.resize((new_width, new_height2), Image.Resampling.LANCZOS)
            
            canvas_width = new_width
            canvas_height = new_height1 + new_height2
            combined = Image.new('RGB', (canvas_width, canvas_height), color='black')
            combined.paste(img1_resized, (0, 0))
            combined.paste(img2_resized, (0, new_height1))
            final_image = combined
            
            # YOLO 标注（基于上下拼接后的画布）
            total_height = canvas_height
            top_center_x = 0.5
            top_center_y = (new_height1 / 2) / total_height
            top_w_norm = 1.0
            top_h_norm = new_height1 / total_height
            yolo1 = f"1 {top_center_x:.6f} {top_center_y:.6f} {top_w_norm:.6f} {top_h_norm:.6f}"
            
            bottom_center_x = 0.5
            bottom_center_y = (new_height1 + new_height2 / 2) / total_height
            bottom_w_norm = 1.0
            bottom_h_norm = new_height2 / total_height
            yolo2 = f"2 {bottom_center_x:.6f} {bottom_center_y:.6f} {bottom_w_norm:.6f} {bottom_h_norm:.6f}"
        
        # ----------------------------
        # 在最终图像上添加文字和随机圆形
        # ----------------------------
        draw = ImageDraw.Draw(final_image, "RGBA")
        
        # 生成第一行文字：当前时间、月份缩写、日期（带后缀）
        current_time = time.strftime("%H:%M:%S")
        month_abbr = time.strftime("%b")
        day = time.strftime("%d")
        if day.endswith('1') and day != '11':
            day_suffix = 'st'
        elif day.endswith('2') and day != '12':
            day_suffix = 'nd'
        elif day.endswith('3') and day != '13':
            day_suffix = 'rd'
        else:
            day_suffix = 'th'
        day_formatted = f"{day}{day_suffix}"
        text_line1 = f"VALID   BEFORE   {current_time}   {month_abbr}   {day_formatted}   CST"
        
        # 第二行随机 40 位十六进制字符串
        text_line2 = ''.join(random.choices('0123456789ABCDEF', k=40))
        
        # 计算文字放置位置（右下角区域）
        margin_x = 5
        margin_bottom = 3
        line_spacing = 7
        img_width, img_height = final_image.size
        text_y2 = img_height - font_size2 - margin_bottom
        text_y1 = text_y2 - line_spacing - font_size1
        
        # 绘制第一行文字背景（对白色涂底 "VALID   BEFORE   hh:mm:ss" 部分）
        valid_before_text = f"VALID   BEFORE   {current_time}"
        text_bbox = draw.textbbox((margin_x, text_y1), valid_before_text, font=font1)
        text_bbox = (text_bbox[0], text_bbox[1] - 3, text_bbox[2], text_bbox[3] - 6)
        draw.rectangle(text_bbox, fill="white")
        
        # 随机颜色绘制文字
        random_color1 = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        random_color2 = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.text((margin_x, text_y1), text_line1, fill=random_color1, font=font1)
        draw.text((margin_x, text_y2), text_line2, fill=random_color2, font=font2)
        
        # 生成一个随机位置和随机半径（15px-50px）的圆（50% 透明）
        radius = random.randint(15, 50)
        x = random.randint(radius, img_width - radius)
        y = random.randint(radius, img_height - radius)
        circle_color = (random.randint(0, 255), random.randint(0, 255),
                        random.randint(0, 255), 128)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=circle_color, outline=None)
        
        # 圆形的 YOLO 标注（基于最终图像尺寸）
        circle_center_x = x / img_width
        circle_center_y = y / img_height
        circle_w_norm = (2 * radius) / img_width
        circle_h_norm = (2 * radius) / img_height
        yolo_circle = f"0 {circle_center_x:.6f} {circle_center_y:.6f} {circle_w_norm:.6f} {circle_h_norm:.6f}"
        
        # ----------------------------
        # 保存图像和对应的 YOLO 数据文件
        # ----------------------------
        file_number = f"{i:05d}"
        image_path = os.path.join(output_image_folder, file_number + ".jpg")
        txt_path = os.path.join(output_txt_folder, file_number + ".txt")
        
        final_image.save(image_path)
        with open(txt_path, "w") as f:
            f.write(yolo1 + "\n")
            f.write(yolo2 + "\n")
            f.write(yolo_circle + "\n")
            
    except Exception as e:
        print(f"Error processing image {i}: {e}")

if __name__ == '__main__':
    total_images = 30000
    max_threads = 20

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(process_image, i) for i in range(1, total_images + 1)]
        for future in as_completed(futures):
            pass