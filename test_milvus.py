#!/usr/bin/env python3
"""Test Milvus Lite connection."""

import os
from pathlib import Path

from pymilvus import MilvusClient

client = MilvusClient("./milvus_demo.db")

print("collections:", client.list_collections())

# Test 1: Use relative path
print("=== Test 1: Relative path ===")
try:
    from pymilvus import MilvusClient
    db_path = "./milvus_data/test.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    client = MilvusClient(uri=db_path)
    print(f"✅ Success with relative path: {db_path}")
    
    # Test collection
    if client.has_collection("test"):
        client.drop_collection("test")
    client.create_collection("test", dimension=128)
    print("✅ Collection created")
    
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Use absolute path
print("\n=== Test 2: Absolute path ===")
try:
    from pymilvus import MilvusClient
    db_path = os.path.abspath("./milvus_data/test2.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    client = MilvusClient(uri=db_path)
    print(f"✅ Success with absolute path: {db_path}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 3: Check pymilvus version
print("\n=== Test 3: Version check ===")
try:
    import pymilvus
    print(f"pymilvus version: {pymilvus.__version__}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 4: Check if milvus-lite is available
print("\n=== Test 4: milvus-lite check ===")
try:
    import milvus_lite
    print(f"milvus-lite version: {milvus_lite.__version__}")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n=== All tests completed ===")
