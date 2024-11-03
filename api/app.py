import os
import json
import logging
import string
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Kaneki')  # Replace 'fallback_secret_key' with a secure fallback for development


# Get credentials from environment variables (set these in Vercel)
USERNAME = os.environ.get('APP_USERNAME', 'Aziz')  # Get from env or fallback
PASSWORD = os.environ.get('APP_PASSWORD', '1738')  # Get from env or fallback


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:  # Check if the user is logged in
            return redirect(url_for('login'))  # Redirect to login page if not
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    if 'username' in session:  # Check if the user is logged in
        return redirect(url_for('index'))  # Redirect to index if logged in
    return redirect(url_for('login'))  # Redirect to login page if not
 


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Debug: print out the values for inspection
        logger.info(f"Attempting login with Username: {username}, Password: {password}")

        # Check if the provided username and password match
        if username == USERNAME and password == PASSWORD:
            session['username'] = username  # Store username in session
            logger.info(f"User {username} logged in successfully.")
            return redirect(url_for('index'))  # Redirect to the main page after successful login
        else:
            flash('Invalid username or password', 'danger')  # Flash an error message
            logger.warning(f"Invalid login attempt for Username: {username}")

    return render_template('login.html')  # Render the login page



@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    flash('You have been successfully logged out.', 'success')  # Flash a logout success message
    return redirect(url_for('login'))  # Redirect to login page after logout




# Set up basic logging
logging.basicConfig(level=logging.INFO)  # You can change the level to DEBUG for more verbosity
logger = logging.getLogger(__name__)  # Create a logger

# Load credentials from environment or file
def load_credentials():
    try:
        credentials_info = os.getenv('GOOGLE_SHEETS_CREDENTIALS')

        if credentials_info is None:
            logger.error("No credentials found in environment variable.")
            raise Exception("No credentials found in environment variable.")
        
        credentials_dict = json.loads(credentials_info)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        
        return credentials

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding credentials: {str(e)}")
        raise Exception(f"Error decoding credentials: {str(e)}")

    except Exception as e:
        logger.error(f"Valid credentials could not be loaded: {str(e)}")
        raise Exception(f"Valid credentials could not be loaded: {str(e)}")

def generate_random_order_id(length=4):
    characters = string.ascii_letters + string.digits  # Letters and digits
    order_id = ''.join(random.choice(characters) for _ in range(length))
    return order_id

# Function to ensure the order ID is unique
def generate_unique_order_id(existing_ids, length=4):
    while True:
        order_id = generate_random_order_id(length)
        if order_id not in existing_ids:
            return order_id

def fetch_orders_from_sheet():
    credentials = load_credentials()
    service = build('sheets', 'v4', credentials=credentials)
    spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
    range_name = 'Sheet1!A2:E999'  # Adjust range as needed

    response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    orders = response.get('values', [])
    
    if not orders:
        logger.warning("No orders found in the specified range.")
    return orders
        
@app.route('/index')
@login_required  # Protect this route
def index():
    logger.info("Index route accessed.")
    return render_template('index.html')

@app.route('/google-api', methods=['GET'])
def call_google_api():
    logger.info("call_google_api route accessed.")
    try:
        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)
        spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
        range_name = 'Sheet1!A2:D10'

        response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        logger.info(f"Data fetched from Google Sheets: {response.get('values', [])}")
        return jsonify(response.get('values', []))

    except Exception as e:
        logger.error(f"Error in call_google_api: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/show_all', methods=['GET'])
def show_all():
    logger.info("show_all route accessed.")
    try:
        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)
        spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
        range_name = 'Sheet1!A2:E999'

        logger.debug(f"Fetching data from Google Sheets: {spreadsheet_id}, Range: {range_name}.")
        response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        
        orders = response.get('values', [])
        logger.info(f"Data fetched successfully from Google Sheets: {orders}")

        if not orders:
            logger.warning("No orders found in the specified range.")
            return jsonify({"error": "No orders found."}), 404
        
        # Group orders by customer name
        customer_orders = {}
        for order in orders:
            customer_name = order[1]  # Assuming customer name is in the second column (index 1)
            if customer_name not in customer_orders:
                customer_orders[customer_name] = []
            customer_orders[customer_name].append(order)

        # Flatten the customer orders into the required format
        grouped_orders = []
        for customer_name, orders in customer_orders.items():
            for order in orders:
                grouped_orders.append({
                    'order_id': order[0],  # Assuming Order ID is in the first column (index 0)
                    'customer_name': customer_name,
                    'order_details': order[2],  # Assuming Order Details is in the third column (index 2)
                    'order_date': order[3],  # Assuming Order Date is in the fourth column (index 3)
                    'status': order[4],  # Assuming Status is in the fifth column (index 4)
                })

        return jsonify(grouped_orders)

    except Exception as e:
        logger.error(f"Error in show_all: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/delete_order', methods=['POST'])
def delete_order():
    logger.info("delete_order route accessed.")
    try:
        order_id = request.json.get('order_id')
        logger.info(f"Request to delete order with ID: {order_id}")

        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)

        spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
        range_name = 'Sheet1!A2:E999'

        response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        orders = response.get('values', [])

        if not orders:
            logger.warning("No orders found in the spreadsheet.")
            return jsonify({"error": "No orders found."}), 404

        row_to_delete = None
        for index, order in enumerate(orders):
            if order[0] == order_id:
                row_to_delete = index + 2  # +2 because we're starting from row 2 in the sheet
                break
        
        if row_to_delete is None:
            logger.warning(f"Order ID {order_id} not found.")
            return jsonify({"error": "Order ID not found."}), 404

        # Delete the row by shifting up the remaining rows
        requests = [{
            'deleteDimension': {
                'range': {
                    'sheetId': 0,  # Assuming you are working with the first sheet
                    'dimension': 'ROWS',
                    'startIndex': row_to_delete - 1,
                    'endIndex': row_to_delete,  # endIndex is exclusive
                }
            }
        }]
        body = {
            'requests': requests
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

        logger.info(f"Order with ID {order_id} deleted successfully.")
        return jsonify({"success": True, "message": "Order deleted successfully."})

    except Exception as e:
        logger.error(f"Error in delete_order: {str(e)}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

@app.route('/filter_orders', methods=['POST'])
def filter_orders():
    try:
        data = request.json
        status = data.get('status', '')
        logger.info(f'Filtering orders by status: {status}')

        orders = fetch_orders_from_sheet()  # Fetch orders from Google Sheets
        if status:
            orders = [order for order in orders if order[4].lower() == status.lower()]  # Match case insensitive

        return jsonify(orders)
    except Exception as e:
        logger.error(f'Error filtering orders: {str(e)}')
        return jsonify({'error': 'An error occurred while filtering orders.'}), 500


@app.route('/search_orders', methods=['POST'])
def search_orders():
    logger.info("search_orders route accessed.")
    try:
        search_term = request.json.get('search_term', '')
        logger.info(f"Searching for orders with term: {search_term}")

        # Load Google credentials
        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)

        spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
        range_name = 'Sheet1!A2:E999'

        # Fetch existing orders
        response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        existing_orders = response.get('values', [])

        # Filter orders based on search term
        filtered_orders = [
            order for order in existing_orders
            if search_term.lower() in (order[0].lower() + ' ' + order[1].lower())  # Check against Order ID and Customer Name
        ]

        logger.info(f"Found {len(filtered_orders)} orders matching the search term.")
        return jsonify({"result": filtered_orders})  # Ensure to return the correct structure
    
    except Exception as e:
        logger.error(f"Error in search_orders: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/add_order', methods=['POST'])
def add_order():
    logger.info("add_order route accessed.")
    try:
        order_data = request.json
        logger.info(f"Adding order data: {order_data}")

        # Load Google credentials
        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)

        spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
        range_name = 'Sheet1!A2:E999'

        # Fetch existing orders to determine the next empty row
        response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        existing_orders = response.get('values', [])
        
        # Get existing order IDs to ensure the new ID is unique
        existing_order_ids = [order[0] for order in existing_orders]

        # Generate a unique order ID
        order_id = generate_unique_order_id(existing_order_ids)

        next_row = len(existing_orders) + 2  # +2 to account for header row

        # Prepare the data to add
        body = {
            'values': [[
                order_id,                         # Use the generated unique order ID
                order_data.get('customer_name'),
                order_data.get('order_details'),
                order_data.get('order_date'),
                order_data.get('status')
            ]]
        }

        # Append the new order data
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'Sheet1!A{next_row}',
            valueInputOption='RAW',
            body=body
        ).execute()

        logger.info(f"Order added successfully: {order_data}")
        return jsonify({"success": True, "message": "Order added successfully.", "order_id": order_id})

    except Exception as e:
        logger.error(f"Error in add_order: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/add_order.html')
def add_order_page():
    return render_template('add_order.html')

@app.route('/update_order', methods=['POST'])
def update_order():
    order_id = request.json['order_id']
    status = request.json['status']
    orders = sheet.get_all_records()

    for i, order in enumerate(orders):
        if order['Order ID'] == order_id:
            sheet.update_cell(i + 2, 5, status)  # Status is in the 5th column
            return {'success': True}

    return {'success': False, 'error': 'Order not found'}
@app.route('/update_status', methods=['POST'])
def update_status():
    logger.info("update_status route accessed.")
    try:
        data = request.json
        order_id = data.get('order_id')
        new_status = data.get('status')
        logger.info(f"Updating status for order ID: {order_id} to {new_status}")

        # Load Google credentials and get the sheet
        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)

        spreadsheet_id = '1MoINYcyftNLELcIMo3M8V9zxicvl861CZiKxmnNuDfM'
        range_name = 'Sheet1!A2:E999'

        # Get current orders to find the row with the order_id
        response = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        orders = response.get('values', [])

        if not orders:
            return jsonify({"error": "No orders found."}), 404

        # Find the row index to update
        row_to_update = None
        for index, order in enumerate(orders):
            if order[0] == order_id:  # Assuming the Order ID is in the first column
                row_to_update = index + 2  # +2 because we're starting from row 2 in the sheet
                break

        if row_to_update is None:
            return jsonify({"error": "Order ID not found."}), 404

        # Update the status (assuming it's in the fifth column, index 4)
        values = [order[:4] + [new_status]]  # Keep other details and update status
        body = {
            'values': values
        }
        service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=f'Sheet1!A{row_to_update}:E{row_to_update}', valueInputOption='RAW', body=body).execute()

        logger.info(f"Order with ID {order_id} updated successfully.")
        return jsonify({"success": True, "message": "Status updated successfully."})

    except Exception as e:
        logger.error(f"Error in update_status: {str(e)}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500
    
if __name__ == '__main__':
    app.run(debug=True)
