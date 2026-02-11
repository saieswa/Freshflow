# FreshFlow - Step by Step Setup Guide

## Prerequisites
- Python 3.7 or higher installed
- MongoDB installed on your system
- Internet connection (for installing packages)

---

## Step-by-Step Instructions

### Step 1: Install Python (if not already installed)
1. Check if Python is installed:
   ```powershell
   python --version
   ```
2. If not installed, download from: https://www.python.org/downloads/
3. During installation, check "Add Python to PATH"

### Step 2: Install MongoDB
1. Download MongoDB Community Server from: https://www.mongodb.com/try/download/community
2. Install MongoDB following the installer
3. Start MongoDB service:
   - **Windows**: Open Services (Win+R → `services.msc`) → Find "MongoDB" → Start it
   - OR run in PowerShell as Administrator:
     ```powershell
     net start MongoDB
     ```

### Step 3: Navigate to Project Directory
```powershell
cd "C:\Users\P SAI ESWARI\OneDrive\Documents\Freshflow-main\Freshflow-main"
```

### Step 4: Create Virtual Environment (Recommended)
```powershell
python -m venv venv
```
Activate it:
```powershell
.\venv\Scripts\Activate.ps1
```
If you get an execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 5: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 6: Create Environment File (Optional but Recommended)
Create a file named `.env` in the project root with:
```
SECRET_KEY=your-secret-key-here-change-this-in-production
MONGO_URI=mongodb://localhost:27017/freshflow
```

**Note**: The app will work without this file (it uses defaults), but it's better to create one.

### Step 7: Run the Application
```powershell
python app.py
```

You should see:
```
Starting FreshFlow...
 * Running on http://127.0.0.1:5000
```

### Step 8: Access the Application
1. Open your web browser
2. Go to: `http://localhost:5000` or `http://127.0.0.1:5000`
3. You'll see the landing page

### Step 9: Login
- **Default Admin Credentials:**
  - Username: `admin`
  - Password: `admin123`

OR create a new account by clicking "Sign Up"

---

## Troubleshooting

### MongoDB Connection Error
If you see "MongoDB connection failed":
1. Check if MongoDB service is running:
   ```powershell
   net start MongoDB
   ```
2. Verify MongoDB is on default port (27017)

### Port Already in Use
If port 5000 is already in use:
- Close the application using port 5000, OR
- Edit `app.py` line 476 and change `port=5000` to another port (e.g., `port=5001`)

### Python Package Installation Issues
If `pip install` fails:
1. Upgrade pip:
   ```powershell
   python -m pip install --upgrade pip
   ```
2. Try installing packages one by one

### Import Errors
Make sure you're in the correct directory and virtual environment is activated (if using one).

---

## Quick Start (All Steps Combined)
```powershell
# Navigate to project
cd "C:\Users\P SAI ESWARI\OneDrive\Documents\Freshflow-main\Freshflow-main"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file (optional)
# Use a text editor to create .env with the content shown in Step 6

# Run the application
python app.py
```

---

## Stopping the Application
Press `Ctrl + C` in the terminal to stop the Flask server.

