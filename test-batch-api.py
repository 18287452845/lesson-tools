#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test batch API and get detailed error information
"""

import requests
import json

try:
    response = requests.get("http://127.0.0.1:8000/api/batch/tasks", timeout=10)

    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"\nResponse Body:")
    print(response.text)

    if response.status_code != 200:
        try:
            error_data = response.json()
            print(f"\nError Details:")
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            pass
except Exception as e:
    print(f"Error: {e}")
