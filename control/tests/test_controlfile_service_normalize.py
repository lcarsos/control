"""Test transforms on an individual service"""

import unittest
import logging
import sys

from control.controlfile import normalize_service


class TestNormalization(unittest.TestCase):
    """
    test applying transforms to a service.

    These transforms can be prefixes, suffixes, and unions.
    """

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    def test_unspecified_service(self):
        """
        A Control service does not need to specify a service name if it
        specifies a container name
        """
        service = {"container": {"name": "example"}}
        name, ret = normalize_service(service)
        self.assertEqual(ret['container']['name'], "example")
        self.assertEqual(name, "example")
        self.assertIn('hostname', ret['container'])
        self.assertEqual(ret['container']['hostname'], "example")

    def test_name_prefixes(self):
        """check for prefix changes"""
        service = {
            "service": "example",
            "container": {
                "name": "example",
                "hostname": "service"
            }
        }
        options = {"name": {"prefix": "1."}}
        name, ret = normalize_service(service, options)
        self.assertEqual(ret['container']['name'], "1.example")
        self.assertEqual(name, "example")
        self.assertEqual(ret['container']['hostname'], "service")
        del service['service']
        name, ret = normalize_service(service, options)
        self.assertEqual(ret['container']['name'], "1.example")
        self.assertEqual(name, "example",
                         "service name is affected by name prefix")
        self.assertEqual(ret['container']['hostname'], "service")

    def test_name_suffixes(self):
        """check for suffix changes"""
        service = {
            "service": "example",
            "container": {
                "name": "example",
                "hostname": "service"
            }
        }
        options = {"name": {"suffix": ".company"}}
        name, ret = normalize_service(service, options)
        self.assertEqual(ret['container']['name'], "example.company")
        self.assertEqual(name, "example")
        self.assertEqual(ret['container']['hostname'], "service")
        del service['service']
        name, ret = normalize_service(service, options)
        self.assertEqual(ret['container']['name'], "example.company")
        self.assertEqual(name, "example",
                         "service name is affected by name suffix")
        self.assertEqual(ret['container']['hostname'], "service")
