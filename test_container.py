#!/usr/bin/env python3
"""Test creation and use of the Container class"""

import unittest

import control


class CreateContainer(unittest.TestCase):
    """
    Ensure that a container class is always created correctly with all
    possible variants of a Controlfile service
    """

    def test_happy_path(self):
        """Make sure that the defaults still work"""
        image = 'busybox'
        conf = {"name": "grafana", "hostname": "grafana"}
        container = control.Container(image, conf)
        self.assertEqual(container.expected_timeout, 10)
        self.assertEqual(container.conf['image'], image)


def suite():
    """Group TestCases together so all the tests run"""
    testsuite = unittest.TestSuite()
    testsuite.addTest(unittest.makeSuite(CreateContainer))
    return testsuite


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())