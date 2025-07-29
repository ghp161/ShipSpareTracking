import streamlit as st
from PIL import Image
import base64
from io import BytesIO

def add_logo_background(logo_path="logo.png", opacity=0.4):
    """Add a visible but non-intrusive logo background"""
    try:
        # Open and prepare logo
        logo = Image.open(logo_path)
        
        # Convert to base64
        buffered = BytesIO()
        logo.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # CSS with guaranteed visibility
        css = f"""
        <style>
        [data-testid="stAppViewContainer"] > .main {{
            background-image: url("data:image/png;base64,{img_str}");
            background-size: 40%;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-opacity: 0.4;
            position: relative;
        }}
        
        [data-testid="stAppViewContainer"] > .main::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255, 255, 255, 0.82);
            z-index: 0;
        }}
        
        [data-testid="stAppViewContainer"] > .main > div {{
            position: relative;
            z-index: 1;
        }}
        </style>
        """
        
        st.markdown(css, unsafe_allow_html=True)
        st.markdown('<div class="main">', unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Couldn't load background image: {e}")

def set_page_configuration():
    # Set page configuration
    st.set_page_config(
        page_title="Ship Inventory Management System",
        page_icon="🚢",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Reducing whitespace on the top of the page
    st.markdown("""
    <style>
    
            .stAppHeader {
                background-color: rgba(255, 255, 255, 0.0);  /* Transparent background */
                visibility: visible;  /* Ensure the header is visible */
            }

           /* Remove blank space at top and bottom */ 
           .block-container {
               padding-top: 0rem;
               padding-bottom: 0rem;
            }
           
           /* Remove blank space at the center canvas */ 
           .st-emotion-cache-z5fcl4 {
               position: relative;
               top: -62px;
               }
           
           /* Make the toolbar transparent and the content below it clickable */ 
           .st-emotion-cache-18ni7ap {
               pointer-events: none;
               background: rgb(255 255 255 / 0%)
               }
           .st-emotion-cache-zq5wmm {
               pointer-events: auto;
               background: rgb(255 255 255);
               border-radius: 5px;
               }
    </style>
    """, unsafe_allow_html=True)