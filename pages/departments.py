import streamlit as st
import pandas as pd
import sqlite3
from user_management import login_required
import navbar
from app_settings import set_page_configuration

set_page_configuration()

current_page = "Departments"
st.header(current_page)

navbar.nav(current_page)

class DepartmentManager:
    def __init__(self, db_path='inventory.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_departments_table()

    def create_departments_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES departments (id)
            )
        ''')
        self.conn.commit()

    def update_department(self, dept_id, code, name, parent_id=None):
        cursor = self.conn.cursor()
        try:
            # Prevent circular references
            if parent_id == dept_id:
                return False, "Department cannot be its own parent"
                
            cursor.execute('''
                UPDATE departments 
                SET code=?, name=?, parent_id=?
                WHERE id=?
            ''', (code, name, parent_id, dept_id))
            self.conn.commit()
            return True, None
        except sqlite3.Error as e:
            return False, str(e)

    def delete_department(self, dept_id):
        cursor = self.conn.cursor()
        try:
            # Check if department has children
            cursor.execute("SELECT COUNT(*) FROM departments WHERE parent_id=?", (dept_id,))
            child_count = cursor.fetchone()[0]
            if child_count > 0:
                return False, "Cannot delete department with child departments"

            # Check if department is used in spare_parts
            cursor.execute("SELECT COUNT(*) FROM spare_parts WHERE department_id=?", (dept_id,))
            part_count = cursor.fetchone()[0]
            if part_count > 0:
                return False, f"Cannot delete department - {part_count} inventory items reference it"

            cursor.execute("DELETE FROM departments WHERE id=?", (dept_id,))
            self.conn.commit()
            return True, None
        except sqlite3.Error as e:
            return False, str(e)

    def add_department(self, code, name, parent_id=None):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO departments (code, name, parent_id)
                VALUES (?, ?, ?)
            ''', (code, name, parent_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_departments_as_df(self):
        """Returns department data as a pandas DataFrame"""
        query = '''
            SELECT d1.id, d1.code, d1.name, 
                   COALESCE(d2.name, 'Top Level') as parent_name
            FROM departments d1
            LEFT JOIN departments d2 ON d1.parent_id = d2.id
            ORDER BY COALESCE(d1.parent_id, d1.id), d1.id
        '''
        return pd.read_sql_query(query, self.conn)

    def get_parent_options(self):
        """Returns options for parent department dropdown"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name FROM departments WHERE parent_id IS NULL
        ''')
        return cursor.fetchall()

@login_required
def render_departments_page():
    if 'dept_manager' not in st.session_state:
        st.session_state.dept_manager = DepartmentManager()

    tab1, tab2 = st.tabs(["Department Grid", "Add Department"])

    with tab1:
        #st.subheader("Department Data Grid")
        
        # Get data as DataFrame
        df = st.session_state.dept_manager.get_all_departments_as_df()
        
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
                    
                    parent_options = st.session_state.dept_manager.get_parent_options()
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
                            if st.session_state.dept_manager.update_department(dept_id, new_code, new_name, parent_id):
                                st.rerun()
                                st.success("Department Updated successfully")                                
                            else:
                                st.error("Department code already exists")
                    with col2:
                        if st.form_submit_button("Delete"):
                            # Implement delete logic
                            success, message = st.session_state.dept_manager.delete_department(dept_id)
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
            
            parent_options = st.session_state.dept_manager.get_parent_options()
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
                    if st.session_state.dept_manager.add_department(code, name, parent_id):
                        st.success("Department added successfully")
                        st.rerun()
                    else:
                        st.error("Department code already exists")
                else:
                    st.error("Please fill in all required fields")

if __name__ == "__main__":
    render_departments_page()