#!/usr/bin/env python
"""
Test script to verify kubernetes package import
"""

import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print("-" * 50)

try:
    import kubernetes
    print(f"✅ kubernetes imported successfully!")
    print(f"   Version: {kubernetes.__version__}")
    
    # Test importing specific components
    from kubernetes import client, config
    from kubernetes.client import ApiException
    print("✅ All kubernetes imports working correctly!")
    
except ImportError as e:
    print(f"❌ Failed to import kubernetes: {e}")
    sys.exit(1)

print("-" * 50)
print("All tests passed! The kubernetes package is properly installed.")
