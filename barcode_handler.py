import barcode
from barcode.writer import ImageWriter
import io
import base64
import re

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

    @staticmethod
    def validate_barcode(barcode_input):
        """Validate barcode format and clean input"""
        # Remove any non-alphanumeric characters (like newlines from scanner)
        cleaned_input = re.sub(r'[^a-zA-Z0-9]', '', barcode_input)

        # Check if it matches our format (SP + 8 digits)
        if re.match(r'^SP\d{8}$', cleaned_input):
            return True, cleaned_input
        return False, None

    @staticmethod
    def get_part_by_barcode(data_manager, barcode_input):
        """Look up a part using its barcode"""
        try:
            df = data_manager.get_all_parts()
            part = df[df['barcode'] == barcode_input]
            if not part.empty:
                return True, part.iloc[0]
            return False, None
        except Exception as e:
            print(f"Error looking up barcode: {e}")
            return False, None