import unittest

from tests.endpoints import TestExistingEndpoints
from tests.moderation import TestFilterReportedPosts

tests = [
    TestExistingEndpoints,
    TestFilterReportedPosts,
]

if __name__ == "__main__":
    for test in tests:
        unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(test))
