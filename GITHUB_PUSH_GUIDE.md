# How to Push Your FreshFlow Project to GitHub

## Step-by-Step Guide

### Prerequisites
- Git installed on your computer
- GitHub account created
- GitHub repository created (optional - we'll create one)

---

## Method 1: Using Command Line (Recommended)

### Step 1: Navigate to Your Project Directory
```powershell
cd "C:\Users\P SAI ESWARI\OneDrive\Documents\Freshflow-main\Freshflow-main"
```

### Step 2: Initialize Git (if not already done)
```powershell
git init
```

### Step 3: Configure Git (if not already done)
```powershell
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### Step 4: Add All Files to Git
```powershell
git add .
```

### Step 5: Create Initial Commit
```powershell
git commit -m "Initial commit: FreshFlow inventory management system with CSV upload feature"
```

### Step 6: Create Repository on GitHub
1. Go to https://github.com
2. Click the **"+"** icon (top right) → **"New repository"**
3. Repository name: `FreshFlow` (or your preferred name)
4. Description: "Inventory Management System with CSV Upload"
5. Choose **Public** or **Private**
6. **DO NOT** initialize with README, .gitignore, or license (we already have files)
7. Click **"Create repository"**

### Step 7: Add GitHub Remote
Copy the repository URL from GitHub (e.g., `https://github.com/yourusername/FreshFlow.git`) and run:

```powershell
git remote add origin https://github.com/yourusername/FreshFlow.git
```

**Note:** Replace `yourusername` and `FreshFlow` with your actual GitHub username and repository name.

### Step 8: Push to GitHub
```powershell
git branch -M main
git push -u origin main
```

If prompted for credentials:
- **Username**: Your GitHub username
- **Password**: Use a **Personal Access Token** (not your GitHub password)
  - Generate token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
  - Give it `repo` permissions
  - Copy the token and use it as password

---

## Method 2: Using GitHub Desktop (Easier for Beginners)

1. Download GitHub Desktop from https://desktop.github.com/
2. Install and sign in with your GitHub account
3. Click **"File"** → **"Add Local Repository"**
4. Browse to: `C:\Users\P SAI ESWARI\OneDrive\Documents\Freshflow-main\Freshflow-main`
5. Click **"Publish repository"**
6. Choose repository name and visibility
7. Click **"Publish Repository"**

---

## Quick Command Reference

```powershell
# Navigate to project
cd "C:\Users\P SAI ESWARI\OneDrive\Documents\Freshflow-main\Freshflow-main"

# Initialize git (first time only)
git init

# Add all files
git add .

# Commit changes
git commit -m "Your commit message"

# Add remote (first time only - replace with your repo URL)
git remote add origin https://github.com/yourusername/FreshFlow.git

# Push to GitHub
git push -u origin main
```

---

## Future Updates

After making changes to your code:

```powershell
# Check what changed
git status

# Add changed files
git add .

# Commit changes
git commit -m "Added new feature: description here"

# Push to GitHub
git push
```

---

## Troubleshooting

### Error: "remote origin already exists"
```powershell
git remote remove origin
git remote add origin https://github.com/yourusername/FreshFlow.git
```

### Error: "failed to push some refs"
```powershell
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Error: Authentication failed
- Use Personal Access Token instead of password
- Generate token: https://github.com/settings/tokens

### Want to exclude more files?
Edit the `.gitignore` file in your project root.

---

## What Gets Pushed?

✅ **Included:**
- All Python files (.py)
- Templates (HTML files)
- Static files (CSS, JS)
- Documentation (MD files)
- Requirements.txt
- README.md

❌ **Excluded (via .gitignore):**
- venv/ folder (virtual environment)
- __pycache__/ folders
- .env files (environment variables)
- IDE settings
- OS-specific files

---

**Need Help?** Check GitHub documentation: https://docs.github.com/

