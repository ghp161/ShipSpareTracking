import streamlit as st
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required
import navbar
from datetime import datetime

current_page = "Inventory"
st.header(current_page)

navbar.nav(current_page)


@login_required
def render_inventory_page():
    tab1, tab2 = st.tabs(["View Inventory", "Add New Part"])

    with tab1:
        df = st.session_state.data_manager.get_all_parts()

        # Search and filter
        search_term = st.text_input("Search parts by name or number")
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False)
                    | df['part_number'].str.contains(search_term, case=False)]

        st.dataframe(df[[
            'part_number', 'name', 'quantity', 'min_order_level', 'barcode',
            'location', 'status', 'last_maintenance_date',
            'next_maintenance_date'
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
                    new_location = st.selectbox(
                        "Location", [
                            "Engine Room", "Hull", "Bridge",
                            "Combat Information Center", "Deck and Mast",
                            "Bow", "Deck", "Mast", "Throughout Ship",
                            "Mess Deck", "Flight Deck"
                        ],
                        index=[
                            "Engine Room", "Hull", "Bridge",
                            "Combat Information Center", "Deck and Mast",
                            "Bow", "Deck", "Mast", "Throughout Ship",
                            "Mess Deck", "Flight Deck"
                        ].index(part_data['location']))
                    new_status = st.selectbox(
                        "Status",
                        ["Operational", "Under Maintenance", "In Store"],
                        index=["Operational", "Under Maintenance",
                               "In Store"].index(part_data['status']))
                    new_last_maintenance_date = st.date_input(
                        "Last Maintenance Date",
                        value=datetime.strptime(
                            part_data['last_maintenance_date'],
                            '%Y-%m-%d').date())
                    new_next_maintenance_date = st.date_input(
                        "Next Maintenance Date",
                        value=datetime.strptime(
                            part_data['next_maintenance_date'],
                            '%Y-%m-%d').date())

                    if st.form_submit_button("Update Part"):
                        if new_last_maintenance_date > datetime.now().date():
                            st.error(
                                "Last Maintenance Date should not be greater than the current date."
                            )
                        elif new_next_maintenance_date <= datetime.now().date(
                        ):
                            st.error(
                                "Next Maintenance Date should be greater than the current date."
                            )
                        else:
                            st.session_state.data_manager.update_spare_part(
                                part_data['id'], {
                                    'name':
                                    part_data['name'],
                                    'description':
                                    part_data['description'],
                                    'quantity':
                                    new_quantity,
                                    'min_order_level':
                                    new_min_level,
                                    'min_order_quantity':
                                    new_min_quantity,
                                    'location':
                                    new_location,
                                    'status':
                                    new_status,
                                    'last_maintenance_date':
                                    new_last_maintenance_date.strftime(
                                        '%Y-%m-%d'),
                                    'next_maintenance_date':
                                    new_next_maintenance_date.strftime(
                                        '%Y-%m-%d')
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
            location = st.selectbox("Location", [
                "Engine Room", "Hull", "Bridge", "Combat Information Center",
                "Deck and Mast", "Bow", "Deck", "Mast", "Throughout Ship",
                "Mess Deck", "Flight Deck"
            ])
            status = st.selectbox(
                "Status", ["Operational", "Under Maintenance", "In Store"])
            last_maintenance_date = st.date_input("Last Maintenance Date")
            next_maintenance_date = st.date_input("Next Maintenance Date")

            if st.form_submit_button("Add Part"):
                if part_number and name:
                    if last_maintenance_date > datetime.now().date():
                        st.error(
                            "Last Maintenance Date should not be greater than the current date."
                        )
                    elif next_maintenance_date <= datetime.now().date():
                        st.error(
                            "Next Maintenance Date should be greater than the current date."
                        )
                    else:
                        barcode = st.session_state.barcode_handler.generate_unique_barcode(
                        )
                        success = st.session_state.data_manager.add_spare_part(
                            {
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
                                barcode,
                                'location':
                                location,
                                'status':
                                status,
                                'last_maintenance_date':
                                last_maintenance_date.strftime('%Y-%m-%d'),
                                'next_maintenance_date':
                                next_maintenance_date.strftime('%Y-%m-%d')
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
