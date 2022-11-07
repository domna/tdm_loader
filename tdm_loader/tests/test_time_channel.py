"""Test """
import os
import pytest
import numpy as np
from numpy.testing import assert_array_equal

import tdm_loader as tdm


@pytest.fixture(scope="module")
def tdm_file(request):
    """Fixture for loading a test tdm file"""
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)
    path = f"{test_dir}/test_file_time.tdm"
    data = tdm.OpenFile(str(path))
    return data


# pylint: disable=redefined-outer-name
def test_time_channel(tdm_file):
    """Test correct reading of the time channel"""
    time_channel_ref = np.array([
       '2022-11-04T14:37:48.565332889', '2022-11-04T14:37:49.285334110',
       '2022-11-04T14:37:49.975335121', '2022-11-04T14:37:50.615335941',
       '2022-11-04T14:37:51.255336761', '2022-11-04T14:37:51.905337810',
       '2022-11-04T14:37:52.545338630', '2022-11-04T14:37:53.195339202',
       '2022-11-04T14:37:53.835340499', '2022-11-04T14:37:54.485341072',
       '2022-11-04T14:37:55.155342102', '2022-11-04T14:37:55.865343093',
       '2022-11-04T14:37:56.525343894', '2022-11-04T14:37:57.235344886',
       '2022-11-04T14:37:57.885345935', '2022-11-04T14:37:58.525346755',
       '2022-11-04T14:37:59.165347576', '2022-11-04T14:37:59.905348777',
       '2022-11-04T14:38:00.565349578', '2022-11-04T14:38:01.215350627',
       '2022-11-04T14:38:01.865351676', '2022-11-04T14:38:02.555352687',
       '2022-11-04T14:38:03.205353260', '2022-11-04T14:38:03.845354080',
       '2022-11-04T14:38:04.485355377', '2022-11-04T14:38:05.125356197',
       '2022-11-04T14:38:05.765357017'], dtype='datetime64[ns]')
    assert_array_equal(tdm_file.channel(0, "Time"), time_channel_ref)
