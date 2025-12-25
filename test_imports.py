
try:
    from backend.core.ghostbrain_autogen import GhostBrain_AI_Assistant, safe_init_rag
    from backend.core.tools import execute_step_by_step_streaming
    print("✅ Circular Import Check Passed")
except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ Generic Error: {e}")
