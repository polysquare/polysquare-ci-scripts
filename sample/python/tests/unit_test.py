# /tests/unit_test.py
#
# Test cases for example project.
#
# See LICENCE.md for Copyright information
"""Test cases for usage of example."""

from testtools import TestCase


class TestUnit(TestCase):

    """Unit tests."""

    def test_simple_case(self):
        """Simple test."""
        self.assertEqual(1, 1)
