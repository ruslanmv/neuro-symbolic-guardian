#!/usr/bin/env python3
"""
Test script for verifying the Guardian API is working correctly.
This script demonstrates how to use the REST API from Python.
"""

import requests

BASE = "http://localhost:8000"

def verify(text: str, facts: dict) -> dict:
    """Verify an action using the Guardian API."""
    r = requests.post(
        f"{BASE}/api/verify",
        json={"text": text, "facts": facts},
        timeout=10
    )
    r.raise_for_status()
    return r.json()

def main():
    print("Testing Neuro-Symbolic Guardian API\n")
    print("=" * 60)

    # Test 1: Inventory violation
    print("\n1. Testing inventory constraint violation:")
    print("   Action: 'consume 10 items from inventory'")
    print("   Facts: {inventory: 5}")
    result = verify("consume 10 items from inventory", {"inventory": 5})
    print(f"   Decision: {result['decision']}")
    print(f"   Message: {result['human_message']}")
    print(f"   Reason codes: {result['reason_codes']}")

    # Test 2: Valid action
    print("\n2. Testing valid action:")
    print("   Action: 'consume 2 items from inventory'")
    print("   Facts: {inventory: 5}")
    result = verify("consume 2 items from inventory", {"inventory": 5})
    print(f"   Decision: {result['decision']}")
    print(f"   Message: {result['human_message']}")

    # Test 3: Secret detection
    print("\n3. Testing secret detection:")
    print("   Action: 'Use API key sk-1234567890abcdefghijklmnop'")
    result = verify("Use API key sk-1234567890abcdefghijklmnop", {})
    print(f"   Decision: {result['decision']}")
    print(f"   Message: {result['human_message']}")
    print(f"   Reason codes: {result['reason_codes']}")

    # Test 4: Banking-style example
    print("\n4. Testing banking transfer (simulated):")
    print("   Action: 'transfer 10000 from my account'")
    print("   Facts: {balance: 3200}")
    result = verify("transfer 10000 from my account", {"balance": 3200})
    print(f"   Decision: {result['decision']}")
    print(f"   Latency: {result['telemetry']['latency_ms']}ms")

    print("\n" + "=" * 60)
    print("All tests completed successfully!")

if __name__ == "__main__":
    main()
