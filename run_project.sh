#!/bin/bash
# -------------------------------------------------------------
# Project Setup & Execution Script (POSIX Compatible)
# -------------------------------------------------------------

echo "--- 🧹 STEP 1: Checking Dependencies ---"

# Check for Python and pip
if ! command -v python3 &> /dev/null
then
    echo "❌ Error: python3 command not found. Please install Python 3."
    exit 1
fi

# Check for virtual environment (best practice)
if [ ! -d ".venv" ]; then
    echo "📂 Creating and activating virtual environment (.venv)..."
    python3 -m venv .venv
    source .venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to activate virtual environment."
        exit 1
    fi
fi

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install Python dependencies. Check your requirements.txt."
        deactivate # Attempt to clean up environment
        exit 1
    fi
else
    echo "⚠️ Warning: requirements.txt not found. Skipping dependency installation."
fi

echo -e "\n=========================================="
echo "✅ Setup Complete. Proceeding to execution."
echo "=========================================="

# -------------------------------------------------------------
# Execution Block
# -------------------------------------------------------------
# Replace 'your_main_script.py' with the actual entry point for your application
# For testing, I'll assume a main file exists.
ENTRY_POINT="./your_main_script.py"

if [ -f "$ENTRY_POINT" ]; then
    echo -e "\n🚀 Starting application execution using: $ENTRY_POINT"
    # Execute the main script
    python3 "$ENTRY_POINT"
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "\n=================================================="
        echo "🎉 SUCCESS: Application ran successfully (Exit Code 0)."
        echo "=================================================="
    else
        echo -e "\n=================================================="
        echo "🚨 FAILURE: Application exited with Code $EXIT_CODE. Please check the logs above."
        echo "=================================================="
    fi

    # Deactivate environment upon completion
    deactivate
    exit $EXIT_CODE
else
    echo -e "\n=================================================="
    echo "🚨 FATAL ERROR: The entry point file '$ENTRY_POINT' was not found."
    echo "Please change the 'ENTRY_POINT' variable in the script to point to your main application file."
    echo "=================================================="
    deactivate
    exit 1
fi