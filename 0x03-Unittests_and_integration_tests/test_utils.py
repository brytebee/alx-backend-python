#!/usr/bin/env python3
"""
Unit tests for the utils module access_nested_map function.
This module contains test cases to verify the correct behavior
of accessing nested dictionary structures using key paths.
"""

import unittest
from parameterized import parameterized
from utils import access_nested_map


class TestAccessNestedMap(unittest.TestCase):
    """
    Test cases for the access_nested_map function from utils module.
    This class contains parameterized tests to verify that the function
    correctly accesses values in nested dictionaries using key paths.
    """

    @parameterized.expand([
        ({"a": 1}, ("a",), 1),
        ({"a": {"b": 2}}, ("a",), {"b": 2}),
        ({"a": {"b": 2}}, ("a", "b"), 2),
    ])
    def test_access_nested_map(self, nested_map, path, expected):
        """Test that access_nested_map returns the expected result for given inputs."""
        self.assertEqual(access_nested_map(nested_map, path), expected)


if __name__ == '__main__':
    unittest.main()