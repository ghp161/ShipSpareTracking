import streamlit as st
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required
import navbar

current_page = "Inventory"
st.header(current_page)

navbar.nav(current_page)


@login_required
def render_inventory_page():
    #st.title("Inventory Management")

    tab1, tab2 = st.tabs(["View Inventory", "Add New Part"])

    with tab1:
        df = st.session_state.data_manager.get_all_parts()

        # Search and filter
        search_term = st.text_input("Search parts by name or number")
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False)
                    | df['part_number'].str.contains(search_term, case=False)]

        st.dataframe(df[[
            'part_number', 'name', 'quantity', 'min_order_level', 'barcode'
        ]],
                     hide_index=True)

        # Edit part
        if not df.empty:
            part_to_edit = st.selectbox("Select part to edit",
                                        df['name'].tolist())

            if part_to_edit:
                part_data = df[df['name'] == part_to_edit].iloc[0]
                with st.form("edit_part_form"):
                    new_quantity = st.number_input("Quantity",
                                                   value=int(
                                                       part_data['quantity']),
                                                   min_value=0)
                    new_min_level = st.number_input(
                        "Minimum Order Level",
                        value=int(part_data['min_order_level']),
                        min_value=0)
                    new_min_quantity = st.number_input(
                        "Minimum Order Quantity",
                        value=int(part_data['min_order_quantity']),
                        min_value=1)

                    if st.form_submit_button("Update Part"):
                        st.session_state.data_manager.update_spare_part(
                            part_data['id'], {
                                'name': part_data['name'],
                                'description': part_data['description'],
                                'quantity': new_quantity,
                                'min_order_level': new_min_level,
                                'min_order_quantity': new_min_quantity
                            })
                        st.success("Part updated successfully!")
                        st.rerun()

    with tab2:
        with st.form("add_part_form"):
            part_number = st.text_input("Part Number")
            name = st.text_input("Part Name")
            description = st.text_area("Description")
            quantity = st.number_input("Initial Quantity", min_value=0)
            min_order_level = st.number_input("Minimum Order Level",
                                              min_value=0)
            min_order_quantity = st.number_input("Minimum Order Quantity",
                                                 min_value=1)

            if st.form_submit_button("Add Part"):
                if part_number and name:
                    barcode = st.session_state.barcode_handler.generate_unique_barcode(
                    )
                    success = st.session_state.data_manager.add_spare_part({
                        'part_number':
                        part_number,
                        'name':
                        name,
                        'description':
                        description,
                        'quantity':
                        quantity,
                        'min_order_level':
                        min_order_level,
                        'min_order_quantity':
                        min_order_quantity,
                        'barcode':
                        barcode
                    })

                    if success:
                        st.success("Part added successfully!")
                        st.markdown(f"Generated barcode: `{barcode}`")
                        barcode_image = st.session_state.barcode_handler.generate_barcode(
                            barcode)
                        st.image(f"data:image/png;base64,{barcode_image}")
                    else:
                        st.error("Part number already exists!")
                else:
                    st.error("Part number and name are required!")


if __name__ == "__main__":
    render_inventory_page()
