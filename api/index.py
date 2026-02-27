"""
Vercel Serverless Function entry point.
Wraps the FastAPI app so Vercel can serve it as a Python serverless function.
"""
import sys
import os

# Add the backend directory to the Python path so 'app' package can be found
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_dir)

# Set working directory to backend so relative paths (storage/) work
os.chdir(backend_dir)

# Load .env from backend directory
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

from app.main import app

# Vercel's Python runtime supports ASGI natively.
# The 'app' variable is automatically detected and used.
