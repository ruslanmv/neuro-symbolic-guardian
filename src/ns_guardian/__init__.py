"""Neuro-Symbolic Guardian (NS-Guardian).

A lightweight verification layer that uses symbolic constraint solving (Z3) to
validate actions/outputs before they reach end users.
"""

from .guardian import LogicGuardian, VerificationResult

__all__ = ["LogicGuardian", "VerificationResult"]
