import streamlit as st
from time import sleep
from streamlit_option_menu import option_menu
from user_management import init_session_state, render_login_page
import base64

# Initialize session state
init_session_state()

# Define the pages and their file paths
pages = {
    'Home': 'main.py',
    'User Management': 'pages/admin.py',
    'Analytics': 'pages/analytics.py',
    'Inventory': 'pages/inventory.py',
    'Operations': 'pages/operations.py',
    'Reports': 'pages/reports.py',
    'Logout': 'main.py'
}

icons = [
    'house', 'people-fill', 'graph-up-arrow', 'gear', 'toggles',
    'clipboard2-data'
]

# Create a list of the page names
page_list = list(pages.keys())


def nav(current_page=page_list[0]):
    with st.sidebar:
        #st.image("logo.png", width=100)
        add_logo()
        st.write("")

        if st.session_state.authenticated:
            st.write(f"Logged in as: {st.session_state.username}")
            st.write(f"Role: {st.session_state.user_role}")

            # Alert Section in Sidebar
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

            p = option_menu("Menu",
                            page_list,
                            icons=icons,
                            default_index=page_list.index(current_page),
                            orientation="vertical")

            #print(current_page)
            print(p)

            if p == "Logout":
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user_role = None
                render_login_page()
                st.rerun()

            if current_page != p:
                st.switch_page(pages[p])


def make_sidebar(current_page=page_list[0]):
    with st.sidebar:
        #st.image("logo.png", width=100)
        add_logo()
        st.write("")

        if st.session_state.authenticated:
            st.write(f"Logged in as: {st.session_state.username}")
            st.write(f"Role: {st.session_state.user_role}")

            # Alert Section in Sidebar
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

            p = option_menu("Menu",
                            page_list,
                            icons=icons,
                            default_index=page_list.index(current_page),
                            orientation="vertical")

            if p == "Logout":
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user_role = None
                render_login_page()
                st.rerun()

            if current_page != p:
                st.switch_page(pages[p])

        #elif current_page != p:
        # If anyone tries to access a secret page without being logged in,
        # redirect them to the login page
        #st.switch_page("login.py")
        #   render_login_page()


def logout():
    st.session_state.logged_in = False
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
