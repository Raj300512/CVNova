"""
Vercel serverless entry point for CVNova.
Vercel is WSGI-compatible — yeh file app.py ka app object import karti hai.
"""
import sys
import os

# Project root ko path mein add karo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects a WSGI callable named 'app' or 'handler'
# app already is the Flask WSGI app — no changes needed
