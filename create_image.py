# create_image.py

from PIL import Image, ImageFont, ImageDraw
import pandas as pd
import os
import math

def overlay_text(img, text, position, font, color):
    """
    Overlays the given text on the provided image at the specified position.
    """
    draw = ImageDraw.Draw(img)
    draw.text(position, text, font=font, fill=color)


def _safe_text(value, fallback=""):
    if value is None:
        return fallback
    if isinstance(value, float) and math.isnan(value):
        return fallback
    return str(value)

if __name__ == "__main__":
    # Load the most recent earthquake data from the CSV file
    if not os.path.exists("sismos_ipma.csv"):
        raise SystemExit(0)

    df = pd.read_csv("sismos_ipma.csv")
    if df.empty:
        raise SystemExit(0)

    latest_data = df.iloc[0]

    # Print the event for verification
    print(latest_data)

    # Load the image template
    img_path = "assets/SISMO_TEMPLATE_AUTO.png"
    img = Image.open(img_path)

    # Define the font for the overlay text
    font = ImageFont.truetype("assets/Lato-Bold.ttf", 38)

    # Overlay the location information on the image
    location_text = _safe_text(latest_data.get("location"), fallback="")
    overlay_text(img, location_text, (390, 559), font, "#703D25")

    # Overlay the scale information on the image
    scale_text = _safe_text(latest_data.get("scale"), fallback="")
    overlay_text(img, scale_text, (455, 629), font, "#703D25")

    # Overlay the date_time information on the image
    date_time_text = _safe_text(latest_data.get("date_time"), fallback="")
    overlay_text(img, date_time_text, (242, 772), font, "#00A396")

    # Overlay the intensity information on the image
    intensity_text = _safe_text(latest_data.get("intensity"), fallback="")
    overlay_text(img, intensity_text, (520, 832), font, "#703D25")

    # Save the modified image
    img.save("assets/SISMO_TEMPLATE_MODIFIED.png")
