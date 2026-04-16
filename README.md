````markdown
<h1 align="center">👤 Face Recognition Attendance System</h1>
<p align="center">
  <img src="https://img.shields.io/badge/DBMS-PROJECT-blue.svg?style=for-the-badge">
  <img src="https://img.shields.io/github/stars/chetangadhiya5062/Fork_dbms_project_face_attendance?style=for-the-badge">
  <img src="https://img.shields.io/github/forks/chetangadhiya5062/Fork_dbms_project_face_attendance?style=for-the-badge">
</p>

<p align="center">📸 A smart Face Recognition system to automate student attendance using Python, OpenCV, Tkinter, and MySQL. ✨</p>

---

## ✨ Features

- 🎥 Real-time face detection and recognition with OpenCV
- 📝 Auto logs attendance with name, date & time
- 👤 Student registration with photo capture
- 📚 Trains face data using LBPH algorithm
- 📊 Attendance records saved in MySQL
- 🖼️ GUI powered by Tkinter
- 📤 Export attendance to CSV format

---

## 🛠️ Tech Stack

| Tool        | Purpose                          |
|-------------|----------------------------------|
| `Python`    | Core programming language        |
| `OpenCV`    | Image processing & face detection|
| `Tkinter`   | Graphical User Interface (GUI)   |
| `MySQL`     | Backend database                 |
| `PIL`       | Image handling                   |
| `CSV`       | Export reports                   |

---

## 📷 UI Preview & Demo

| 👨‍🎓 Register Student | 📸 Face Detection | 🧾 Attendance |
|----------------------|------------------|---------------|
| ![register](images/register.png) | ![detect](images/detect.png) | ![attendance](images/attendance.png) |

> *(Replace above with your own screenshots in a `images/` folder)*

---

## 🚀 Getting Started

### 🔁 Clone the Repository

```bash
git clone https://github.com/chetangadhiya5062/Fork_dbms_project_face_attendance.git
cd Fork_dbms_project_face_attendance
````

### 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

> If `requirements.txt` not found:

```bash
pip install opencv-python pillow mysql-connector-python
```

### 🛠️ Set Up MySQL

1. Login to MySQL:

```bash
mysql -u root -p
```

2. Create Database:

```sql
CREATE DATABASE face_recognition;
```

3. Update credentials in `database.py` as needed.

---

### ▶️ Run the App

```bash
python main.py
```

---

## 🧠 Modules Overview

| File                  | Purpose                                 |
| --------------------- | --------------------------------------- |
| `main.py`             | Main GUI launcher                       |
| `student.py`          | Capture & register student faces        |
| `train.py`            | Train model using LBPH face recognizer  |
| `face_recognition.py` | Real-time face recognition & attendance |
| `attendance.py`       | Export attendance to CSV                |
| `database.py`         | Connects to MySQL                       |

---

## 🗂️ Folder Structure

```
.
├── attendance/         # CSV logs
├── dataset/            # Captured face images
├── trainer/            # Trained model
├── icons/              # App icons
├── images/             # Screenshots for README
├── main.py
├── student.py
├── face_recognition.py
├── train.py
└── database.py
```

---

## 🔮 Future Improvements

* [ ] Add Face Mask Detection
* [ ] Improve UI design with custom themes
* [ ] Implement Email/SMS alerts for absentee
* [ ] Dockerize for easy deployment
* [ ] Enable admin login system

---


## 🤝 Contributors

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/chetangadhiya5062">
        <img src="https://github.com/chetangadhiya5062.png" width="100px;" alt=""/>
        <br />
        <sub><b>Chetan Gadhiya</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/VedeshP">
        <img src="https://github.com/VedeshP.png" width="100px;" alt=""/>
        <br />
        <sub><b>Vedesh Pandya</b></sub>
      </a>
    </td>
  </tr>
</table>

---
---

## 📜 License

Licensed under the [MIT License](LICENSE).

---

## 🌟 Show Some Love

If you like this project, consider giving it a ⭐️
It helps the repository grow and shows appreciation! 🙌

<p align="center">
  <img src="https://forthebadge.com/images/badges/made-with-python.svg">
</p>
```
