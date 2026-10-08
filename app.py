from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import pymysql
from sqlalchemy import text  # ✅ Correct import
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()
pymysql.install_as_MySQLdb()

app = Flask(__name__)

# Database configuration comes from environment variables / .env (see .env.example).
# Special characters in the password are URL-encoded.
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD", ""))
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fr_attendance")
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Student Model
class Student(db.Model):
    __tablename__ = 'student'
    roll_no = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Hashed password
    department = db.Column(db.String(50), nullable=False)

# Home Route
@app.route('/')
def home():
    return "Welcome to the Flask App!"

# Route: Register a Student
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not all(key in data for key in ('roll_no', 'name', 'password', 'department')):
        return jsonify({"error": "Missing required fields"}), 400
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_student = Student(roll_no=data['roll_no'], name=data['name'], password=hashed_password, department=data['department'])
    db.session.add(new_student)
    db.session.commit()
    return jsonify({"message": "Student registered successfully"}), 201

# Route: Student Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    student = Student.query.filter_by(roll_no=data['roll_no']).first()
    if student and bcrypt.check_password_hash(student.password, data['password']):
        access_token = create_access_token(identity=student.roll_no)
        return jsonify({"access_token": access_token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

# Route: Get Student Details (Protected)
@app.route('/student', methods=['GET'])
@jwt_required()
def get_student():
    roll_no = get_jwt_identity()
    student = Student.query.filter_by(roll_no=roll_no).first()
    if student:
        return jsonify({"roll_no": student.roll_no, "name": student.name, "department": student.department}), 200
    return jsonify({"error": "Student not found"}), 404

# Ensure database connection and table creation
with app.app_context():
    try:
        db.session.execute(text('SELECT 1'))  # ✅ Corrected import
        print("✅ Database connected successfully!")
        db.create_all()  # ✅ Ensure tables are created
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == '__main__':
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
