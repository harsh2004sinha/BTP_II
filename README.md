<div align="center">
  <h1>⚡ Intelligent Microgrid Energy Management System</h1>
  <p>A full-stack application featuring a Python/FastAPI backend for microgrid optimization and a Next.js frontend for intuitive energy management and monitoring.</p>
</div>

---

## 📋 Table of Contents
- [Prerequisites](#-prerequisites)
- [Project Structure](#-project-structure)
- [Backend Setup (Python FastAPI)](#-backend-setup-python-fastapi)
- [Frontend Setup (Next.js)](#-frontend-setup-nextjs)
- [Database Configuration](#-database-configuration)

---

## 🛠 Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Python 3.9+**
- **Node.js 18+** & **npm**
- **PostgreSQL** (or an online database URL like Neon, Supabase)

---

## 📂 Project Structure

```text
Energy_Management_System/
├── main.py              # FastAPI Application Entry Point
├── requirements.txt     # Python Dependencies
├── .env.sample          # Sample Environment Variables for Backend
├── app/                 # Backend Application Logic (Routers, DB, etc.)
├── core/                # Core Microgrid Optimization & AI Logic
└── frontend/            # Next.js Frontend Application
```

---

## ⚙️ Backend Setup (Python FastAPI)

The backend handles all the optimization algorithms, AI/ML features, and database management. 

### 1. Open Terminal in the Root Directory
Make sure your terminal is opened in the `Energy_Management_System` folder.

### 2. Create a Virtual Environment
It is highly recommended to isolate your Python dependencies.
```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment
**For Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```
*If you are using Command Prompt (cmd), use `.\venv\Scripts\activate.bat` instead.*

**For Mac/Linux:**
```bash
source venv/bin/activate
```

### 4. Upgrade pip
Ensure you have the latest version of pip before installing packages:
```powershell
python.exe -m pip install --upgrade pip
```

### 5. Install Dependencies
Install all the required Python libraries for the backend:
```powershell
pip install -r requirements.txt
```

### 6. Set Up Environment Variables
1. Create a copy of the `.env.sample` file and name it `.env`.
2. Open `.env` and fill in your database connection string and API keys (e.g., OpenWeather, NASA).

### 7. Run the Backend Server
Start the FastAPI development server:
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*The backend API will now be running at `http://localhost:8000`. You can access the interactive Swagger documentation at `http://localhost:8000/docs`.*

---

## 🎨 Frontend Setup (Next.js)

The frontend is a modern web application built with Next.js, React, and Tailwind CSS.

### 1. Open a New Terminal
Leave the backend server running and open a **new** terminal window.

### 2. Navigate to the Frontend Directory
```powershell
cd frontend
```

### 3. Install Node Modules
Install all the required JavaScript dependencies:
```powershell
npm install
```

### 4. Set Up Frontend Environment Variables
1. Ensure there is a `.env.local` file inside the `frontend` folder.
2. It should contain the API URL pointing to your backend:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

### 5. Run the Frontend Development Server
Start the Next.js application:
```powershell
npm run dev
```
*The frontend will now be running at `http://localhost:3000`. Open this link in your browser to view the application.*

---

## 🗄️ Database Configuration

This project uses SQLAlchemy and Alembic for database management. When the FastAPI server starts up, it will automatically create the necessary tables in your database using the connection string provided in your `.env` file under `DATABASE_URL`.

**Example Local Database URL:**
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/energy_db
```

Enjoy building and optimizing your microgrid system! 🚀
