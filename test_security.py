#!/usr/bin/env python3
"""Test Security V2.0 - Enumeration + Pipeline Awareness"""

from backend.config.security import (
    check_protected_path_access,
    full_security_check,
    CURRENT_SECURITY_LEVEL
)

print(f"=== Security Level: {CURRENT_SECURITY_LEVEL.value.upper()} ===\n")

# Test cases che DEVONO essere bloccati
MUST_BLOCK = [
    # File reading
    ("cat /etc/redline/secret.conf", "READ"),
    ("head /etc/shadow", "READ"),
    ("grep password /etc/passwd", "READ"),
    ("sed -n '1p' /etc/redline/secret.conf", "READ"),
    ("awk '1' /etc/sudoers", "READ"),
    
    # Enumeration
    ("ls /etc/redline/", "ENUM"),
    ("ls -la /etc/", "ENUM"),
    ("find /etc -name '*.conf'", "ENUM"),
    ("stat /etc/redline/secret.conf", "ENUM"),
    ("file /etc/passwd", "ENUM"),
    ("readlink -f /etc/redline/secret.conf", "ENUM"),
    
    # Pipeline attacks
    ("cat /etc/redline/secret.conf | head", "PIPELINE"),
    ("ls /etc/redline/ | grep secret", "PIPELINE"),
    ("grep token /etc/redline/secret.conf | base64", "PIPELINE"),
    
    # Path traversal
    ("cat /etc/redline/../redline/secret.conf", "TRAVERSAL"),
    ("ls /etc/../etc/redline/", "TRAVERSAL"),
]

# Test cases che DEVONO passare
MUST_ALLOW = [
    ("ls /home/ghostFrame/", "ALLOWED HOME"),
    ("cat /tmp/test.txt", "ALLOWED TMP"),
    ("find /home -name '*.py'", "ALLOWED FIND"),
    ("echo hello world", "NOT SENSITIVE"),
    ("nmap -sT 192.168.1.1", "NETWORK CMD"),
    ("pwd && whoami", "SAFE PIPELINE"),
]

print("=== MUST BE BLOCKED ===")
blocked_pass = 0
blocked_fail = 0
for cmd, test_type in MUST_BLOCK:
    allowed, reason = check_protected_path_access(cmd)
    if allowed:
        print(f"❌ FAIL [{test_type}]: {cmd[:50]}")
        print(f"   Expected BLOCK, got ALLOW: {reason}")
        blocked_fail += 1
    else:
        print(f"✅ BLOCKED [{test_type}]: {cmd[:40]}...")
        blocked_pass += 1

print(f"\n=== MUST BE ALLOWED ===")
allow_pass = 0
allow_fail = 0
for cmd, test_type in MUST_ALLOW:
    allowed, reason = check_protected_path_access(cmd)
    if not allowed:
        print(f"❌ FAIL [{test_type}]: {cmd[:50]}")
        print(f"   Expected ALLOW, got BLOCK: {reason}")
        allow_fail += 1
    else:
        print(f"✅ ALLOWED [{test_type}]: {cmd[:40]}...")
        allow_pass += 1

print(f"\n=== SUMMARY ===")
print(f"Block tests: {blocked_pass}/{len(MUST_BLOCK)} passed")
print(f"Allow tests: {allow_pass}/{len(MUST_ALLOW)} passed")
total_pass = blocked_pass + allow_pass
total = len(MUST_BLOCK) + len(MUST_ALLOW)
print(f"Overall: {total_pass}/{total} ({100*total_pass//total}%)")
