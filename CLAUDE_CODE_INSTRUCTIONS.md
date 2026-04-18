
# CLAUDE_CODE_INSTRUCTIONS.md
# Face Attendance System — Frontend Briefing for Claude Code

> **Read this entire file before writing a single line of code.**
> This document tells you everything about the backend, the API contract,
> and exactly what the frontend needs to do.

---

## 1. Project Overview

A **face-based attendance system** for college classrooms.

- Teacher opens a session → sets classroom location → students mark attendance
- Student must be **physically inside the classroom** (verified via GPS geofence)
- Student's **face must be recognised** (ArcFace deep learning model)
- A **liveness challenge** (blink / nod / smile) prevents photo spoofing
- All CV processing happens on the **backend** — frontend only captures webcam frames

---

## 2. Tech Stack (Frontend)

Use **React + TypeScript + Vite + Tailwind CSS**.

```
frontend/
  src/
    pages/
      LoginPage.tsx
      TeacherDashboard.tsx
      StudentDashboard.tsx
    components/
      WebcamCapture.tsx        ← reusable webcam component
      LivenessChallenge.tsx    ← shows challenge prompt + captures frames
      AttendanceList.tsx       ← real-time table for teacher
      SessionCard.tsx
      GeofenceMap.tsx          ← optional: show a map pin for classroom
    hooks/
      useAuth.ts
      useGeolocation.ts
      useWebcam.ts
    api/
      client.ts                ← axios instance with base URL + auth header
      auth.ts
      sessions.ts
      attendance.ts
      students.ts
    App.tsx
    main.tsx
```

---

## 3. Backend API Reference

**Base URL:** `http://localhost:8000`

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

### 3.1 Auth

#### POST `/api/auth/login`
**Body:**
```json
{ "email": "teacher@college.edu", "password": "teacher123" }
```
**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": "teacher-001",
  "name": "Prof. Sharma",
  "role": "teacher",          // "teacher" | "student"
  "roll_number": null,
  "face_enrolled": false
}
```

---

### 3.2 Sessions (Teacher only)

#### POST `/api/sessions/create`
```json
{
  "course_name": "Computer Vision (CS401)",
  "classroom_lat": 26.9124,
  "classroom_lon": 75.7873,
  "room_radius_meters": 20,
  "duration_minutes": 30
}
```
**Response:** `SessionResponse` (see below)

#### GET `/api/sessions/active`
Returns list of active sessions. Students call this to find their session.
```json
[
  {
    "id": "A3F7B2",
    "teacher_id": "teacher-001",
    "course_name": "Computer Vision (CS401)",
    "status": "active",
    "classroom_lat": 26.9124,
    "classroom_lon": 75.7873,
    "room_radius_meters": 20,
    "created_at": "2024-09-01T09:00:00",
    "expires_at": "2024-09-01T09:30:00"
  }
]
```

#### POST `/api/sessions/{session_id}/close`
Closes the session. Teacher only. No body required.

#### GET `/api/sessions/{session_id}/attendance`
Returns the live attendance list for a session.
```json
[
  {
    "id": 1,
    "student_id": "student-001",
    "student_name": "Aarav Mehta",
    "roll_number": "CS2021001",
    "status": "present",               // see AttendanceStatus below
    "face_similarity_score": 0.73,
    "liveness_score": 0.82,
    "distance_from_class_meters": 8.4,
    "marked_at": "2024-09-01T09:05:00"
  }
]
```

**AttendanceStatus values:**
- `present` — ✅ verified and marked
- `rejected_location` — ❌ outside geofence
- `rejected_face` — ❌ face not recognised
- `rejected_liveness` — ❌ liveness check failed
- `rejected_no_face` — ❌ no face detected in frame

---

### 3.3 Attendance Marking (Student only)

#### GET `/api/attendance/challenge`
Get a random liveness challenge before marking attendance.
```json
{ "challenge": "blink" }   // "blink" | "nod" | "smile"
```

#### POST `/api/attendance/mark`
The main attendance endpoint. Send everything at once.
```json
{
  "session_id": "A3F7B2",
  "student_lat": 26.9125,
  "student_lon": 75.7874,
  "face_image_b64": "<base64 JPEG from webcam>",
  "liveness_frames_b64": ["<base64>", "<base64>", "<base64>", "<base64>", "<base64>"],
  "liveness_challenge_type": "blink"
}
```

**Response:**
```json
{
  "success": true,
  "status": "present",
  "message": "Attendance marked! Welcome, Aarav Mehta",
  "face_similarity_score": 0.73,
  "liveness_score": 0.81,
  "liveness_challenge_passed": true,
  "distance_meters": 8.4,
  "debug_image_b64": "<base64 annotated JPEG — show this in UI>"
}
```

---

### 3.4 Students / Enrollment

#### GET `/api/students/`
Returns student list. Teachers see all, students see only themselves.

#### POST `/api/students/enroll-face`
Student enrolls their face (one-time setup).
```json
{ "face_image_b64": "<base64 JPEG>" }
```
**Response:** `{ "success": true, "message": "Enrollment successful" }`

---

## 4. Dummy Accounts

| Role    | Email                   | Password    |
|---------|-------------------------|-------------|
| Teacher | teacher@college.edu     | teacher123  |
| Student | aarav@college.edu       | student123  |
| Student | priya@college.edu       | student123  |
| Student | rohan@college.edu       | student123  |
| Student | sneha@college.edu       | student123  |

---

## 5. UI/UX Requirements

### 5.1 General
- Clean, modern UI — think a college admin panel
- Dark sidebar + light content area OR full light theme — your choice
- Responsive — must work on mobile (students use phones)
- Use Tailwind CSS utility classes throughout
- Show loading spinners during API calls
- Toast notifications for success/error (use `react-hot-toast` or similar)

---

### 5.2 Login Page (`/login`)

Single page with two tabs or a role-selector:
- **Teacher Login** and **Student Login** use the same form
- After login, redirect:
  - Teacher → `/teacher`
  - Student → `/student`
- Store JWT in `localStorage` as `face_attendance_token`
- Store user info in React context / Zustand store

---

### 5.3 Teacher Dashboard (`/teacher`)

**Left sidebar:** Nav links — Sessions, Attendance History, Students

**Main area has 3 views:**

#### View 1: Create Session
Form with:
- Course name (text input)
- Room radius in metres (slider: 5m–100m, default 20m)
- **"Use My Location" button** — calls `navigator.geolocation.getCurrentPosition()` and fills lat/lon
- Show the captured coordinates as a small label: `📍 26.9124°N, 75.7873°E`
- Duration in minutes (select: 15 / 30 / 45 / 60 / No limit)
- **"Start Session" button** → POST `/api/sessions/create`
- On success: show the **Session ID** in a large badge (e.g. `A3F7B2`) that the teacher can share with students

#### View 2: Live Attendance (shown when a session is active)
- Show session info at top: course name, session ID, time remaining, radius
- **Attendance table** — auto-refresh every 5 seconds (poll GET `/api/sessions/{id}/attendance`)
- Table columns: Roll No | Name | Status | Similarity Score | Liveness | Distance | Time
- Status badges:
  - `present` → green badge ✅
  - `rejected_*` → red badge ❌ with reason
- Show count: `3 / 28 students present`
- **"Close Session" button** → POST `/api/sessions/{id}/close`

#### View 3: Students Tab
- List all students with their name, roll number, and face enrollment status
- Show a green "Enrolled" or red "Not Enrolled" chip

---

### 5.4 Student Dashboard (`/student`)

**Flow has 4 steps — show as a step indicator at the top:**

```
Step 1: Find Session  →  Step 2: Enroll Face  →  Step 3: Verify Location  →  Step 4: Face Scan
```

#### Step 1: Find Session
- Auto-call GET `/api/sessions/active` on load
- If sessions found: show session card(s) with course name + session ID
- Student taps a session to select it
- If not enrolled: show a banner "You need to enroll your face first" → jump to enrollment

#### Step 1b: Enroll Face (if `face_enrolled === false`)
- Show instructions: "Position your face in the oval, ensure good lighting"
- Show `<WebcamCapture />` component with an oval face guide overlay
- "Capture & Enroll" button → POST `/api/students/enroll-face`
- On success: show confirmation and proceed to Step 2

#### Step 2: Verify Location
- "Allow Location" button → `navigator.geolocation.getCurrentPosition()`
- Show a spinner while acquiring GPS
- If location obtained: show `📍 Location acquired (±Xm accuracy)`
- If denied: show error "Location access is required to mark attendance"
- Automatically advance to Step 3 when location is ready

#### Step 3: Face Scan + Liveness Challenge
This is the most important step. Sub-steps:

**3a. Get challenge**
- Call GET `/api/attendance/challenge` → receive e.g. `"blink"`
- Show instruction card:
  - **Blink** → "👁️ Please blink naturally when ready"
  - **Nod** → "↕️ Please slowly nod your head up and down"
  - **Smile** → "😊 Please give a natural smile"

**3b. Webcam capture**
- Show live webcam feed in a rounded square container
- Overlay an oval guide for face positioning
- Show a countdown or "Ready — performing [challenge]..." indicator
- Capture logic:
  1. Capture **1 main frame** (the high-quality recognition frame) → `face_image_b64`
  2. Capture **5 frames at 200ms intervals** during the challenge → `liveness_frames_b64`
  3. Use `canvas.toDataURL('image/jpeg', 0.85)` to get base64

**3c. Submit**
- Call POST `/api/attendance/mark` with all data
- Show loading spinner: "Verifying identity..."
- **On success (status: present):**
  - Green success screen with checkmark ✅
  - Show: "Welcome, [Name]!" + similarity score + liveness score
  - If `debug_image_b64` is returned, show the annotated image in a small preview box
- **On failure:**
  - Red error screen with ❌
  - Show the specific reason from `message`
  - "Try Again" button

---

## 6. WebcamCapture Component Spec

```tsx
// components/WebcamCapture.tsx
// Props:
interface WebcamCaptureProps {
  onCapture: (imageB64: string) => void;       // Called with single frame
  onFrameStream?: (frames: string[]) => void;  // Called with N frames for liveness
  frameCount?: number;                          // How many liveness frames to capture (default 5)
  frameIntervalMs?: number;                     // Interval between frames (default 200ms)
  showOvalGuide?: boolean;                      // Show face positioning oval
  autoCapture?: boolean;                        // Start capturing immediately
}
```

Implementation notes:
- Use `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })`
- Draw video to a hidden `<canvas>` to extract frames
- Show a **mirrored** video preview (users expect this from selfie cameras)
- The oval guide should be drawn as an SVG overlay on top of the video

---

## 7. Geolocation Hook Spec

```ts
// hooks/useGeolocation.ts
// Returns:
{
  location: { lat: number; lon: number; accuracy: number } | null;
  error: string | null;
  loading: boolean;
  requestLocation: () => void;
}
```

Call `navigator.geolocation.getCurrentPosition()` with:
```ts
{ enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
```

---

## 8. API Client Setup

```ts
// api/client.ts
import axios from 'axios';

const client = axios.create({ baseURL: 'http://localhost:8000' });

// Auto-attach JWT
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('face_attendance_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('face_attendance_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);
```

---

## 9. Routing Structure

```tsx
// App.tsx — use react-router-dom v6
<Routes>
  <Route path="/login"   element={<LoginPage />} />
  <Route path="/teacher" element={<ProtectedRoute role="teacher"><TeacherDashboard /></ProtectedRoute>} />
  <Route path="/student" element={<ProtectedRoute role="student"><StudentDashboard /></ProtectedRoute>} />
  <Route path="/"        element={<Navigate to="/login" />} />
</Routes>
```

`ProtectedRoute` checks localStorage for token + correct role, redirects to `/login` if missing.

---

## 10. Recommended npm Packages

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "react-router-dom": "^6",
    "axios": "^1.6",
    "react-hot-toast": "^2.4",
    "lucide-react": "^0.383.0",
    "clsx": "^2.1"
  },
  "devDependencies": {
    "typescript": "^5",
    "vite": "^5",
    "@vitejs/plugin-react": "^4",
    "tailwindcss": "^3",
    "autoprefixer": "^10",
    "postcss": "^8",
    "@types/react": "^18",
    "@types/react-dom": "^18"
  }
}
```

---

## 11. Environment Variables

Create `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

Use in code: `import.meta.env.VITE_API_BASE_URL`

---

## 12. Project Bootstrap Commands

Run these to scaffold the frontend:
```bash
cd face_attendance
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom axios react-hot-toast lucide-react clsx
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Then add to `tailwind.config.js`:
```js
content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"]
```

And add to `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## 13. CV Debug Image Display

When the backend returns `debug_image_b64`, display it like this:

```tsx
{result.debug_image_b64 && (
  <div className="mt-4">
    <p className="text-sm text-gray-500 mb-1">CV Pipeline Output</p>
    <img
      src={`data:image/jpeg;base64,${result.debug_image_b64}`}
      alt="CV verification debug"
      className="rounded-lg border border-gray-200 max-w-xs"
    />
  </div>
)}
```

This image shows:
- Detected face bounding box + landmarks
- Quality scores overlaid on the image
- Green banner = verified, Red banner = rejected with reason
- Makes the CV pipeline visible and impressive for the demo

---

## 14. Important Notes for Claude Code

1. **Do NOT implement any face recognition logic in the frontend.** All CV happens in the Python backend. The frontend only captures webcam frames and sends them as base64.

2. **The backend must be running** at `http://localhost:8000` before the frontend will work. Run `bash start.bash` from the project root first.

3. **Both dashboards run on the same React app** — routing is role-based, not separate apps.

4. **For demo/testing without a real classroom**, the teacher can just press "Use My Location" and the student (running on the same machine or same WiFi) will also be at essentially the same GPS coordinates, so the geofence will pass.

5. **Polling for live attendance** — use `setInterval` with `clearInterval` cleanup in `useEffect` to poll every 5 seconds on the teacher's attendance view.

6. **Face enrollment is required before marking attendance.** If `face_enrolled === false` in the login response, show the enrollment flow first.

7. **Session ID sharing** — in a real class, the teacher would display the 6-char session ID on a projector. In the demo, students can just see it in the UI since it's one machine.

---

## 15. File/Folder Summary

```
face_attendance/
├── start.bash                    ← Run this first (sets up venv + starts backend)
├── CLAUDE_CODE_INSTRUCTIONS.md  ← This file
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              ← FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py        ← Settings (thresholds, JWT secret, etc.)
│   │   │   ├── database.py      ← SQLite init + dummy data seed
│   │   │   ├── security.py      ← JWT + role-based auth dependencies
│   │   │   └── geofence.py      ← Haversine geofence validation
│   │   ├── cv/
│   │   │   ├── filters.py       ← CLAHE, bilateral, unsharp mask, gamma, LBP, FFT
│   │   │   ├── face_detection.py← RetinaFace → MediaPipe → Haar fallback
│   │   │   ├── liveness.py      ← Passive (texture/freq/gradient) + Active (EAR/nod/MAR)
│   │   │   ├── recognition.py   ← ArcFace embeddings + FAISS search + HOG fallback
│   │   │   └── pipeline.py      ← Orchestrator — chains all CV modules
│   │   ├── models/
│   │   │   ├── user.py          ← User, UserRole
│   │   │   └── session.py       ← AttendanceSession, AttendanceRecord
│   │   ├── schemas/
│   │   │   └── schemas.py       ← All Pydantic request/response models
│   │   └── api/
│   │       ├── auth.py          ← POST /api/auth/login
│   │       ├── sessions.py      ← Session CRUD
│   │       ├── attendance.py    ← POST /api/attendance/mark (main CV endpoint)
│   │       └── students.py      ← Enrollment
│   └── uploads/
│       └── faces/               ← Auto-created: embeddings/ and images/
└── frontend/                    ← YOU BUILD THIS
    └── (React + Vite + Tailwind)
```

---

*Happy coding. The backend is fully production-ready. Your job is to make it look great.*
