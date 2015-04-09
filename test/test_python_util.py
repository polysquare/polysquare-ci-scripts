# /test/test_python_util.py
#
# Test cases for the function in ciscripts/python_util.py
#
# See /LICENCE.md for Copyright information
"""Test cases for the functions in ciscripts/python_util.py."""

import sys

import ciscripts.python_util as python_util

from mock import Mock

from nose_parameterized import (param, parameterized)

from testtools import TestCase


class TestGetPythonVersion(TestCase):

    """Test cases for obtaining the python version."""

    @parameterized.expand([param(1, "{0}".format(sys.version_info[0])),
                           param(2, "{0}.{1}".format(sys.version_info[0],
                                                     sys.version_info[1])),
                           param(3,
                                 "{0}.{1}.{2}".format(sys.version_info[0],
                                                      sys.version_info[1],
                                                      sys.version_info[2]))])
    def test_get_python_version_at_precision(self,
                                             precision,
                                             expected_version):
        """Get python version at precision."""
        self.assertEqual(expected_version,
                         python_util.get_python_version(precision))


class TestDetermineIfPythonModulesAvailable(TestCase):

    """Test cases for determining if a python module is available."""

    def test_python_module_available(self):
        """Return true where python module is available."""
        self.assertTrue(python_util.python_module_available("sys"))

    def test_python_module_not_available(self):
        """Return false where python module is not available."""
        self.assertFalse(python_util.python_module_available("___unavailable"))

    def test_run_function_if_python_module_unavailable(self):
        """Function executed if python module unavailable."""
        mock = Mock()
        python_util.run_if_module_unavailable("___unavailable", mock, "arg")

        mock.assert_called_with("arg")

    def test_dont_run_function_if_python_module_available(self):
        """Function not executed when python module available."""
        mock = Mock()
        python_util.run_if_module_unavailable("sys", mock)

        mock.assert_not_called()  # suppress(PYC70)
