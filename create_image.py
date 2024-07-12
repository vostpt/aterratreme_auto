# create_image.py

from PIL import Image, ImageFont, ImageDraw
import pandas as pd

def overlay_text(img, text, position, font, color):
    """
    Overlays the given text on the provided image at the specified position.
    """
    draw = ImageDraw.Draw(img)
    draw.text(position, text, font=font, fill=color)

if __name__ == "__main__":
    # Load the most recent earthquake data from the CSV file
    df = pd.read_csv("sismos_ipma.csv")
    latest_data = df.iloc[0]

    # Print the event for verification
    print(latest_data)

    # Load the image template
    img_path = "assets/SISMO_TEMPLATE_AUTO.png"
    img = Image.open(img_path)

    # Define the font for the overlay text
    font = ImageFont.truetype("assets/Lato-Bold.ttf", 38)

    # Overlay the location information on the image
    location_text = latest_data['location']
    overlay_text(img, location_text, (390, 559), font, "#703D25")

    # Overlay the scale information on the image
    scale_text = str(latest_data['scale'])
    overlay_text(img, scale_text, (455, 629), font, "#703D25")

    # Overlay the date_time information on the image
    date_time_text = latest_data['date_time']
    overlay_text(img, date_time_text, (242, 772), font, "#00A396")

    # Overlay the intensity information on the image
    intensity_text = latest_data['intensity']
    overlay_text(img, intensity_text, (520, 832), font, "#703D25")

    # Save the modified image
    img.save("assets/SISMO_TEMPLATE_MODIFIED.png")
