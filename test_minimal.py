#!/usr/bin/env python
"""Minimal test to debug pytest hang."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("1. Importing pytest...")
import pytest

print("2. Importing app...")
from app.main import app

print("3. Importing TestClient...")
from fastapi.testclient import TestClient

print("4. Creating test client...")
client = TestClient(app)

print("5. Making request...")
response = client.get("/health")

print(f"6. Response: {response.status_code} - {response.json()}")

print("✅ All steps passed!")
