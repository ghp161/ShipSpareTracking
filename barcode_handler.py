import barcode
from barcode.writer import ImageWriter
import io
import base64
import re
from barcode import *

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
    def validate_barcode(barcode):
        """
        Validate barcode format: 3 chars - 1 char - 4 digits (ABC-D-1234)
        
        Args:
            barcode (str): The barcode to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not isinstance(barcode, str):
            return False, "Barcode must be a string"
        
        pattern = r'^[A-Za-z]{3}-[A-Za-z]{1}-\d{4}$'
        print("barcode:", barcode)  # Add this temporarily
        if not re.fullmatch(pattern, barcode):
            return False, (
                "Invalid barcode format. "
                "Required format: ABC-D-1234 (3 letters, 1 letter, 4 digits)"
            )
        
        return True, "Barcode is valid"

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