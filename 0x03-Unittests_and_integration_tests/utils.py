# First, let's understand the utils.access_nested_map function
# This function likely takes a nested dictionary and a path (tuple of keys)
# and returns the value at that path

def access_nested_map(nested_map, path):
    """
    Access a nested map using a sequence of keys.
    
    Args:
        nested_map: A nested dictionary
        path: A tuple of keys representing the path to the desired value
        
    Returns:
        The value at the specified path in the nested map
    """
    result = nested_map
    for key in path:
        result = result[key]
    return result

# Let's test this function with the given examples:
print("Testing access_nested_map function:")

# Test 1: nested_map={"a": 1}, path=("a",)
test1 = access_nested_map({"a": 1}, ("a",))
print(f"Test 1 result: {test1}")  # Expected: 1

# Test 2: nested_map={"a": {"b": 2}}, path=("a",)
test2 = access_nested_map({"a": {"b": 2}}, ("a",))
print(f"Test 2 result: {test2}")  # Expected: {"b": 2}

# Test 3: nested_map={"a": {"b": 2}}, path=("a", "b")
test3 = access_nested_map({"a": {"b": 2}}, ("a", "b"))
print(f"Test 3 result: {test3}")  # Expected: 2

print("\nNow creating the unit test class:")

import unittest
from parameterized import parameterized

class TestAccessNestedMap(unittest.TestCase):
    
    @parameterized.expand([
        ({"a": 1}, ("a",), 1),
        ({"a": {"b": 2}}, ("a",), {"b": 2}),
        ({"a": {"b": 2}}, ("a", "b"), 2),
    ])
    def test_access_nested_map(self, nested_map, path, expected):
        """Test that access_nested_map returns the expected result."""
        self.assertEqual(access_nested_map(nested_map, path), expected)

# Example of how to run the tests
if __name__ == '__main__':
    unittest.main()