import unittest

from tests.endpoints import ExistingEndpoints

tests = [
    ExistingEndpoints,
]

if __name__ == "__main__":
    for test in tests:
        unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(test))
