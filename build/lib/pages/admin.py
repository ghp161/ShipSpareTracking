import streamlit as st
from user_management import login_required
#from navbar import make_sidebar
import navbar

current_page = "User Management"
st.header(current_page)

navbar.nav(current_page)

@login_required
def render_admin_page():
    if st.session_state.user_role != 'admin':
        st.error("You don't have permission to access this page")
        return

    #st.title("User Management")
    #make_sidebar()
    tab1, tab2 = st.tabs(["Add User", "Manage Users"])

    with tab1:
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["staff", "manager", "admin"])

            if st.form_submit_button("Add User"):
                if new_username and new_password:
                    if st.session_state.user_manager.register_user(
                            new_username, new_password, role):
                        st.success(f"User {new_username} added successfully")
                        st.rerun()
                    else:
                        st.error("Username already exists")
                else:
                    st.error("Please fill in all fields")

    with tab2:
        users = st.session_state.user_manager.get_all_users()
        if users:
            for user in users:
                with st.expander(f"User: {user[1]}"):
                    st.write(f"Role: {user[2]}")
                    st.write(f"Created: {user[3]}")
                    st.write(f"Last Login: {user[4] or 'Never'}")

                    if user[1] != 'admin':  # Prevent modifying admin user
                        new_role = st.selectbox(
                            "Update Role", ["staff", "manager", "admin"],
                            index=["staff", "manager", "admin"].index(user[2]),
                            key=f"role_{user[0]}")

                        if new_role != user[2]:
                            if st.button("Update Role",
                                         key=f"update_{user[0]}"):
                                if st.session_state.user_manager.update_user_role(
                                        user[1], new_role):
                                    st.success("Role updated successfully")
                                    st.rerun()
                                else:
                                    st.error("Failed to update role")


if __name__ == "__main__":
    render_admin_page()
