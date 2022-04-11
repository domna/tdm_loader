"""Tests zip based tdm files to work with tdm_loader"""
import os
import pytest
import numpy as np
from numpy.testing import assert_array_equal

import tdm_loader as tdm


@pytest.fixture(scope="module")
def get_file_dir(request):
    """Fixture for loading the supplementary test files directory"""
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)
    return test_dir


@pytest.fixture(scope="module")
# pylint: disable=redefined-outer-name
def tdm_file(get_file_dir):
    """Fixture for loading a test tdm file"""
    path = f"{get_file_dir}/2021-02-26_07-55-01.tdm"
    data = tdm.OpenFile(str(path))
    return data


# pylint: disable=redefined-outer-name
def test_explicit_sequence_representation(get_file_dir, tdm_file):
    """Handles explicit sequence representation channels correctly"""
    assert_array_equal(
        tdm_file.channel(1, 5), np.loadtxt(f"{get_file_dir}/channel15.txt")
    )
    assert tdm_file.channel_name(1, 5) == "eps_HAC_RE_CIT_UN_c_Offset"


# pylint: disable=redefined-outer-name
def test_linear_implicit_repr(get_file_dir, tdm_file):
    """Handles linear_implicit sequence representation correctly"""
    assert_array_equal(
        tdm_file.channel(0, 0), np.loadtxt(f"{get_file_dir}/channel00.txt")
    )
    assert tdm_file.channel_name(0, 0) == "Zeit_[200Hz]-rel"
    assert tdm_file.channel(0, 0).shape == (11316,)


# pylint: disable=redefined-outer-name
def test_linear_implicit_repr_with_offset(get_file_dir, tdm_file):
    """Handles linear_implicit sequence representation with offset correctly"""
    assert_array_equal(
        tdm_file.channel(0, 1), np.loadtxt(f"{get_file_dir}/channel01.txt")
    )
    assert tdm_file.channel_name(0, 1) == "Zeit_[200Hz]-abs"
    assert tdm_file.channel(0, 1).shape == (11316,)


# pylint: disable=redefined-outer-name
def test_raw_linear_repr(get_file_dir, tdm_file):
    """Handles raw_linear sequence representation correctly"""
    assert tdm_file.channel_name(0, 15) == "F___Zylinder_02"
    assert_array_equal(
        tdm_file.channel(0, 15), np.loadtxt(f"{get_file_dir}/channel015.txt")
    )
