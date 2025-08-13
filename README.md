# Ship Spare Parts Inventory Management System

A barcode-based inventory tracking system for ship spare parts management with hierarchical department structure, role-based access control, and advanced reporting capabilities.

## Features

- 🚢 **Barcode Management**: Generate and scan barcodes with ABC-D-1234 format
- 🏗️ **Hierarchical Departments**: Parent-child department structure with inheritance
- 🔐 **Role-Based Access**: Three user levels (Super User, Admin, User)
- 📊 **Advanced Analytics**: Stock levels, transaction trends, demand forecasting
- 📦 **Bulk Operations**: CSV import/export for inventory management
- 🚨 **Alerts**: Low stock and last piece level notifications
- 📱 **Mobile-Friendly**: Responsive web interface

## Installation

### Prerequisites
- Python 3.11+
- pip package manager

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ship-inventory-system.git
   cd ship-inventory-system
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run main.py
   ```

4. Access the app at `http://localhost:8501`

## Configuration

Edit `.streamlit/config.toml` for UI customization:
```toml
[theme]
primaryColor = "#0066cc"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

## Usage

### Default Credentials
- **Admin**: `admin` / `admin123`
- **Roles**:
  - Super User: Full system access
  - Admin: Limited admin privileges
  - User: Department-specific access

### Key Modules
1. **Inventory Management** (`pages/inventory.py`)
   - Add/edit spare parts
   - Bulk import via CSV
   - Department-wise views

2. **Operations** (`pages/operations.py`)
   - Barcode scanning interface
   - Check-in/check-out functionality

3. **Reports** (`pages/reports.py`)
   - Stock level analysis
   - Transaction history
   - Data export

4. **User Management** (`pages/admin.py`)
   - User creation/modification
   - Role assignment

## Database Schema
The SQLite database (`inventory.db`) contains four main tables:
1. `departments` - Hierarchical department structure
2. `spare_parts` - Inventory items with barcodes
3. `transactions` - Check-in/check-out records
4. `users` - Authentication and access control

## Deployment Options

### 1. Local Development
```bash
streamlit run main.py
```

### 2. Docker Container
```bash
docker build -t ship-inventory .
docker run -p 8501:8501 ship-inventory
```

### 3. Streamlit Sharing
1. Create `requirements.txt` from `pyproject.toml`
2. Deploy to Streamlit Community Cloud

## Screenshots

| Module | Preview |
|--------|---------|
| Login | ![Login Screen](screenshots/login.png) |
| Dashboard | ![Dashboard](screenshots/dashboard.png) |
| Barcode Scanning | ![Barcode](screenshots/barcode.png) |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

For issues or feature requests, please [open an issue](https://github.com/yourusername/ship-inventory-system/issues).

---

**Note**: Replace placeholder images and GitHub URLs with your actual project resources before publishing.
