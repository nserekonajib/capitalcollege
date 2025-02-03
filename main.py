from flask import *
from functions import *
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz
import uuid
import threading
import time
from waitress import serve




app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Hardcoded credentials
USERNAME = "admin"
PASSWORD = "password123"

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['user'] = username  # Store user in session
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials, please try again."
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        # Read the db.xlsx to fetch data
        df = pd.read_excel('db.xlsx')
        
        # Remove any leading or trailing spaces in column names (to prevent issues)
        df.columns = df.columns.str.strip()
        
        # Normalize the 'status' column by stripping any unexpected whitespace
        df['status'] = df['status'].str.strip().str.lower()  # Ensure consistency
        
        # Calculate total students, active, and inactive students
        total_students = len(df)
        active_students = len(df[df['status'] == 'active'])
        inactive_students = len(df[df['status'] == 'inactive'])
        
        # Filter inactive students' details
        inactive_students_details = df[df['status'] == 'inactive']
        
        # Pass these values to the template
        return render_template('dashboard.html', 
                               total_students=total_students, 
                               active_students=active_students, 
                               inactive_students=inactive_students,
                               inactive_students_details=inactive_students_details)
    return redirect(url_for('login'))




@app.route("/upload_students", methods=["GET", "POST"])
def upload_students():
    if request.method == "POST":
        try:
            if "upload_file" in request.files:
                file = request.files["upload_file"]

                if not file or file.filename == "":
                    flash("No file selected. Please upload an Excel file.", "danger")
                    return redirect(url_for("upload_students"))

                if not file.filename.endswith(".xlsx"):
                    flash("Invalid file format. Only .xlsx files are allowed.", "danger")
                    return redirect(url_for("upload_students"))

                file_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
                
                try:
                    file.save(file_path)
                except Exception as e:
                    flash(f"Error saving file: {str(e)}", "danger")
                    return redirect(url_for("upload_students"))

                try:
                    process_excel(file_path)
                    flash("Bulk students uploaded successfully!", "success")
                except Exception as e:
                    flash(f"Error processing file: {str(e)}", "danger")

            elif request.form.get("manual_entry"):
                student = request.form.get("student", "").strip()
                email = request.form.get("email", "").strip()
                papers_taken = request.form.get("papers_taken", "").strip()

                if not student or not email or not papers_taken:
                    flash("All fields are required for manual entry.", "danger")
                    return redirect(url_for("upload_students"))

                success, message = add_student_manually(student, email, papers_taken)
                flash(message, "success" if success else "danger")

            else:
                flash("Invalid request. Please upload a file or enter student details manually.", "danger")

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

        return redirect(url_for("upload_students"))

    return render_template("upload_students.html")




CLASS_FILE = "class.xlsx"

@app.route('/create_class', methods=['GET', 'POST'])
def create_class():
    if request.method == 'POST':
        try:
            # Get form data
            paper_number = request.form.get('paper_number')
            paper_name = request.form.get('paper_name')
            zoom_link = request.form.get('zoom_link')
            start_time = request.form.get('start_time')

            # Validate required fields
            if not paper_number or not paper_name or not zoom_link or not start_time:
                flash("All fields are required!", "error")
                return redirect(url_for('create_class'))

            # Convert start time to Ugandan time (EAT - UTC+3)
            uganda_tz = pytz.timezone("Africa/Kampala")
            start_time = datetime.strptime(start_time, "%H:%M").time()
            formatted_time = start_time.strftime("%H:%M") + " EAT"

            # Load or create the class file
            if os.path.exists(CLASS_FILE):
                class_df = pd.read_excel(CLASS_FILE)
            else:
                class_df = pd.DataFrame(columns=["Paper Number", "Paper Name", "Zoom Link", "Start Time"])

            # Append new class entry
            new_entry = pd.DataFrame([{
                "Paper Number": paper_number,
                "Paper Name": paper_name,
                "Zoom Link": zoom_link,
                "Start Time": formatted_time
            }])

            class_df = pd.concat([class_df, new_entry], ignore_index=True)

            # Save to Excel
            class_df.to_excel(CLASS_FILE, index=False)

            flash("Class created successfully!", "success")
            return redirect(url_for('create_class'))

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('create_class'))

    return render_template('create_class.html')



# Load student database
def load_students():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        df.columns = df.columns.str.strip().str.lower()  # Ensure lowercase column names
        return df
    return pd.DataFrame(columns=["student", "email", "papers taken", "default password", "status"])

@app.route('/manage_student_account')
def manage_student_account():
    return render_template("manage_student_account.html")

@app.route('/get_students', methods=['GET'])
def get_students():
    search_query = request.args.get("search", "").lower()
    students_df = load_students()
    
    if search_query:
        students_df = students_df[
            students_df["student"].astype(str).str.lower().str.contains(search_query, na=False) |
            students_df["email"].astype(str).str.lower().str.contains(search_query, na=False)
        ]
    
    return jsonify(students_df.to_dict(orient="records"))

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    student_email = data.get("email")
    new_status = data.get("status")
    
    if not student_email or new_status not in ["Active", "Inactive"]:
        return jsonify({"error": "Invalid request"}), 400
    
    students_df = load_students()
    students_df.loc[students_df["email"] == student_email, "status"] = new_status
    students_df.to_excel(DB_FILE, index=False)
    
    return jsonify({"success": True, "new_status": new_status})

@app.route('/update_password', methods=['POST'])
def update_password():
    data = request.json
    student_email = data.get("email")
    new_password = data.get("password")
    
    if not student_email or not new_password:
        return jsonify({"error": "Invalid request"}), 400
    
    students_df = load_students()
    students_df.loc[students_df["email"] == student_email, "default password"] = new_password
    students_df.to_excel(DB_FILE, index=False)
    
    return jsonify({"success": True, "message": "Password updated successfully"})

    

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))



session_file = "sessions.xlsx"

# Load students function
def load_students():
    return pd.read_excel("db.xlsx", dtype={"email": str, "default password": str, "status": str})

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()  # Normalize input email
        password = request.form['password'].strip()  # Remove spaces

        students_df = load_students()  # Reload latest data
        students_df['email'] = students_df['email'].str.strip().str.lower()  # Normalize emails

        student = students_df[students_df['email'] == email]

        if student.empty:
            return "Invalid email or password."

        # Ensure status is handled correctly
        status = student['status'].values[0].strip().lower()
   
        if status == 'inactive':
            
            return render_template("inactive_account.html")  # Alert for inactive account

        # Fix password comparison
        stored_password = str(student['default password'].values[0]).strip()
        if password != stored_password:
            return "Invalid email or password."

        # If user is already logged in
        if is_student_logged_in(email):
                        # Assign a new session
            session_id = str(uuid.uuid4())
            df_sessions = pd.read_excel(session_file)  # Reload session data
            new_session = pd.DataFrame([{'email': email, 'session_id': session_id}])
            df_sessions = pd.concat([df_sessions, new_session], ignore_index=True)
            df_sessions.to_excel(session_file, index=False)
            # Save session in Flask
            session['user'] = email
            session['session_id'] = session_id
            
            return render_template("logged_in_alert.html", email=email)

        # Clear any previous session
        logout_student(email)  # Ensure logout removes previous session from sessions.xlsx

        # Assign a new session
        session_id = str(uuid.uuid4())
        df_sessions = pd.read_excel(session_file)  # Reload session data
        new_session = pd.DataFrame([{'email': email, 'session_id': session_id}])
        df_sessions = pd.concat([df_sessions, new_session], ignore_index=True)
        df_sessions.to_excel(session_file, index=False)

        # Save session in Flask
        session['user'] = email
        session['session_id'] = session_id

        return redirect(url_for('student_dashboard'))

    return render_template('student_login.html')



# **🔄 API to Check Live Status**
@app.route('/check_status')
def check_status():
    if 'user' in session:
        students_df = load_students()  # Always reload data
        student = students_df[students_df['email'] == session['user']]

        if student.empty:
            return jsonify({"status": "logout"})

        status = student['status'].values[0].strip().lower()
        if status == 'inactive':
            logout_student(session['user'])
            session.clear()
            return jsonify({"status": "logout"})
        else:
            return jsonify({"status": "active"})

    return jsonify({"status": "logout"})

# Load class data
def loads_classes():
    return pd.read_excel("class.xlsx")

# Load student data
def loads_students():
    return pd.read_excel("db.xlsx")

@app.route('/student_dashboard')
def student_dashboard():
    if 'user' not in session:
        return redirect(url_for('student_login'))

    email = session['user'].strip().lower()  # Normalize session email
    students_df = loads_students()

    # Normalize emails in the DataFrame to avoid case mismatches
    students_df['email'] = students_df['email'].str.strip().str.lower()

    student = students_df[students_df['email'] == email]

    if student.empty:
        return "Student not found"

    papers_taken = student['papers taken'].values[0].split(",")
    available_classes_df = loads_classes()
    available_classes = available_classes_df[available_classes_df['Paper Number'].isin(papers_taken)]

    if available_classes.empty:
        return render_template('student_dashboard.html', student=student, message="No available classes for you.")

    class_table = available_classes[['Paper Number', 'Paper Name', 'Start Time']].copy()
    
    class_table['Join Zoom'] = class_table['Paper Number'].apply(
        lambda x: f'<a href="{available_classes_df[available_classes_df["Paper Number"] == x]["Zoom Link"].values[0]}" target="_blank" class="btn btn-primary text-white bg-blue-500 hover:bg-blue-700 rounded-md px-4 py-2">Join Class</a>'
    )
    
    html_table = class_table.to_html(escape=False, index=False, classes="table table-responsive table-striped")
    
    responsive_css = """
    <style>
    .table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    .table th, .table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    .table th {
        background-color: #f2f2f2;
    }
    @media (max-width: 768px) {
        .table {
            font-size: 13px;
            display: block;
            overflow-x: auto;
            white-space: nowrap;
        }
        .table th, .table td {
            padding: 10px;
        }
    }
    @media (max-width: 480px) {
        .table {
            font-size: 12px;
        }
        .table th, .table td {
            padding: 8px;
            display: block;
            width: 100%;
            text-align: center;
        }
    }
    </style>
    """
    
    return render_template('student_dashboard.html', student=student, classes=responsive_css + html_table)

@app.route('/logouts')
def logouts():
    if 'user' in session:
        email = session['user']
        logout_student(email)  # Remove the session from the sessions.xlsx file
        session.clear()  # Clear Flask session

    return redirect(url_for('student_login'))  # Redirect to login page


db_file = "db.xlsx"  # Path to your Excel file

@app.route('/logout_all_sessions', methods=['POST'])
def logout_all_sessions():
    if 'user' not in session:  # Ensure the user is logged in
        return jsonify({"status": "error", "message": "User not logged in."}), 400

    email = session['user']  # Get logged-in user email

    # Load the database
    df = pd.read_excel(db_file)

    # Check if the user exists in the database
    if email not in df['email'].values:
        return jsonify({"status": "error", "message": "User not found."}), 404

    # Change status to "Inactive"
    df.loc[df['email'] == email, 'status'] = "Inactive"
    df.to_excel(db_file, index=False)

    # Wait for 10 seconds
    time.sleep(60)

    # Change status back to "Active"
    df.loc[df['email'] == email, 'status'] = "Active"
    df.to_excel(db_file, index=False)

    return jsonify({"status": "success", "message": "User status updated successfully."}), 200



# Load students function
def loaded_students():
    return pd.read_excel("db.xlsx", dtype={"email": str, "default password": str, "status": str})

# Save students function
def save_students(df):
    df.to_excel("db.xlsx", index=False)

@app.route('/edit_student', methods=['GET', 'POST'])
def edit_student():
    students_df = pd.read_excel("db.xlsx", dtype=str)

    if request.method == 'POST':
        email = request.form.get('email').strip().lower()

        # If searching for a student
        if 'search' in request.form:
            student = students_df[students_df['email'].str.strip().str.lower() == email]
            if student.empty:
                return render_template("edit_student.html", message="Student not found.")

            student_data = student.iloc[0].to_dict()
            return render_template("edit_student.html", student=student_data)

        # If updating student details
        elif 'update' in request.form:
            student_index = students_df[students_df['email'].str.strip().str.lower() == email].index

            if student_index.empty:
                return render_template("edit_student.html", message="Student not found.")

            # Update all fields dynamically (including email, default password, status, and student name)
            for column in ['student', 'email', 'default password', 'status']:
                students_df.at[student_index[0], column] = request.form.get(column, "").strip()

            students_df.to_excel("db.xlsx", index=False)
            return render_template("edit_student.html", message="Student updated successfully!")

    return render_template("edit_student.html")

if __name__ == '__main__':
    #app.run(host = "0.0.0.0", port=5550)
    serve(app, host="0.0.0.0", port=5550)
