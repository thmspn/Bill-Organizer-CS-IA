# Import necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import matplotlib.dates as mdates
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend to avoid issues with Flask and GUI-based backends

# Initialize the Flask application
app = Flask(__name__, template_folder='Frontend')
app.secret_key = 'csia'  # Secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bill_organizer.db'  # Database URI
db = SQLAlchemy(app)  # Initialize SQLAlchemy with the Flask app

# Create the database tables within the application context
with app.app_context():
    db.create_all()  # This creates all the tables defined in the models

# Define the home route
@app.route('/')
def home():
    return render_template('auth.html')  # Render the authentication template

# Define the login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']  # Get the username from the form
    password = request.form['password'].encode('utf-8')  # Get the password and encode it

    user = User.query.filter_by(username=username).first()  # Query the database for the user

    # Check if the user exists and the password is correct
    if user and bcrypt.checkpw(password, user.password.encode('utf-8')):
        flash('Login successful!', 'success')  # Flash a success message
        return redirect(url_for('dashboard', user_id=user.id))  # Redirect to the dashboard
    else:
        flash('Invalid username or password', 'error')  # Flash an error message
        return redirect(url_for('home'))  # Redirect back to the home page

# Define the signup route
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']  # Get the username from the form
    password = request.form['password'].encode('utf-8')  # Get the password and encode it
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())  # Hash the password

    # Check if the username already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists!', 'error')  # Flash an error message
        return redirect(url_for('home'))  # Redirec t back to the home page

    # Create a new user and add it to the database
    new_user = User(username=username, password=hashed_password.decode('utf-8'))
    db.session.add(new_user)
    db.session.commit()

    flash('Registration successful! Please login.', 'success')  # Flash a success message
    return redirect(url_for('home'))  # Redirect back to the home page

# Define the dashboard route
@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = User.query.get_or_404(user_id)  # Get the user or return a 404 error if not found

    # Get sorting parameters from the request
    sort = request.args.get('sort', 'date')  # Default to sorting by date
    order = request.args.get('order', 'asc')  # Default to ascending order

    # Get the selected year from the request
    selected_year = request.args.get('year', 'all_time')  # Default to 'all_time'

    # Fetch bills for each type(water, electricity, and gas)
    water_bills = WaterBill.query.filter_by(user_id=user_id).all()
    electricity_bills = ElectricityBill.query.filter_by(user_id=user_id).all()
    gas_bills = GasBill.query.filter_by(user_id=user_id).all()

    # Filter bills based on the selected year
    if selected_year != 'all_time':
        selected_year = int(selected_year)
        water_bills = [bill for bill in water_bills if bill.date.year == selected_year]
        electricity_bills = [bill for bill in electricity_bills if bill.date.year == selected_year]
        gas_bills = [bill for bill in gas_bills if bill.date.year == selected_year]

    # Calculate averages for water bills
    water_avg_rate = sum(bill.rate for bill in water_bills) / len(water_bills) if water_bills else 0
    water_avg_usage = sum(bill.usage for bill in water_bills) / len(water_bills) if water_bills else 0

    # Calculate averages for electricity bills
    electricity_avg_rate = sum(bill.rate for bill in electricity_bills) / len(electricity_bills) if electricity_bills else 0
    electricity_avg_usage = sum(bill.usage for bill in electricity_bills) / len(electricity_bills) if electricity_bills else 0

    # Calculate averages for gas bills
    gas_avg_rate = sum(bill.rate for bill in gas_bills) / len(gas_bills) if gas_bills else 0
    gas_avg_usage = sum(bill.usage for bill in gas_bills) / len(gas_bills) if gas_bills else 0

    # Get unique years for each bill type
    water_years = sorted({bill.date.year for bill in WaterBill.query.filter_by(user_id=user_id).all()}, reverse=True)
    electricity_years = sorted({bill.date.year for bill in ElectricityBill.query.filter_by(user_id=user_id).all()}, reverse=True)
    gas_years = sorted({bill.date.year for bill in GasBill.query.filter_by(user_id=user_id).all()}, reverse=True)

    # Render the dashboard template with all the data
    return render_template(
        'dashboard.html',
        user=user,
        water_bills=water_bills,
        electricity_bills=electricity_bills,
        gas_bills=gas_bills,
        water_avg_rate=water_avg_rate,
        water_avg_usage=water_avg_usage,
        electricity_avg_rate=electricity_avg_rate,
        electricity_avg_usage=electricity_avg_usage,
        gas_avg_rate=gas_avg_rate,
        gas_avg_usage=gas_avg_usage,
        water_years=water_years,
        electricity_years=electricity_years,
        gas_years=gas_years,
        selected_year=selected_year,  # Pass selected_year to the template
        sort=sort,
        order=order
    )

# Define the User model
# This model represents the user table, which has the uid, username, password etc.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True) #uid
    username = db.Column(db.String(80), unique=True, nullable=False) #username
    password = db.Column(db.String(120), nullable=False) #password
    water_bills = db.relationship('WaterBill', backref='user', lazy=True) #relation to water bills
    electricity_bills = db.relationship('ElectricityBill', backref='user', lazy=True) #relation to electricity bills
    gas_bills = db.relationship('GasBill', backref='user', lazy=True) #relation to gas bills

#For all the bill models, the uid is key that links each table to the certatin user
# Define the WaterBill model
class WaterBill(db.Model):
    id = db.Column(db.Integer, primary_key=True) #bill id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usage = db.Column(db.Float, nullable=False)  # in cubic meters
    rate = db.Column(db.Float, nullable=False)  # rate per cubic meter
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # calculated as usage * rate

# Define the ElectricityBill model
class ElectricityBill(db.Model):
    id = db.Column(db.Integer, primary_key=True) #bill id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usage = db.Column(db.Float, nullable=False)  # in kWh
    rate = db.Column(db.Float, nullable=False)  # rate per kWh
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # calculated as usage * rate

# Define the GasBill model
class GasBill(db.Model):
    id = db.Column(db.Integer, primary_key=True) #bill id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usage = db.Column(db.Float, nullable=False)  # in cubic meters
    rate = db.Column(db.Float, nullable=False)  # rate per cubic meter
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # calculated as usage * rate

# Define the BillManager class to handle bill operations
class BillManager:
    def __init__(self, bill_type):
        self.bill_type = bill_type

    def add_bill(self, user_id):
        try: #using try and except to make sure that the user inputs the correct data and doesn't crash the program
            # Get form data
            usage = float(request.form['usage'])
            rate = float(request.form['rate'])
            month_year = request.form['date']
            date = datetime.strptime(month_year + '-01', '%Y-%m-%d').date()

            # Calculate amount based on bill type
            if self.bill_type == 'water' or self.bill_type == 'electricity':
                amount = (usage * rate) / 100  # Convert cents to dollars
            elif self.bill_type == 'gas':
                amount = usage * rate  # Amount in dollars

            # Validation
            #using if statements to make sure that the user inputs the correct data
            if usage <= 0 or rate <= 0:
                flash('Usage and rate must be positive numbers.', 'error')
                return redirect(url_for('dashboard', user_id=user_id))
            if date > datetime.now().date():
                flash('Date cannot be in the future.', 'error')
                return redirect(url_for('dashboard', user_id=user_id))

            # Create the bill based on the type using if and elif
            if self.bill_type == 'water':
                new_bill = WaterBill(user_id=user_id, usage=usage, rate=rate, date=date, amount=amount)
            elif self.bill_type == 'electricity':
                new_bill = ElectricityBill(user_id=user_id, usage=usage, rate=rate, date=date, amount=amount)
            elif self.bill_type == 'gas':
                new_bill = GasBill(user_id=user_id, usage=usage, rate=rate, date=date, amount=amount)

            # Add the new bill to the database
            db.session.add(new_bill)
            db.session.commit()
            flash(f'{self.bill_type.capitalize()} bill added successfully!', 'success')
            #if an error occurs it will flash instead of crashing system
        except ValueError:
            flash('Invalid input. Please check the form data.', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

        return redirect(url_for('dashboard', user_id=user_id))

    def delete_bill(self, bill_id):
        # Get the bill based on the type using if and elif
        if self.bill_type == 'water':
            bill = WaterBill.query.get_or_404(bill_id)
        elif self.bill_type == 'electricity':
            bill = ElectricityBill.query.get_or_404(bill_id)
        elif self.bill_type == 'gas':
            bill = GasBill.query.get_or_404(bill_id)

        # Delete the bill from the database using built in functions
        db.session.delete(bill)
        db.session.commit()
        flash(f'{self.bill_type.capitalize()} bill deleted successfully!', 'success')
        return redirect(url_for('dashboard', user_id=bill.user_id))

    def edit_bill(self, bill_id):
        # Get the bill based on the type
        if self.bill_type == 'water':
            bill = WaterBill.query.get_or_404(bill_id)
        elif self.bill_type == 'electricity':
            bill = ElectricityBill.query.get_or_404(bill_id)
        elif self.bill_type == 'gas':
            bill = GasBill.query.get_or_404(bill_id)
        #again the use of try and except to not crash the system
        try:
            # Update the bill with new data from the form
            bill.usage = float(request.form['usage'])
            bill.rate = float(request.form['rate'])
            month_year = request.form['date']
            bill.date = datetime.strptime(month_year + '-01', '%Y-%m-%d').date()

            # Calculate amount based on bill type
            if self.bill_type == 'water' or self.bill_type == 'electricity':
                bill.amount = (bill.usage * bill.rate) / 100  # Convert cents to dollars
            elif self.bill_type == 'gas':
                bill.amount = bill.usage * bill.rate  # Amount in dollars

            # Commit the changes to the database
            db.session.commit()
            flash(f'{self.bill_type.capitalize()} bill updated successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

        return redirect(url_for('dashboard', user_id=bill.user_id))

# Define routes for bill operations
# Route Adding Water Bill
@app.route('/add_water_bill/<int:user_id>', methods=['POST'])
def add_water_bill(user_id):
    return BillManager('water').add_bill(user_id)
# Route Adding Electricity Bill
@app.route('/add_electricity_bill/<int:user_id>', methods=['POST'])
def add_electricity_bill(user_id):
    return BillManager('electricity').add_bill(user_id)
# Route Adding Gas Bill
@app.route('/add_gas_bill/<int:user_id>', methods=['POST'])
def add_gas_bill(user_id):
    return BillManager('gas').add_bill(user_id)
# Route Deleting Water Bill
@app.route('/delete_water_bill/<int:bill_id>', methods=['POST'])
def delete_water_bill(bill_id):
    return BillManager('water').delete_bill(bill_id)
# Route Deleting Electricity Bill   
@app.route('/delete_electricity_bill/<int:bill_id>', methods=['POST'])
def delete_electricity_bill(bill_id):
    return BillManager('electricity').delete_bill(bill_id)
# Route Deleting Gas Bill
@app.route('/delete_gas_bill/<int:bill_id>', methods=['POST'])
def delete_gas_bill(bill_id):
    return BillManager('gas').delete_bill(bill_id)
# Route Editing Water Bill
@app.route('/edit_water_bill/<int:bill_id>', methods=['POST'])
def edit_water_bill(bill_id):
    return BillManager('water').edit_bill(bill_id)
# Route Editing Electricity Bill
@app.route('/edit_electricity_bill/<int:bill_id>', methods=['POST'])
def edit_electricity_bill(bill_id):
    return BillManager('electricity').edit_bill(bill_id)
# Route Editing Gas Bill
@app.route('/edit_gas_bill/<int:bill_id>', methods=['POST'])
def edit_gas_bill(bill_id):
    return BillManager('gas').edit_bill(bill_id)

# Define routes for filtering bills
# Route for filtering water bills
@app.route('/filter_water_bills/<int:user_id>', methods=['GET'])
def filter_water_bills(user_id):
    return filter_bills(user_id, 'water')
# Route for filtering electricity bills
@app.route('/filter_electricity_bills/<int:user_id>', methods=['GET'])
def filter_electricity_bills(user_id):
    return filter_bills(user_id, 'electricity')
# Route for filtering gas bills
@app.route('/filter_gas_bills/<int:user_id>', methods=['GET'])
def filter_gas_bills(user_id):
    return filter_bills(user_id, 'gas')

def filter_bills(user_id, bill_type):
    try:
        # Get filter parameters from the request
        usage_min = request.args.get('usage_min', type=float)
        usage_max = request.args.get('usage_max', type=float)
        rate_min = request.args.get('rate_min', type=float)
        rate_max = request.args.get('rate_max', type=float)
        amount_min = request.args.get('amount_min', type=float)
        amount_max = request.args.get('amount_max', type=float)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Dictionary to store bill models
        BILL_MODELS = {
            'water': WaterBill,
            'electricity': ElectricityBill,
            'gas': GasBill
        }
        # Ensure valid bill type
        bill_model = BILL_MODELS.get(bill_type)
        if not bill_model:
            flash(f"Invalid bill type: {bill_type}", 'error')
            return redirect(url_for('dashboard', user_id=user_id))
       
        # Start query
        query = bill_model.query.filter_by(user_id=user_id)
       
        # Apply filters **ONLY IF VALUES EXIST**
        #Using if statements to make sure data is right
        #Usage Filter
        if usage_min is not None:
            query = query.filter(bill_model.usage >= usage_min)
        if usage_max is not None:
            query = query.filter(bill_model.usage <= usage_max)
        #Rate Filter
        if rate_min is not None:
            query = query.filter(bill_model.rate >= rate_min)
        if rate_max is not None:
            query = query.filter(bill_model.rate <= rate_max)
        #Amount Filter
        if amount_min is not None:
            query = query.filter(bill_model.amount >= amount_min)
        if amount_max is not None:
            query = query.filter(bill_model.amount <= amount_max)
        #Date Filter
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(bill_model.date >= start_date)
            except ValueError:
                flash("Invalid start date format. Use YYYY-MM-DD.", 'error')
                return redirect(url_for('dashboard', user_id=user_id))
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(bill_model.date <= end_date)
            except ValueError:
                flash("Invalid end date format. Use YYYY-MM-DD.", 'error')
                return redirect(url_for('dashboard', user_id=user_id))

        # Get the filtered bills
        filtered_bills = query.all()

        # Fetch all bills for other types (water, electricity, gas)
        water_bills = WaterBill.query.filter_by(user_id=user_id).all()
        electricity_bills = ElectricityBill.query.filter_by(user_id=user_id).all()
        gas_bills = GasBill.query.filter_by(user_id=user_id).all()

        # Calculate averages for water bills
        water_avg_rate = sum(bill.rate for bill in water_bills) / len(water_bills) if water_bills else 0
        water_avg_usage = sum(bill.usage for bill in water_bills) / len(water_bills) if water_bills else 0

        # Calculate averages for electricity bills
        electricity_avg_rate = sum(bill.rate for bill in electricity_bills) / len(electricity_bills) if electricity_bills else 0
        electricity_avg_usage = sum(bill.usage for bill in electricity_bills) / len(electricity_bills) if electricity_bills else 0

        # Calculate averages for gas bills
        gas_avg_rate = sum(bill.rate for bill in gas_bills) / len(gas_bills) if gas_bills else 0
        gas_avg_usage = sum(bill.usage for bill in gas_bills) / len(gas_bills) if gas_bills else 0

        # Render the dashboard template with the filtered data
        return render_template(
            'dashboard.html',
            user=User.query.get_or_404(user_id),
            water_bills=filtered_bills if bill_type == 'water' else water_bills,
            electricity_bills=filtered_bills if bill_type == 'electricity' else electricity_bills,
            gas_bills=filtered_bills if bill_type == 'gas' else gas_bills,
            water_avg_rate=water_avg_rate,
            water_avg_usage=water_avg_usage,
            electricity_avg_rate=electricity_avg_rate,
            electricity_avg_usage=electricity_avg_usage,
            gas_avg_rate=gas_avg_rate,
            gas_avg_usage=gas_avg_usage,
            water_years=sorted({bill.date.year for bill in WaterBill.query.filter_by(user_id=user_id).all()}, reverse=True),
            electricity_years=sorted({bill.date.year for bill in ElectricityBill.query.filter_by(user_id=user_id).all()}, reverse=True),
            gas_years=sorted({bill.date.year for bill in GasBill.query.filter_by(user_id=user_id).all()}, reverse=True),
            selected_year='all_time',  # Reset selected year for filtered view
            sort='date',
            order='asc'
        )

    except Exception as e:
        flash(f'An error occurred while filtering {bill_type} bills: {str(e)}', 'error')
        return redirect(url_for('dashboard', user_id=user_id))

# Define the route to generate graphs
@app.route('/generate_graph/<int:user_id>')
def generate_graph(user_id):
    try :#using try and except to make sure that the user inputs the correct data and doesn't crash the program
        # Get filter parameters from the request
        bill_type = request.args.get('type', '').strip()
        time_range = request.args.get('time_range', 'all_time')  # Default to 'all_time'

        # Fetch bills based on the bill type using if and elif statements
        if bill_type == 'water':
            bills = WaterBill.query.filter_by(user_id=user_id).all()
        elif bill_type == 'electricity':
            bills = ElectricityBill.query.filter_by(user_id=user_id).all()
        elif bill_type == 'gas':
            bills = GasBill.query.filter_by(user_id=user_id).all()
        else:
            flash('Invalid bill type.', 'error')
            return redirect(url_for('dashboard', user_id=user_id))

        # Filter bills based on the selected time range
        if time_range != 'all_time':
            selected_year = int(time_range)
            bills = [bill for bill in bills if bill.date.year == selected_year]

        # Convert bills to a DataFrame
        # First selected data is sent into a list then using pandas to convert the bills into a dataframe
        data = []
        for bill in bills:
            data.append({
                'Date': bill.date.strftime('%Y-%m'),
                'Usage': bill.usage,
                'Rate': bill.rate,
                'Amount': bill.amount
            })
        df = pd.DataFrame(data)

        # Convert 'Date' to datetime for sorting
        df['Date'] = pd.to_datetime(df['Date'])

        # Group by Date and aggregate Usage and Amount
        df_aggregated = df.groupby('Date').agg({
            'Usage': 'sum',
            'Rate': 'first',  # Rate is the same for all bills on the same date
            'Amount': 'sum'
        }).reset_index()

        # Sort by date
        df_aggregated = df_aggregated.sort_values(by='Date')

        # Create a larger figure to prevent overcrowding
        plt.figure(figsize=(12, 12))

        # Plot Month vs Rate
        plt.subplot(3, 1, 1)
        plt.plot(df_aggregated['Date'], df_aggregated['Rate'], marker='o', color='blue', label='Rate')
        # Add trendline for Rate
        z = np.polyfit(mdates.date2num(df_aggregated['Date']), df_aggregated['Rate'], 1)
        p = np.poly1d(z)
        # Plot the trendline
        plt.plot(df_aggregated['Date'], p(mdates.date2num(df_aggregated['Date'])), "r--", label='Trendline')
        # Add title, labels, and legend
        plt.title(f'{bill_type.capitalize()} Bills - Monthly Rate')
        plt.xlabel('Month')
        plt.ylabel('Rate (¢)' if bill_type in ['water', 'electricity'] else 'Rate ($)')
        plt.grid(True)
        plt.legend()

        # Add labels for Rate points (raised slightly for clarity of the graph)
        # using a for statemnt to add labels to the graph as itll stop once it reaches the end of the data
        for i, row in df_aggregated.iterrows(): 
            plt.text(row['Date'], row['Rate'] + 5, f"{row['Rate']:.2f}", ha='center', va='bottom', fontsize=8)

        # Adjust y-axis limits for Rate subplot
        plt.ylim(bottom=min(df_aggregated['Rate']) * 0.9, top=max(df_aggregated['Rate']) * 1.1)

        # Plot Month vs Usage
        plt.subplot(3, 1, 2)
        plt.plot(df_aggregated['Date'], df_aggregated['Usage'], marker='o', color='green', label='Usage')
        # Add trendline for Usage
        z = np.polyfit(mdates.date2num(df_aggregated['Date']), df_aggregated['Usage'], 1)
        p = np.poly1d(z)
        # Plot the trendline
        plt.plot(df_aggregated['Date'], p(mdates.date2num(df_aggregated['Date'])), "r--", label='Trendline')
        # Add title, labels, and legend
        plt.title(f'{bill_type.capitalize()} Bills - Monthly Usage')
        plt.xlabel('Month')
        plt.ylabel('Usage (m³)' if bill_type in ['water', 'gas'] else 'Usage (kWh)')
        plt.grid(True)
        plt.legend()

        # Add labels for Usage points (raised slightly)
        # using a for statemnt to add labels to the graph as itll stop once it reaches the end of the data
        for i, row in df_aggregated.iterrows(): 
            plt.text(row['Date'], row['Usage'] + 0.5, f"{row['Usage']:.2f}", ha='center', va='bottom', fontsize=8)

        # Adjust y-axis limits for Usage subplot
        plt.ylim(bottom=min(df_aggregated['Usage']) * 0.9, top=max(df_aggregated['Usage']) * 1.1)

        # Plot Month vs Amount
        plt.subplot(3, 1, 3)
        plt.plot(df_aggregated['Date'], df_aggregated['Amount'], marker='o', color='red', label='Amount')
        # Add trendline for Amount
        z = np.polyfit(mdates.date2num(df_aggregated['Date']), df_aggregated['Amount'], 1)
        p = np.poly1d(z)
        # Plot the trendline
        plt.plot(df_aggregated['Date'], p(mdates.date2num(df_aggregated['Date'])), "r--", label='Trendline')
        # Add title, labels, and legend
        plt.title(f'{bill_type.capitalize()} Bills - Monthly Amount')
        plt.xlabel('Month')
        plt.ylabel('Amount ($)')
        plt.grid(True)
        plt.legend()

        # Add labels for Amount points (raised slightly)
        # using a for statemnt to add labels to the graph as itll stop once it reaches the end of the data
        for i, row in df_aggregated.iterrows():
            plt.text(row['Date'], row['Amount'] + 0.05, f"${row['Amount']:.2f}", ha='center', va='bottom', fontsize=8)

        # Adjust y-axis limits for Amount subplot
        plt.ylim(bottom=min(df_aggregated['Amount']) * 0.9, top=max(df_aggregated['Amount']) * 1.1)

        # Format x-axis dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.gcf().autofmt_xdate()

        # Adjust layout to prevent overlap
        plt.tight_layout()

        # Save the plot to a BytesIO object
        img = BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()

        # Return the image as a response
        return send_file(img, mimetype='image/png')
    except Exception as e: #if an error occurs it will flash instead of crashing system
        flash(f'An error occurred while generating the graph: {str(e)}', 'error')
        return redirect(url_for('dashboard', user_id=user_id))

# Define the route to export CSV
@app.route('/export_csv/<int:user_id>')
def export_csv(user_id):
    try:
        # Fetch all bills for the user
        water_bills = WaterBill.query.filter_by(user_id=user_id).all()
        electricity_bills = ElectricityBill.query.filter_by(user_id=user_id).all()
        gas_bills = GasBill.query.filter_by(user_id=user_id).all()

        # Combine all bills into a single DataFrame
        # First all data is sent into a list then using pandas to convert the bills into a dataframe
        #Data is sorted by type, usage, rate, date and amount
        data = []
        for bill in water_bills:
            data.append(('Water', bill.usage, bill.rate, bill.date.strftime('%Y-%m-%d'), bill.amount))
        for bill in electricity_bills:
            data.append(('Electricity', bill.usage, bill.rate, bill.date.strftime('%Y-%m-%d'), bill.amount))
        for bill in gas_bills:
            data.append(('Gas', bill.usage, bill.rate, bill.date.strftime('%Y-%m-%d'), bill.amount))

        df = pd.DataFrame(data, columns=['Type', 'Usage', 'Rate', 'Date', 'Amount'])

        # Convert DataFrame to CSV
        csv = df.to_csv(index=False)

        # Return CSV as a downloadable file
        return send_file(
            BytesIO(csv.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='bills.csv'
        )
    except Exception as e: #if an error occurs it will flash instead of crashing system
        flash(f'An error occurred while exporting CSV: {str(e)}', 'error')
        return redirect(url_for('dashboard', user_id=user_id))

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)  # Run the app in debug mode(this is for me to debug with)