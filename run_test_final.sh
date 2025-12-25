#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
echo ">>> TESTING INTEL <<<"
python3 tests/test_intel.py
echo ">>> TESTING HIERARCHICAL VISION <<<"
python3 tests/test_hierarchical.py
