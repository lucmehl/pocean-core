#!python
# coding=utf-8
import os
import shutil
import unittest
import tempfile

import numpy as np

from pocean.dataset import EnhancedDataset
from pocean.utils import generic_masked, get_default_axes

import logging
from pocean import logger
logger.level = logging.INFO
logger.handlers = [logging.StreamHandler()]


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.input_file = os.path.join(os.path.dirname(__file__), "resources/coamps.nc")

    def test_get_default_axes(self):
        assert get_default_axes() == (
            'trajectory',
            'station',
            'profile',
            't',
            'x',
            'y',
            'z',
        )

        new_defaults = {
            'trajectory': 'a',
            'station':    'b',
            'profile':    'c',
            't':          'd',
            'x':          'e',
            'y':          'f',
            'z':          'g',
        }
        assert get_default_axes(new_defaults) == (
            'a',
            'b',
            'c',
            'd',
            'e',
            'f',
            'g',
        )

        new_defaults = {
            'trajectory': 'a',
            'station':    'b',
            'profile':    'c'
        }
        assert get_default_axes(new_defaults) == (
            'a',
            'b',
            'c',
            't',
            'x',
            'y',
            'z',
        )

        # Time is not a valid axis key
        bad_defaults = {
            'time': 'a'
        }
        with self.assertRaises(TypeError):
            get_default_axes(bad_defaults)

        # Can't have duplicate values
        bad_defaults = {
            'x': 'a',
            'y': 'a'
        }
        with self.assertRaises(ValueError):
            get_default_axes(bad_defaults)

    def test_single_attr_filter(self):
        nc = EnhancedDataset(self.input_file)
        grid_spacing_vars = nc.filter_by_attrs(grid_spacing='4.0 km')

        x = nc.variables.get('x')
        y = nc.variables.get('y')

        self.assertEqual(len(grid_spacing_vars), 2)
        assert x in grid_spacing_vars
        assert y in grid_spacing_vars

    def test_multiple_attr_filter(self):
        nc = EnhancedDataset(self.input_file)
        grid_spacing_vars = nc.filter_by_attrs(grid_spacing='4.0 km', standard_name='projection_y_coordinate')

        y = nc.variables.get('y')

        self.assertEqual(len(grid_spacing_vars), 1)
        assert y in grid_spacing_vars

    def test_generic_masked_bad_min_max_value(self):

        fid, tpath = tempfile.mkstemp(suffix='.nc', prefix='pocean-test')
        shutil.copy2(self.input_file, tpath)

        with EnhancedDataset(tpath, 'a') as ncd:
            v = ncd.variables['v_component_wind_true_direction_all_geometries']
            v.valid_min = 0.1
            v.valid_max = 0.1
            r = generic_masked(v[:], attrs=ncd.vatts(v.name))
            rflat = r.flatten()
            assert rflat[~rflat.mask].size == 0

            # Create a byte variable with a float valid_min and valid_max
            # to make sure it doesn't error
            b = ncd.createVariable('imabyte', 'b')
            b.valid_min = 0
            b.valid_max = 600  # this is over a byte and thus invalid
            b[:] = 3
            r = generic_masked(b[:], attrs=ncd.vatts(b.name))
            assert np.all(r.mask == False)  # noqa

            b.valid_min = 0
            b.valid_max = 2
            r = generic_masked(b[:], attrs=ncd.vatts(b.name))
            assert np.all(r.mask == True)  # noqa

            c = ncd.createVariable('imanotherbyte', 'f4')
            c.setncattr('valid_min', b'0')
            c.setncattr('valid_max', b'9')
            c[:] = 3
            r = generic_masked(c[:], attrs=ncd.vatts(c.name))
            assert np.all(r.mask == False)  # noqa

            c = ncd.createVariable('imarange', 'f4')
            c.valid_range = [0.0, 2.0]
            c[:] = 3.0
            r = generic_masked(c[:], attrs=ncd.vatts(c.name))
            assert np.all(r.mask == True)  # noqa

            c.valid_range = [0.0, 2.0]
            c[:] = 1.0
            r = generic_masked(c[:], attrs=ncd.vatts(c.name))
            assert np.all(r.mask == False)  # noqa

        os.close(fid)
        if os.path.exists(tpath):
            os.remove(tpath)


class TestNetcdfUtils(unittest.TestCase):

    def test_cf_safe_name(self):
        from pocean.cf import cf_safe_name
        self.assertEqual('foo', cf_safe_name('foo'))
        self.assertEqual('v_1foo', cf_safe_name('1foo'))
        self.assertEqual('v_1foo_99', cf_safe_name('1foo-99'))
        self.assertEqual('foo_99', cf_safe_name('foo-99'))
        self.assertEqual('foo_99_', cf_safe_name('foo(99)'))
        self.assertEqual('v__foo_99_', cf_safe_name('_foo(99)'))