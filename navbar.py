import streamlit as st
from time import sleep
from streamlit_option_menu import option_menu
from user_management import init_session_state, render_login_page

# Initialize session state
init_session_state()

# Define the pages and their file paths
pages = {
    'Home': 'main.py',
    'User Management': 'pages/admin.py',
    'Analytics': 'pages/analytics.py',
    'Inventory': 'pages/inventory.py',
    'Operations': 'pages/operations.py',
    'Reports': 'pages/reports.py'
}

icons = ['house', 'people-fill', 'graph-up-arrow', 'gear', 'toggles', 'clipboard2-data']

# Create a list of the page names
page_list = list(pages.keys())


def nav(current_page=page_list[0]):
    with st.sidebar:
        st.title("💎 Meridian DataLabs")
        st.write("")

        st.write(f"Logged in as: {st.session_state.username}")
        st.write(f"Role: {st.session_state.user_role}")

        # Alert Section in Sidebar
        low_stock = st.session_state.data_manager.get_low_stock_items()
        if not low_stock.empty:
            st.error(f"🚨 {len(low_stock)} items below minimum stock level!")
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

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_role = None
            st.rerun()

        if current_page != p:
            st.switch_page(pages[p])


def make_sidebar(current_page=page_list[0]):
    with st.sidebar:
        st.title("💎 Meridian DataLabs")
        st.write("")
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
            if current_page != p:
                st.switch_page(pages[p])

            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user_role = None
                st.rerun()
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


#st.switch_page("login.py")
