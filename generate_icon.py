from PIL import Image, ImageDraw

def create_app_icon(output_path="app_icon.ico"):
    # Create high-resolution multi-size icon
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for size in sizes:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = size

        # Outer rounded gradient pill/circle (Vibrant Blue/Cyan)
        # Background: Rich Deep Indigo-Blue (#1E3A8A -> #2563EB)
        draw.ellipse([2, 2, w - 3, h - 3], fill=(24, 32, 58, 255), outline=(59, 130, 246, 255), width=max(1, int(w * 0.04)))

        # Inner decorative circle (Cyan highlight)
        margin = int(w * 0.15)
        draw.ellipse([margin, margin, w - margin, h - margin], fill=(37, 99, 235, 230))

        # Microphone shape in white
        mic_w = max(2, int(w * 0.22))
        mic_h = max(4, int(h * 0.35))
        mic_x = int((w - mic_w) / 2)
        mic_y = int(h * 0.25)

        # Mic capsule
        draw.rounded_rectangle([mic_x, mic_y, mic_x + mic_w, mic_y + mic_h], radius=int(mic_w/2), fill=(255, 255, 255, 255))

        # Mic base arc (U shape)
        arc_m = int(w * 0.26)
        arc_top = int(h * 0.35)
        arc_bottom = int(h * 0.65)
        draw.arc([arc_m, arc_top, w - arc_m, arc_bottom], start=0, end=180, fill=(255, 255, 255, 255), width=max(1, int(w * 0.05)))

        # Mic stand
        stand_x = int(w / 2)
        stand_y1 = arc_bottom
        stand_y2 = int(h * 0.76)
        draw.line([stand_x, stand_y1, stand_x, stand_y2], fill=(255, 255, 255, 255), width=max(1, int(w * 0.05)))

        # Mic base plate
        base_w = int(w * 0.28)
        draw.line([stand_x - int(base_w/2), stand_y2, stand_x + int(base_w/2), stand_y2], fill=(255, 255, 255, 255), width=max(1, int(w * 0.05)))

        images.append(img)

    images[0].save(output_path, format="ICO", sizes=sizes)
    # Also save PNG for UI headers
    images[0].save("app_icon.png", format="PNG")
    print(f"Icon generated: {output_path}")

if __name__ == "__main__":
    create_app_icon()
