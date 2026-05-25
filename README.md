# Task Management System

A full-stack, multi-user task management web application built with **Python (Google App Engine)** and **Firebase/Firestore**. Users can create collaborative task boards, invite teammates, assign and track tasks in real time, and manage board membership with role-based permissions.

---

## ✨ Features

- 🔐 **Firebase Authentication** — secure login/logout
- 📋 **Task Boards** — create, rename, and delete boards
- 👥 **Multi-user Collaboration** — invite users to boards; board owner controls membership
- ✅ **Task Management** — create, edit, delete, and complete tasks with due dates
- 👤 **Task Assignment** — assign tasks to any board member
- 🔴 **Unassigned Task Highlighting** — tasks turn red when their assigned user is removed
- 📊 **Live Counters** — active, completed, and total task counts per board
- 🛡️ **Role-based Permissions** — only board owners can rename, remove users, or delete boards

---

## 🛠️ Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3 (Google App Engine)        |
| Database  | Google Cloud Firestore (NoSQL)      |
| Auth      | Firebase Authentication             |
| Frontend  | HTML / CSS / JavaScript             |
| Hosting   | Google App Engine                   |

---

## 📁 Project Structure

```
project-root/
│
├── .git/                     # Local git repository
├── __pycache__/              # Python bytecode cache (auto-generated)
│
├── static/
│   ├── firebase-login.js     # Firebase authentication logic
│   └── styles.css            # Application stylesheet
│
├── templates/
│   ├── main.html             # Landing / Login page & dashboard
│   ├── board.html            # Individual task board view
│   └── edit_task.html        # Task edit form
│
├── main.py                   # Main application entry point (Python backend)
└── requirement.txt           # Python dependencies
```

---

## 🗄️ Firestore Data Model

The app uses Firestore's parent-child relationships for efficient, scalable querying.

```
users (collection)
└── {userId}
    ├── email: string
    └── displayName: string

taskboards (collection)
└── {boardId}
    ├── name: string
    ├── createdBy: userId
    ├── members: [userId, ...]
    └── tasks (subcollection)
        └── {taskId}
            ├── title: string
            ├── dueDate: timestamp
            ├── completed: boolean
            ├── completedAt: timestamp | null
            ├── assignedTo: userId | null
            └── isUnassigned: boolean
```

---

## 🚀 Getting Started

### Prerequisites

- [Python 3.x](https://www.python.org/)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- A [Firebase project](https://console.firebase.google.com/) with Firestore and Authentication enabled

### 1. Clone the repository

```bash
git clone https://github.com/engrarslan99/Collaborative-Task-Manager.git
cd Collaborative-Task-Manager
```

### 2. Configure Firebase

In your Firebase console, enable **Email/Password Authentication** and **Firestore**, then add your config:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

### 3. Install dependencies

```bash
pip install -r requirement.txt
```

### 4. Run locally

```bash
dev_appserver.py app.yaml
```

Visit `http://localhost:8080`

### 5. Deploy to Google App Engine

```bash
gcloud app deploy
```

---

## 🎓 Academic Context

| Detail | Info |
|--------|------|
| **Institution** | Griffith College Dublin |
| **Programme** | MSc Computer Science |
| **Module** | Cloud Platforms & Applications |
| **Year** | 2025 |

---

## 👨‍💻 Author

**Arslan Ashfaq**  
[LinkedIn](https://www.linkedin.com/in/arslanashfaq99) · [GitHub](https://github.com/engrarslan99)

