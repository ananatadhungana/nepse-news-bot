from PIL import Image

def get_dominant_color(image_path):
    img = Image.open(image_path)
    img = img.convert("RGBA")
    # Resize to a smaller size for faster processing
    img.thumbnail((100, 100))
    
    # Get all colors in the image and their counts
    colors = img.getcolors(img.size[0] * img.size[1])
    
    # Filter out transparent pixels (alpha < 255)
    opaque_colors = [(count, color) for count, color in colors if color[3] == 255]

    if not opaque_colors:
        return (0, 0, 0) # Default to black if no opaque pixels

    # Sort by count to get the most frequent color
    opaque_colors.sort(key=lambda x: x[0], reverse=True)
    
    # Return the RGB of the most dominant opaque color
    return opaque_colors[0][1][:3]

if __name__ == "__main__":
    logo_path = "logo.png"
    dominant_color = get_dominant_color(logo_path)
    print(f"Dominant color (RGB): {dominant_color}")
