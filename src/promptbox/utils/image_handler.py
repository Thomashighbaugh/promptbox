"""
Contains utility functions for handling image metadata, conforming to the
standard 'chara' tEXt chunk format for PNG character cards.
"""
import json
import base64
from PIL import Image, PngImagePlugin
import io
import piexif

class ImageMetadataError(Exception):
    """Custom exception for errors related to image metadata processing."""
    pass

def write_metadata_to_png(image_bytes: bytes, card_data: dict) -> bytes:
    """
    Writes a dictionary of card data to a PNG's metadata chunk.
    This uses the 'chara' keyword in a tEXt chunk, standard for character cards.
    """
    try:
        # Prepare the data as a base64 encoded string
        json_data = json.dumps(card_data)
        base64_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')

        # Add the data to a PngInfo object for writing to the tEXt chunk
        png_info = PngImagePlugin.PngInfo()
        png_info.add_text("chara", base64_data)

        # Re-save the image with the new metadata chunk
        # Using Pillow ensures we can handle various image formats and save to PNG
        img = Image.open(io.BytesIO(image_bytes))
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', pnginfo=png_info)
        
        return img_buffer.getvalue()

    except Exception as e:
        raise ImageMetadataError(f"Failed to write character metadata to image: {e}")

def read_metadata_from_image(image_bytes: bytes) -> dict | None:
    """
    Reads character card data from an image's metadata.
    It first checks for the standard 'chara' tEXt chunk in PNGs.
    As a fallback, it checks for EXIF data for cards created by older versions of this app.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Method 1: Standard PNG 'chara' chunk (most common format)
        if img.info and isinstance(img.info, dict) and 'chara' in img.info:
            base64_data = img.info['chara']
            json_data = base64.b64decode(base64_data)
            data = json.loads(json_data)
            return data

        # Method 2: EXIF fallback (for JPEGs or older app-generated PNGs)
        raw_exif = img.info.get("exif")
        if raw_exif:
            exif_dict = piexif.load(raw_exif)
            user_comment_bytes = exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            if user_comment_bytes:
                comment_str = piexif.helper.UserComment.load(user_comment_bytes)
                data = json.loads(comment_str)
                return data

    except (json.JSONDecodeError, base64.binascii.Error):
        raise ImageMetadataError("Failed to decode character data. Metadata may be corrupt or in an unsupported format.")
    except Exception as e:
        # A broad catch for other PIL/piexif errors (e.g., file is not a valid image)
        raise ImageMetadataError(f"Could not process image file: {e}")
        
    return None
