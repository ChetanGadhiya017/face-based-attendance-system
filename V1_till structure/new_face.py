import cv2
import face_recognition
import numpy as np
from sqlalchemy import create_engine, text
from datetime import date, timedelta
import sys
import os
# No argparse needed if course_id is hardcoded
# import argparse # For command-line arguments

# face rec lib in python 3.12.4 - global interpreter

# --- Database Configuration ---
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Set ATTENDANCE_DATABASE_URL in your environment / .env (see .env.example)
DATABASE_URL = os.getenv("ATTENDANCE_DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/attendance_v1")
# Reminder: Use secure credential management in production!

# --- Table and Column Names (Adjust if needed) ---
STUDENT_TABLE = "STUDENT"
STUDENT_ID_COL = "ID"
STUDENT_NAME_COL = "NAME"
STUDENT_IMAGE_PATH_COL = "IMAGE_PATH"

ATTENDANCE_TABLE = "ATTENDANCE"
ATTENDANCE_STUDENT_ID_COL = "STUDENT_ID"
ATTENDANCE_COURSE_ID_COL = "COURSE_ID"
ATTENDANCE_DATE_COL = "DATE"
ATTENDANCE_STATUS_COL = "STATUS"

# --- Enrollment Table Name ---
ENROLLMENT_TABLE = "ENROLLMENT" # Added for clarity

# --- Global Variables ---
known_face_encodings = []
known_student_ids = []
known_student_names = {} # Dictionary to map ID to Name for display

# --- Function to Load Known Students from Database ---
def load_known_students_from_db(engine):
    """Loads student data (ID, Name, Image Path) and generates face encodings."""
    global known_face_encodings, known_student_ids, known_student_names
    known_face_encodings = []
    known_student_ids = []
    known_student_names = {}

    print("Connecting to database...")
    try:
        with engine.connect() as connection:
            print("Fetching student data for face recognition...")
            # Select students who have an image path
            query = text(f"""
                SELECT {STUDENT_ID_COL}, {STUDENT_NAME_COL}, {STUDENT_IMAGE_PATH_COL}
                FROM {STUDENT_TABLE}
                WHERE {STUDENT_IMAGE_PATH_COL} IS NOT NULL AND {STUDENT_IMAGE_PATH_COL} != ''
            """)
            result = connection.execute(query)
            students = result.fetchall()

            if not students:
                print(f"Warning: No students with image paths found in '{STUDENT_TABLE}'.")
                return False

            print(f"Found {len(students)} students with images. Generating encodings...")
            count = 0
            skipped = 0
            for student_id, name, image_path in students:
                # Use double backslashes or forward slashes for paths in Python strings
                # Correcting potential path issues if read directly from DB might be needed
                # image_path = image_path.replace('\\', '/') # Example correction
                
                # but here i have added '/' only in the database while i was writing the queries to add the path

                
                if not image_path or not os.path.exists(image_path):
                    print(f"Warning: Image path '{image_path}' for student {student_id} ({name}) not found or is empty. Skipping.")
                    skipped += 1
                    continue

                try:
                    print(f"Processing {student_id}: {name} ({image_path})")
                    student_image = face_recognition.load_image_file(image_path)
                    # Important: Assume only ONE face per student image for encoding
                    face_encodings = face_recognition.face_encodings(student_image)

                    if len(face_encodings) > 0:
                        # Use the first encoding found
                        encoding = face_encodings[0]
                        known_face_encodings.append(encoding)
                        known_student_ids.append(student_id)
                        known_student_names[student_id] = name # Store name mapped by ID
                        count += 1
                    else:
                        print(f"Warning: No face detected in image for student {student_id} ({name}) at '{image_path}'. Skipping.")
                        skipped += 1

                except Exception as e:
                    print(f"Error processing image for student {student_id} ({name}) at '{image_path}': {e}")
                    skipped += 1

            print("-" * 30)
            print(f"Successfully loaded and encoded {count} student faces.")
            if skipped > 0:
                print(f"Skipped {skipped} students due to missing images or detection issues.")
            print("-" * 30)
            return count > 0 # Return True if at least one face was loaded

    except Exception as e:
        print(f"FATAL ERROR: Could not connect to or fetch from database: {e}")
        print("Please check DB connection, table/column names, and permissions.")
        return False

# --- Function to Mark Attendance in Database ---
def mark_attendance(engine, student_id, course_id, attendance_date):
    """Marks a student as 'Present' for a specific course and date."""
    status = 'Present'
    try:
        with engine.connect() as connection:
            # Use INSERT IGNORE (MySQL specific) to avoid errors if attendance for this
            # student/course/date already exists. Alternatively, check first.
            # Using parameterized query for safety
            query = text(f"""
                INSERT IGNORE INTO {ATTENDANCE_TABLE}
                ({ATTENDANCE_STUDENT_ID_COL}, {ATTENDANCE_COURSE_ID_COL}, {ATTENDANCE_DATE_COL}, {ATTENDANCE_STATUS_COL})
                VALUES (:student_id, :course_id, :att_date, :status)
            """)
            connection.execute(query, {
                "student_id": student_id,
                "course_id": course_id,
                "att_date": attendance_date,
                "status": status
            })
            connection.commit()
            return True # Indicate success or that the record potentially already existed

    except Exception as e:
        print(f"ERROR: Failed to mark attendance for {student_id} in {course_id}: {e}")
        return False

# --- Main Application Logic ---
if __name__ == "__main__":

    # --- Set the Course ID directly ---
    # current_course_id = "20CP206T"
    # current_course_id = "20CP207P"
    # current_course_id = "20CP207T"
    # current_course_id = "20CP208P"
    # current_course_id = "20CP208T"
    # current_course_id = "20CP209P"
    # current_course_id = "20CP209T"
    current_course_id = "20CP210P"
    print(f"Starting attendance system for Course ID: {current_course_id}")

    # --- Database Engine ---
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        sys.exit(f"Failed to create database engine: {e}")

    # --- Load Known Faces ---
    if not load_known_students_from_db(engine):
        print("Warning: No known student faces loaded. Only 'Unknown' will be detected.")

    # --- Webcam Initialization ---
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("Error: Could not open webcam.")
    print("Webcam opened successfully.")

    # --- Get Attendance Date ---
    # today_date = date.today()
    # today_date = date.today() - timedelta(days=1) # Using yesterday's date as per your code
    today_date = date.today()
    print(f"Attendance Date: {today_date}")

    # --- Keep track of students marked present in this session ---
    students_marked_today_session = set()

    # --- Processing Loop ---
    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Warning: Failed to grab frame from webcam.")
                continue # Try next frame

            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            # Convert BGR (OpenCV) to RGB (face_recognition)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Find face locations and encodings
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            current_frame_face_names = []

            # Process detected faces only if known faces are loaded
            if known_face_encodings:
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.55)
                    student_id = "Unknown"
                    display_name = "Unknown"

                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            student_id = known_student_ids[best_match_index]
                            display_name = known_student_names.get(student_id, "Known (Name N/A)")

                            # --- V V V --- ADDED ENROLLMENT CHECK --- V V V ---
                            if student_id != "Unknown": # Only check enrollment if recognized
                                is_enrolled = False # Assume not enrolled initially
                                try:
                                    with engine.connect() as connection:
                                        # Prepare the check query using text() for parameters
                                        check_query = text(f"""
                                            SELECT COUNT(*) FROM {ENROLLMENT_TABLE}
                                            WHERE {ATTENDANCE_STUDENT_ID_COL} = :sid AND {ATTENDANCE_COURSE_ID_COL} = :cid
                                        """)
                                        # Execute with current student_id and course_id
                                        result = connection.execute(check_query, {"sid": student_id, "cid": current_course_id})
                                        enrollment_count = result.scalar() # Gets the count

                                        if enrollment_count is not None and enrollment_count > 0:
                                            is_enrolled = True

                                except Exception as e:
                                    print(f"DB Error checking enrollment for {student_id} in {current_course_id}: {e}")
                                    # Decide how to handle DB error, e.g., skip marking attendance for this frame

                                # --- Mark Attendance ONLY if Recognized AND Enrolled ---
                                if is_enrolled:
                                    # Now, proceed with the logic to mark attendance if not already marked in session
                                    if student_id not in students_marked_today_session:
                                        print(f"Recognized & Enrolled: {display_name} ({student_id}). Attempting to mark attendance...")
                                        if mark_attendance(engine, student_id, current_course_id, today_date):
                                            print(f"-> Attendance successfully recorded for {display_name} ({student_id})")
                                            students_marked_today_session.add(student_id)
                                        else:
                                            print(f"-> Failed to record attendance for {display_name} ({student_id})")
                                    # else: # Optional: print if already marked in this session
                                    #     pass # print(f"Already marked {display_name} in this session.")
                                else:
                                    # Student recognized but not enrolled in this specific course
                                    print(f"Recognized: {display_name} ({student_id}) but NOT ENROLLED in course {current_course_id}. Attendance not marked.")
                            # --- ^ ^ ^ --- END OF ENROLLMENT CHECK --- ^ ^ ^ ---


                    current_frame_face_names.append(display_name) # Add name for display

            else: # If no known faces loaded, all are Unknown
                for _ in face_locations:
                    current_frame_face_names.append("Unknown")


            # --- Display Results on the Original Frame ---
            for (top, right, bottom, left), name in zip(face_locations, current_frame_face_names):
                # Scale back up face locations
                top *= 2
                right *= 2
                bottom *= 2
                left *= 2

                # Draw rectangle and label
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.7, (255, 255, 255), 1)


            # Display the resulting image
            cv2.imshow(f'Attendance System - Course: {current_course_id} | Date: {today_date}', frame)

            # Exit loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Exiting program...")
                break

    except KeyboardInterrupt:
        print("Program interrupted by user (Ctrl+C).")
    except Exception as e:
        print(f"An unexpected error occurred during the main loop: {e}")
    finally:
        # Release resources
        if 'cap' in locals() and cap.isOpened():
            cap.release()
            print("Webcam released.")
        cv2.destroyAllWindows()
        print("OpenCV windows closed.")
        print(f"Students marked present during this session: {len(students_marked_today_session)}")
        print(sorted(list(students_marked_today_session))) # Print the list of IDs marked, sorted