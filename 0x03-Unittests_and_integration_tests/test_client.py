#!/usr/bin/env python3
"""
Unit tests for the client module GithubOrgClient class.
This module contains test cases to verify the correct behavior
of the GithubOrgClient class methods and properties.
"""

import sys
import os
import unittest
from unittest.mock import patch, PropertyMock, Mock
from parameterized import parameterized, parameterized_class

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import GithubOrgClient  # noqa: E402
from fixtures import TEST_PAYLOAD  # noqa: E402


class TestGithubOrgClient(unittest.TestCase):
    """
    Test cases for the GithubOrgClient class from client module.
    This class contains tests to verify that the GithubOrgClient
    correctly interacts with the GitHub API without making actual HTTP calls.
    """

    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('client.get_json')
    def test_org(self, org_name, mock_get_json):
        """Test that GithubOrgClient.org returns correct value and calls
        get_json once."""
        # Set up mock return value
        expected_result = {"name": org_name, "type": "Organization"}
        mock_get_json.return_value = expected_result

        # Create client instance and call org property
        client = GithubOrgClient(org_name)
        result = client.org

        # Verify get_json was called once with expected URL
        expected_url = f"https://api.github.com/orgs/{org_name}"
        mock_get_json.assert_called_once_with(expected_url)

        # Verify the result matches the expected value
        self.assertEqual(result, expected_result)

    def test_public_repos_url(self):
        """Test that _public_repos_url returns expected URL based on mocked
        org payload."""
        with patch('client.GithubOrgClient.org',
                   new_callable=PropertyMock) as mock_org:
            # Mock payload with repos_url
            mock_payload = {
                "repos_url": "https://api.github.com/orgs/google/repos"
            }
            mock_org.return_value = mock_payload

            # Create client instance and test _public_repos_url
            client = GithubOrgClient("google")
            result = client._public_repos_url

            # Verify the result matches the expected URL
            expected_url = "https://api.github.com/orgs/google/repos"
            self.assertEqual(result, expected_url)

    @patch('client.get_json')
    def test_public_repos(self, mock_get_json):
        """Test that public_repos returns expected list of repos and calls
        mocked methods once."""
        # Mock payload for get_json
        mock_repos_payload = [
            {"name": "repo1", "license": {"key": "mit"}},
            {"name": "repo2", "license": {"key": "apache-2.0"}},
            {"name": "repo3", "license": None}
        ]
        mock_get_json.return_value = mock_repos_payload

        # Use context manager to mock _public_repos_url
        mock_url_path = 'client.GithubOrgClient._public_repos_url'
        with patch(mock_url_path, new_callable=PropertyMock) as mock_url:
            mock_url.return_value = "https://api.github.com/orgs/google/repos"

            # Create client instance and call public_repos
            client = GithubOrgClient("google")
            result = client.public_repos()

            # Verify the result is the expected list of repo names
            expected_repos = ["repo1", "repo2", "repo3"]
            self.assertEqual(result, expected_repos)

            # Verify mocked property was called once
            mock_url.assert_called_once()

            # Verify get_json was called once
            mock_get_json.assert_called_once()

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False),
    ])
    def test_has_license(self, repo, license_key, expected):
        """Test that has_license returns expected boolean based on repo
        license."""
        client = GithubOrgClient("google")
        result = client.has_license(repo, license_key)
        self.assertEqual(result, expected)


@parameterized_class(
    ("org_payload", "repos_payload", "expected_repos", "apache2_repos"),
    TEST_PAYLOAD
)
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """
    Integration test cases for the GithubOrgClient class.
    This class contains integration tests that mock external requests
    but test the full flow of the GithubOrgClient methods.
    """

    @classmethod
    def setUpClass(cls):
        """Set up class fixtures and start request patcher."""
        def side_effect(url):
            """Side effect function to return appropriate payload based on
            URL."""
            mock_response = Mock()
            if url == "https://api.github.com/orgs/google":
                mock_response.json.return_value = cls.org_payload
            elif url == "https://api.github.com/orgs/google/repos":
                mock_response.json.return_value = cls.repos_payload
            else:
                mock_response.json.return_value = None
            return mock_response

        # Start patcher for requests.get
        cls.get_patcher = patch('requests.get', side_effect=side_effect)
        cls.get_patcher.start()

    @classmethod
    def tearDownClass(cls):
        """Stop the request patcher."""
        cls.get_patcher.stop()

    def test_public_repos(self):
        """Test that public_repos returns expected list of repos from
        fixtures."""
        client = GithubOrgClient("google")
        result = client.public_repos()
        self.assertEqual(result, self.expected_repos)

    def test_public_repos_with_license(self):
        """Test that public_repos with license filter returns expected
        apache-2.0 repos from fixtures."""
        client = GithubOrgClient("google")
        result = client.public_repos(license="apache-2.0")
        self.assertEqual(result, self.apache2_repos)


if __name__ == '__main__':
    unittest.main()
