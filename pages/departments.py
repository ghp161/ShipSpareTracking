import streamlit as st
import pandas as pd
import sqlite3
from user_management import login_required
import navbar
from app_settings import set_page_configuration
from data_manager import DataManager

set_page_configuration()

current_page = "Departments"
st.header(current_page)

navbar.nav(current_page)
    

@login_required
def render_departments_page():

    tab1, tab2 = st.tabs(["Department Grid", "Add Department"])

    with tab1:
        #st.subheader("Department Data Grid")
        
        # Get data as DataFrame
        df = st.session_state.data_manager.get_all_departments_as_df()
        
        if not df.empty:
            # Display as interactive grid
            st.dataframe(
                df,
                column_config={
                    "id": "ID",
                    "code": "Code",
                    "name": "Department Name",
                    "parent_name": "Parent Department"
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Add edit/delete functionality
            st.subheader("Edit Department")
            dept_id = st.selectbox(
                "Select Department to Edit",
                df['id'],
                format_func=lambda x: f"{df[df['id']==x]['code'].iloc[0]} - {df[df['id']==x]['name'].iloc[0]}"
            )
            
            if dept_id:
                dept_data = df[df['id'] == dept_id].iloc[0]
                with st.form(f"edit_form_{dept_id}"):
                    new_code = st.text_input("Code", value=dept_data['code'])
                    new_name = st.text_input("Name", value=dept_data['name'])
                    
                    parent_options = st.session_state.data_manager.get_parent_options()
                    current_parent = None if dept_data['parent_name'] == 'Top Level' else \
                        next((p[0] for p in parent_options if p[1] == dept_data['parent_name']), None)
                    
                    parent_id = st.selectbox(
                        "Parent Department",
                        [None] + [p[0] for p in parent_options],
                        format_func=lambda x: "Top Level" if x is None else \
                            next((p[1] for p in parent_options if p[0] == x), "None"),
                        index=0 if current_parent is None else \
                            [p[0] for p in parent_options].index(current_parent) + 1
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            # Implement update logic
                            if st.session_state.data_manager.update_department(dept_id, new_code, new_name, parent_id):
                                st.rerun()
                                st.success("Department Updated successfully")                                
                            else:
                                st.error("Department code already exists")
                    with col2:
                        if st.form_submit_button("Delete"):
                            # Implement delete logic
                            success, message = st.session_state.data_manager.delete_department(dept_id)
                            if success:
                                st.rerun()
                                st.success("Department deleted successfully!")                                
                            else:
                                st.error(f"Deletion failed: {message}")
        else:
            st.info("No departments found")

    with tab2:
        #st.subheader("Add New Department")
        with st.form("add_department_form"):
            code = st.text_input("Department Code", max_chars=10)
            name = st.text_input("Department Name")
            
            parent_options = st.session_state.data_manager.get_parent_options()
            is_parent = st.checkbox("This is a top-level department", value=True)
            
            parent_id = None
            if not is_parent and parent_options:
                parent_id = st.selectbox(
                    "Parent Department",
                    [p[0] for p in parent_options],
                    format_func=lambda x: next((p[1] for p in parent_options if p[0] == x), None),
                    index=0
                )
            
            if st.form_submit_button("Add Department"):
                if code and name:
                    if st.session_state.data_manager.add_department(code, name, parent_id):
                        st.success("Department added successfully")
                        st.rerun()
                    else:
                        st.error("Department code already exists")
                else:
                    st.error("Please fill in all required fields")

if __name__ == "__main__":
    render_departments_page()