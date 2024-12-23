import unittest

from tests.test_endpoints import TestExistingEndpoints
from tests.test_moderation import TestFilterReportedPosts

tests = [
    TestExistingEndpoints,
    TestFilterReportedPosts,
]

if __name__ == "__main__":
    for test in tests:
        unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(test))
