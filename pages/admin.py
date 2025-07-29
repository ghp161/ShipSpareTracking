import streamlit as st
import pandas as pd
from user_management import login_required
import navbar
from app_settings import set_page_configuration
from datetime import datetime

set_page_configuration()

current_page = "User Management"
st.header(current_page)

navbar.nav(current_page)

@login_required
def render_admin_page():
    if st.session_state.user_role in ['Admin', 'User']:
        st.error("You don't have permission to access this page")
        return
    
    tab1, tab2 = st.tabs(["Manage Users", "Add New User"])

    with tab1:
        #st.subheader("User Management")
        
        df = st.session_state.user_manager.get_all_users_with_departments()
        
        if not df.empty:
            # Display non-editable grid with status indicator
            st.dataframe(
                df[['id', 'username', 'role', 'isactive', 'parent_department', 'child_department']],
                column_config={
                    "id": "ID",
                    "username": "Username",
                    "role": "Role",
                    "isactive": st.column_config.CheckboxColumn(
                        "Active",
                        disabled=True,
                        help="User account status"
                    ),
                    "parent_department": "Parent Department",
                    "child_department": "Child Department"
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Edit user section
            st.subheader("Edit User")
            user_id = st.selectbox(
                "Select User to Edit",
                df['id'],
                format_func=lambda x: f"{df[df['id']==x]['username'].iloc[0]} ({df[df['id']==x]['role'].iloc[0]})"
            )
            
            if user_id:
                user_data = df[df['id'] == user_id].iloc[0]

                # Initialize department variables
                department_id = None
                current_parent = None
                current_child = None

                # Department selection (outside the form for proper cascading)
                if user_data['role'] == "User":
                    st.subheader("Department Assignment")
                    parent_depts = st.session_state.user_manager.get_parent_departments()
                    
                    # Safely get current parent department
                    if not pd.isna(user_data['parent_department']) and not parent_depts.empty:
                        parent_match = parent_depts[parent_depts['name'] == user_data['parent_department']]
                        current_parent = parent_match['id'].iloc[0] if not parent_match.empty else None
                    
                    # Parent department selection
                    selected_parent = st.selectbox(
                        "Parent Department",
                        parent_depts['id'].tolist(),
                        format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                        index=parent_depts['id'].tolist().index(current_parent) if current_parent is not None else 0,
                        key=f"parent_dept_{user_id}"
                    )
                    
                    # Child departments (will update when parent changes)
                    child_depts = st.session_state.user_manager.get_child_departments(selected_parent)
                    
                    # Safely get current child department
                    if not pd.isna(user_data['child_department']) and not child_depts.empty:
                        child_match = child_depts[child_depts['name'] == user_data['child_department']]
                        current_child = child_match['id'].iloc[0] if not child_match.empty else None
                    
                    if not child_depts.empty:
                        # Safely determine index
                        child_index = 0
                        if current_child is not None and current_child in child_depts['id'].tolist():
                            child_index = child_depts['id'].tolist().index(current_child)
                        
                        department_id = st.selectbox(
                            "Child Department",
                            child_depts['id'].tolist(),
                            format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                            index=child_index,
                            key=f"child_dept_{user_id}"
                        )
                    else:
                        st.warning("No child departments available")
                        department_id = None

                with st.form(f"edit_form_{user_id}"):
                    st.markdown("**Basic Information**")
                    new_username = st.text_input("Username", value=user_data['username'])
                    st.text_input("Role", value=user_data['role'], disabled=True)
                    new_role = user_data['role']  # Keep original role
                    
                    # Password change section
                    st.markdown("**Password Change**")
                    change_password = st.checkbox("Change password")
                    new_password = None
                    if change_password:
                        new_password = st.text_input("New Password", type="password")
                        confirm_password = st.text_input("Confirm Password", type="password")
                        if new_password and new_password != confirm_password:
                            st.error("Passwords do not match!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            # Validate password change if requested
                            #print("department_id:", department_id)  # Add this temporarily
                            if change_password and not new_password:
                                st.error("Please enter a new password")
                            else:
                                # Update user information
                                success, message = st.session_state.user_manager.update_user(
                                    user_id=user_id,
                                    username=new_username,
                                    role=new_role,
                                    department_id=department_id if new_role == "User" else None,
                                    new_password=new_password if change_password else None
                                )
                                if success:
                                    st.toast("User updated successfully!", icon="✅")
                                    st.success("User updated successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Update failed: {message}")
                    with col2:
                        if st.form_submit_button("Deactivate" if user_data['isactive'] else "Activate"):
                            if user_id == st.session_state.get('user_id'):
                                st.error("You cannot deactivate your own account!")
                            else:
                                if user_data['isactive']:
                                    success, message = st.session_state.user_manager.deactivate_user(user_id)
                                else:
                                    success, message = st.session_state.user_manager.activate_user(user_id)
                                
                                if success:
                                    st.success("User status updated successfully!")
                                    st.toast("User status updated successfully!", icon="✅")
                                    st.rerun()
                                else:
                                    st.error(f"Operation failed: {message}")
        else:
            st.info("No users found")

    with tab2:
        st.subheader("Add New User")
        
        # Initialize form fields in session state
        if 'new_username' not in st.session_state:
            st.session_state.new_username = ""
        if 'new_password' not in st.session_state:
            st.session_state.new_password = ""
        if 'new_user_role' not in st.session_state:
            st.session_state.new_user_role = "User"
        if 'new_user_parent_dept' not in st.session_state:
            st.session_state.new_user_parent_dept = None
        if 'new_user_child_dept' not in st.session_state:
            st.session_state.new_user_child_dept = None
        if 'show_success' not in st.session_state:
            st.session_state.show_success = False
        
        # Show success toast if flag is set
        if st.session_state.show_success:
            st.toast("User added successfully!", icon="✅")
            st.session_state.show_success = False  # Reset the flag
        
        # Department selection
        role = st.selectbox(
            "Role*", 
            ["Super User", "Admin", "User"], 
            key="new_user_role_select",
            index=["Super User", "Admin", "User"].index(st.session_state.new_user_role)
        )
        
        if role == "User":
            st.markdown("**Department Assignment**")
            parent_depts = st.session_state.user_manager.get_parent_departments()
            selected_parent = st.selectbox(
                "Parent Department*",
                parent_depts['id'].tolist(),
                index=None,
                placeholder="Select Parent Department",
                format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                key="new_user_parent_dept_select"
            )
                
            if selected_parent:
                child_depts = st.session_state.user_manager.get_child_departments(selected_parent)
                if not child_depts.empty:
                    department_id = st.selectbox(
                        "Child Department*",
                        child_depts['id'].tolist(),
                        index=None,
                        placeholder="Select Child Department",
                        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                        key="new_user_child_dept_select"
                    )
                else:
                    st.warning("No child departments available")
                    department_id = None

        with st.form("add_user_form"):
            new_username = st.text_input("Username*", value=st.session_state.new_username, key="new_username_input")
            new_password = st.text_input("Password*", type="password", value=st.session_state.new_password, key="new_password_input")
            
            submit_button = st.form_submit_button(label='Submit')

            if submit_button:
                if not new_username or not new_password:
                    st.error("Please fill in all required fields (marked with *)")
                elif role == "User" and not department_id:
                    st.error("Please select a child department for user")
                else:
                    if st.session_state.user_manager.register_user(
                            username=new_username,
                            password=new_password,
                            role=role,
                            department_id=department_id if role == "User" else None, isactive=True):
                        
                        # Set success flag and clear form
                        st.session_state.show_success = True
                        st.session_state.new_username = ""
                        st.session_state.new_password = ""
                        st.session_state.new_user_role = "User"
                        st.session_state.new_user_parent_dept = None
                        st.session_state.new_user_child_dept = None
                        
                        # Rerun to show toast and clear form
                        st.rerun()
                    else:
                        st.error("Username already exists")
                        st.toast("Username already exists!", icon="✅")

if __name__ == "__main__":
    render_admin_page()