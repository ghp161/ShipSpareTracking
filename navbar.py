# navbar.py
import streamlit as st
from streamlit_option_menu import option_menu
from user_management import init_session_state, logout
import base64

# Page configuration
pages = {
    'Home': 'main.py',
    'User Management': 'pages/admin.py',
    'Departments': 'pages/departments.py',
    'Data Management': 'pages/data_management.py',
    'Analytics': 'pages/analytics.py',
    'Inventory': 'pages/inventory.py',
    'Operations': 'pages/operations.py',
    'Reports': 'pages/reports.py',
    'Logout': 'main.py'
}

icons = [
    'house', 'people-fill', 'building', 'database', 'graph-up-arrow', 
    'gear', 'toggles', 'clipboard2-data', 'box-arrow-right'
]

def nav(current_page="Home"):
    """Navigation sidebar"""
    with st.sidebar:
        add_logo()
        st.write("")

        if st.session_state.authenticated:
            # User info
            username = st.session_state.get('username', 'Guest')
            user_role = st.session_state.get('user_role', '')
            
            st.write(f"Logged in as: **{username}**")
            st.write(f"Role: **{user_role}**")

            # Determine visible pages
            visible_pages, visible_icons = get_visible_pages(user_role)

            if visible_pages:
                selected = option_menu(
                    "Menu",
                    visible_pages,
                    icons=visible_icons,
                    default_index=visible_pages.index(current_page) if current_page in visible_pages else 0,
                    orientation="vertical"
                )
                
                # Handle navigation
                if selected == "Logout":
                    logout()
                elif current_page != selected:
                    st.switch_page(pages[selected])
            
            # Stock alerts
            display_stock_alerts()

def get_visible_pages(user_role):
    """Get visible pages based on user role"""
    if user_role == 'Super User':
        return list(pages.keys()), icons
    elif user_role == 'Admin':
        visible_pages = [p for p in pages.keys() 
                        if p not in ['User Management', 'Departments', 'Data Management']]
        visible_icons = [icon for icon, p in zip(icons, pages.keys())
                        if p not in ['User Management', 'Departments', 'Data Management']]
        return visible_pages, visible_icons
    elif user_role == 'User':
        return ['Inventory', 'Reports', 'Logout'], \
               ['gear', 'clipboard2-data', 'box-arrow-right']
    else:
        return [], []

def display_stock_alerts():
    """Display stock alerts in sidebar"""
    if 'data_manager' in st.session_state:
        try:
            if st.session_state.user_role == 'User':
                user_dept_id = st.session_state.get('user_department_id')
                lpl_stock = st.session_state.data_manager.get_last_piece_stock_items_by_dept(user_dept_id)
            else:
                lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
            
            if not lpl_stock.empty:
                st.error(f"🚨 {len(lpl_stock)} Last Piece Level Items!")
                
        except Exception as e:
            st.error(f"Error loading stock alerts: {str(e)}")

def make_sidebar(current_page="Home"):
    """Alternative sidebar function"""
    nav(current_page)

# Logo functions (unchanged)
def get_base64_of_bin_file(png_file: str) -> str:
    with open(png_file, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_resource
def build_markup_for_logo(png_file: str) -> str:
    binary_string = get_base64_of_bin_file(png_file)
    return f"""
            <style>
                [data-testid="stSidebarHeader"] {{
                    background-image: url("data:image/png;base64,{binary_string}");
                    background-repeat: no-repeat;
                    background-size: contain;
                    background-position: top center;
                }}
            </style>
            """

def add_logo():
    st.markdown(
        build_markup_for_logo("logo.png"),
        unsafe_allow_html=True,
    )