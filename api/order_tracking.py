import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Define the scope
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load credentials
creds = ServiceAccountCredentials.from_json_keyfile_name("A:\\Dev\\Web App\\AK store\\ak-store-437214-4f4281b2eeea.json", scope)

# Authorize and create a client
client = gspread.authorize(creds)

# Open your Google Sheet by name
sheet = client.open("AK Store Order Tracking").sheet1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_order', methods=['POST'])
def get_order():
    order_id = request.form.get('order_id')  # Get order ID from form
    if not order_id:
        return jsonify({"error": "Order ID is required"}), 400

    # Fetch all records
    data = sheet.get_all_records()
    
    # Find the order details by ID
    order_details = next((item for item in data if item['Order ID'] == order_id), None)
    
    if order_details:
        return jsonify(order_details)  # Return order details as JSON
    else:
        return jsonify({"error": "Order not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
