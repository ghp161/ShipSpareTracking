import streamlit as st
from time import sleep
from streamlit_option_menu import option_menu
from user_management import init_session_state, render_login_page
import base64
from data_manager import DataManager

# Initialize session state
init_session_state()

# Define the pages and their file paths
pages = {
    'Home': 'main.py',
    'User Management': 'pages/admin.py',
    'Departments': 'pages/departments.py',
    'Data Management': 'pages/data_management.py',  # Add this line
    'Analytics': 'pages/analytics.py',
    'Inventory': 'pages/inventory.py',
    'Operations': 'pages/operations.py',
    'Reports': 'pages/reports.py',
    'Logout': 'main.py'
}

icons = [
    'house', 'people-fill', 'building', 'database', 'graph-up-arrow', 'gear', 'toggles',
    'clipboard2-data', 'box-arrow-right'
]

# Create a list of the page names
page_list = list(pages.keys())


def nav(current_page=page_list[0]):
    # Initialize selected variable
    selected = None
    # Initialize session state if not already done
    if 'authenticated' not in st.session_state:
        init_session_state()

    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()

    with st.sidebar:
        #st.image("logo.png", width=100)
        add_logo()
        st.write("")

        if st.session_state.authenticated:
            # Safe session state access
            username = st.session_state.get('username', 'Guest')  # Default to 'Guest' if not set
            st.write(f"Logged in as: {username}")
            #st.write(f"Logged in as: {st.session_state.username}")
            #st.write(f"Role: {st.session_state.user_role}")
            role = st.session_state.get('user_role', '')  # Default to 'Guest' if not set
            st.write(f"Role: {role}")

            # Safely check for low stock items
            if 'data_manager' in st.session_state:
                try:
                    # Alert Section in Sidebar
                    if st.session_state.user_role == 'User':
                        lpl_stock = st.session_state.data_manager.get_last_piece_stock_items_by_dept(st.session_state.get('user_department_id'))
                    else:
                        lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
                    if not lpl_stock.empty:
                        st.error(
                            f"🚨 {len(lpl_stock)} - Last Piece Level!")
                        with st.expander("View Last Piece Level Stock Alerts"):
                            for _, item in lpl_stock.iterrows():
                                st.warning(f"""
                                    **{item['name']}**
                                    - Current: {item['quantity']}
                                    - Minimum: {item['min_order_level']}
                                    - Order Quantity: {item['min_order_quantity']}
                                """)

                    if st.session_state.user_role == 'User':
                        low_stock = st.session_state.data_manager.get_low_stock_items_by_dept(st.session_state.get('user_department_id'))
                    else:
                        low_stock = st.session_state.data_manager.get_low_stock_items()
                    if not low_stock.empty:
                        st.error(
                            f"🚨 {len(low_stock)} items below minimum stock level!")
                        with st.expander("View Low Stock Alerts"):
                            for _, item in low_stock.iterrows():
                                st.warning(f"""
                                    **{item['name']}**
                                    - Current: {item['quantity']}
                                    - Minimum: {item['min_order_level']}
                                    - Order Quantity: {item['min_order_quantity']}
                                """)
                except Exception as e:
                    st.error(f"Error checking stock levels: {str(e)}")

            user_role = st.session_state.get('user_role', 'user')
            #print("user_role:", user_role)  # Add this temporarily
            if user_role == 'Super User':
                visible_pages = list(pages.keys())
                visible_icons = icons
            elif user_role == 'Admin':
                # Exclude User Management and Departments
                visible_pages = [p for p in pages.keys() 
                            if p not in ['User Management', 'Departments', 'Data Management']]
                visible_icons = [icon for icon, p in zip(icons, pages.keys())
                            if p not in ['User Management', 'Departments', 'Data Management']]
            elif user_role == 'User':
                visible_pages = ['Inventory', 'Reports', 'Logout']
                visible_icons = ['gear', 'clipboard2-data', 'box-arrow-right']
            else:
                visible_pages = []
                visible_icons = []


            #print("visible_pages list 2:", visible_pages)  # Add this temporarily
            # Create the menu
            if visible_pages:
                selected = option_menu(
                    "Menu",
                    visible_pages,
                    icons=visible_icons,
                    default_index=visible_pages.index(current_page) if current_page in visible_pages else 0,
                    orientation="vertical"
                )
                
                # Handle logout
                if selected == "Logout":
                    #st.session_state.clear()  # Clear all session state
                    # Clear session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()   # Rerun to show login page

                if current_page != selected:
                    st.switch_page(pages[selected])
        #else:
            # Show login page without sidebar
            #st.set_page_config(layout="centered")
            #render_login_page()


def make_sidebar(current_page=page_list[0]):
    # Initialize selected variable
    selected = None

    # Initialize session state if not already done
    if 'authenticated' not in st.session_state:
        init_session_state()

    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()

    with st.sidebar:
        #st.image("logo.png", width=100)
        add_logo()
        st.write("")
        #print("visible_pages list:")  # Add this temporarily
        if st.session_state.authenticated:
            st.write(f"Logged in as: {st.session_state.username}")
            st.write(f"Role: {st.session_state.user_role}")
            #print("Page list:", page_list)  # Add this temporarily
            
            # Safely check for low stock items
            if 'data_manager' in st.session_state:
                try:
                    # Alert Section in Sidebar
                    if st.session_state.user_role == 'User':
                        lpl_stock = st.session_state.data_manager.get_last_piece_stock_items_by_dept(st.session_state.get('user_department_id'))
                    else:
                        lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
                    if not lpl_stock.empty:
                        st.error(
                            f"🚨 {len(lpl_stock)} - Last Piece Level!")
                        with st.expander("View Last Piece Level Stock Alerts"):
                            for _, item in lpl_stock.iterrows():
                                st.warning(f"""
                                    **{item['name']}**
                                    - Current: {item['quantity']}
                                    - Minimum: {item['min_order_level']}
                                    - Order Quantity: {item['min_order_quantity']}
                                """)
                                
                    if st.session_state.user_role == 'User':
                        low_stock = st.session_state.data_manager.get_low_stock_items_by_dept(st.session_state.get('user_department_id'))
                    else:
                        low_stock = st.session_state.data_manager.get_low_stock_items()
                    if not low_stock.empty:
                        st.error(
                            f"🚨 {len(low_stock)} items below minimum stock level!")
                        with st.expander("View Low Stock Alerts"):
                            for _, item in low_stock.iterrows():
                                st.warning(f"""
                                    **{item['name']}**
                                    - Current: {item['quantity']}
                                    - Minimum: {item['min_order_level']}
                                    - Order Quantity: {item['min_order_quantity']}
                                """)
                except Exception as e:
                    st.error(f"Error checking stock levels: {str(e)}")

            user_role = st.session_state.get('user_role', 'user')
            #print("user_role:", user_role)  # Add this temporarily
            if user_role == 'Super User':
                visible_pages = list(pages.keys())
                visible_icons = icons
            elif user_role == 'Admin':
                # Exclude User Management and Departments
                visible_pages = [p for p in pages.keys() 
                            if p not in ['User Management', 'Departments']]
                visible_icons = [icon for icon, p in zip(icons, pages.keys())
                            if p not in ['User Management', 'Departments']]
            elif user_role == 'User':
                visible_pages = ['Inventory', 'Reports', 'Logout']
                visible_icons = ['gear', 'clipboard2-data', 'box-arrow-right']
            else:
                visible_pages = []
                visible_icons = []


            #print("visible_pages list 2:", visible_pages)  # Add this temporarily
            # Create the menu
            if visible_pages:
                selected = option_menu(
                    "Menu",
                    visible_pages,
                    icons=visible_icons,
                    default_index=visible_pages.index(current_page) if current_page in visible_pages else 0,
                    orientation="vertical"
                )
                
                # Handle logout
                if selected == "Logout":
                    #st.session_state.clear()  # Clear all session state
                    # Clear session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()   # Rerun to show login page

                if current_page != selected:
                    st.switch_page(pages[selected])
        else:
            # Show login page without sidebar
            st.set_page_config(layout="centered")
            render_login_page()

            

        #elif current_page != p:
        # If anyone tries to access a secret page without being logged in,
        # redirect them to the login page
        #st.switch_page("login.py")
        #   render_login_page()


def logout():
    st.session_state.logged_in = False
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.info("Logged out successfully!")
    sleep(0.5)
    render_login_page()

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

#st.switch_page("login.py")
