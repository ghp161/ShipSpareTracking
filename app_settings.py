import streamlit as st

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