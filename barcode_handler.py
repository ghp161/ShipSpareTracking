import barcode
from barcode.writer import ImageWriter
import io
import base64

class BarcodeHandler:
    @staticmethod
    def generate_barcode(value):
        # Generate Code128 barcode
        barcode_class = barcode.get_barcode_class('code128')
        rv = io.BytesIO()
        barcode_class(value, writer=ImageWriter()).write(rv)
        return base64.b64encode(rv.getvalue()).decode()

    @staticmethod
    def generate_unique_barcode(prefix="SP"):
        import random
        import string
        
        # Generate a random 8-character string
        random_part = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}{random_part}"
