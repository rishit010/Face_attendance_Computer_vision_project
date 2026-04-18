#  Face Attendance System (Computer Vision + Full Stack)

A **Face Recognition-based Attendance System** that automatically detects and marks attendance using computer vision, with a modern web interface for interaction.

This project combines **AI/ML + Web Development** to build a real-world, practical system.

---

##  Features

*  Real-time face detection using webcam
*  Face recognition using ML models
*  Automatic attendance marking
*  Login system with protected routes
*  Student Dashboard
*  Teacher Dashboard
*  Fast API-based backend + React frontend

---

##  Tech Stack

###  Frontend

* React (TypeScript)
* Tailwind CSS
* Axios

###  Backend

* Python
* FastAPI / Flask
* OpenCV
* Mediapipe / Face Recognition

---

##  Project Structure

```
face_attendance/
│
├── backend/
│   ├── venv/              # (ignored in repo)
│   ├── main.py            # Backend entry point
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── store/
│   │   └── api/
│   └── ...
│
├── start.bash
└── README.md
```

---

##  Setup Instructions

###  Clone Repository

```bash
git clone https://github.com/rishit010/Face_attendance_Computer_vision_project.git
cd Face_attendance_Computer_vision_project
```

---

###  Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

---

###  Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

###  Run Backend

```bash
cd backend
python main.py
```

---

##  How It Works

1. Webcam captures live video
2. Faces are detected using computer vision
3. Facial features are extracted and compared
4. If matched → attendance is recorded
5. Data is displayed on dashboards

---

## Future Improvements

*  Attendance analytics dashboard
*  Deployment (AWS / Vercel)
*  Mobile-friendly UI
*  Improved face recognition accuracy

---

##  Note

* `venv/` is excluded using `.gitignore`
* Install dependencies using `requirements.txt`
* Do not upload large files or environments

---

##  Author

**Rishit Thamman**
BTech CSE 

**Lavanya Sharma**
BTech CSE
---
