
import sys
import os
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("Sys Path:")
for p in sys.path:
    print(f" - {p}")

try:
    import langchain_community
    print(f"Langchain Community: {langchain_community.__file__}")
except ImportError as e:
    print(f"Error importing: {e}")
