"""Test transforms on an individual service"""

import unittest
import logging
import sys

from .context import control


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
        service = {"name": "example"}
        ret = control.Controlfile.normalize_service(service)
        self.assertEqual(ret['name'], "example")
        self.assertIn('service', ret)
        self.assertEqual(ret['service'], "example")
        self.assertIn('hostname', ret)
        self.assertEqual(ret['hostname'], "example")

    def test_name_prefixes(self):
        """check for prefix changes"""
        service = {
            "service": "example",
            "name": "example",
            "hostname": "service"
        }
        options = {"name": {"prefix": "1."}}
        ret = control.Controlfile.normalize_service(service, options)
        self.assertEqual(ret['name'], "1.example")
        self.assertEqual(ret['service'], "example")
        self.assertEqual(ret['hostname'], "service")
        del service['service']
        ret = control.Controlfile.normalize_service(service, options)
        self.assertEqual(ret['name'], "1.example")
        self.assertEqual(ret['service'], "example",
                         "service name is affected by name prefix")
        self.assertEqual(ret['hostname'], "service")

    def test_name_suffixes(self):
        """check for suffix changes"""
        service = {
            "service": "example",
            "name": "example",
            "hostname": "service"
        }
        options = {"name": {"suffix": ".company"}}
        ret = control.Controlfile.normalize_service(service, options)
        self.assertEqual(ret['name'], "example.company")
        self.assertEqual(ret['service'], "example")
        self.assertEqual(ret['hostname'], "service")
        del service['service']
        ret = control.Controlfile.normalize_service(service, options)
        self.assertEqual(ret['name'], "example.company")
        self.assertEqual(ret['service'], "example",
                         "service name is affected by name suffix")
        self.assertEqual(ret['hostname'], "service")