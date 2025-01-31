import pandas as pd
import os

def process_excel(file_path):
    db_file = "db.xlsx"
    
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' not found.")

        # Read the input Excel file
        df = pd.read_excel(file_path)

        # Required columns
        required_columns = {"student", "email", "papers taken"}
        
        # Check if required columns exist
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Missing required columns. Ensure the file has: {required_columns}")

        # Add default columns
        df["default password"] = "123"
        df["status"] = "active"

        # Load or create the database file
        if os.path.exists(db_file):
            db_df = pd.read_excel(db_file)
        else:
            db_df = pd.DataFrame(columns=["student", "email", "papers taken", "default password", "status"])

        # Append new data
        db_df = pd.concat([db_df, df], ignore_index=True)

        # Save to db.xlsx
        db_df.to_excel(db_file, index=False)

        # Delete the input file
        os.remove(file_path)
        print(f"Processed data successfully saved to '{db_file}', and '{file_path}' has been deleted.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

DB_FILE = "db.xlsx"

def add_student_manually(student, email, papers_taken):
    """Add a single student to db.xlsx."""
    try:
        # Load existing db.xlsx or create an empty DataFrame
        if os.path.exists(DB_FILE):
            db_df = pd.read_excel(DB_FILE, dtype=str)
        else:
            db_df = pd.DataFrame(columns=["student", "email", "papers taken", "default password", "status"])

        # Create new student entry
        new_student = pd.DataFrame([{
            "student": student,
            "email": email,
            "papers taken": papers_taken,
            "default password": "123",
            "status": "active"
        }])

        # Append and save
        db_df = pd.concat([db_df, new_student], ignore_index=True)
        db_df.to_excel(DB_FILE, index=False, engine="openpyxl")

        return True, "Student added successfully!"
    except Exception as e:
        return False, str(e)


# Load student database from Excel

df_students = pd.read_excel("db.xlsx")  # Student records

# Session file (to track active users)
session_file = "sessions.xlsx"

# Ensure session file exists
try:
    df_sessions = pd.read_excel(session_file)
except FileNotFoundError:
    df_sessions = pd.DataFrame(columns=['email', 'session_id'])
    df_sessions.to_excel(session_file, index=False)

# Function to get student status
def get_student_status(email):
    student = df_students[df_students['email'] == email]
    if not student.empty:
        return student['status'].values[0]
    return None

def is_student_logged_in(email):
    df_sessions = pd.read_excel(session_file)
    return not df_sessions[df_sessions['email'] == email].empty

def logout_student(email):
    # Load session data from the session file
    df_sessions = pd.read_excel(session_file)

    # Filter out the session for the current user
    df_sessions = df_sessions[df_sessions['email'] != email]

    # Save the updated session data back to the Excel file
    df_sessions.to_excel(session_file, index=False)
