"""Unittests for tdm_loader"""
import os
import pytest
import numpy as np

import tdm_loader as tdm


@pytest.fixture(scope="module")
def tdm_file(request):
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)
    path = f"{test_dir}/test_sample0001.tdm"
    data = tdm.OpenFile(str(path))
    return data


def test_channel_accessibility(tdm_file):
    arg_arr = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]
    try:
        for ch in arg_arr:
            tdm_file.channel(*ch)
        tdm_file.channel(0, 0, 0)
    except IndexError:
        pytest.fail("Not all channels are accessible.")


def test_invalid_channel_raises_error(tdm_file):
    arg_arr = [
        (-4, -1),
        (-4, 0),
        (0, -4),
        (3, 0),
        (0, 3),
        (1, 2),
        (2, 1),
        (1, 2),
        (3, 0),
    ]

    for ch in arg_arr:
        with pytest.raises(IndexError):
            tdm_file.channel(*ch)


def test_get_channel_by_index(tdm_file):
    assert (tdm_file.channel(0, 0) == np.array([1, 2, 3, 4])).all()
    assert (tdm_file.channel(0, 1) == np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])).all()

    assert (
        tdm_file.channel(0, 2)
        == np.array([9, 10, 11, -50, 2147483647, -2147483647 - 1])
    ).all()
    assert (
        tdm_file.channel(1, 0) == np.array([1.7976931348623157e308, 2147483647])
    ).all()
    assert (tdm_file.channel(1, 1) == np.array([0])).all()
    assert (
        tdm_file.channel("channel2_test123$$?", "Float_4_Integers")
        == np.array([1, 2, 3, 4])
    ).all()
    assert (
        tdm_file.channel(0, "Float as Float")
        == np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    ).all()
    assert (
        tdm_file.channel(0, "Integer32_with_max_min")
        == np.array(
            [
                9,
                10,
                11,
                -50,
                2147483647,
                -2147483648,
            ]
        )
    ).all()
    assert (
        tdm_file.channel("channel2", 0)
        == np.array([1.7976931348623157e308, 2147483647])
    ).all()
    assert (tdm_file.channel("channel2", 1) == np.array([0])).all()
    assert (
        tdm_file.channel("channel2", "")
        == np.array([1.7976931348623157e308, 2147483647])
    ).all()
    assert (tdm_file.channel("channel2", "", ch_occurrence=1) == np.array([0])).all()


def test_get_channel_group_by_str(tdm_file):
    assert (tdm_file.channel("channel2_test123$$?", 0) == np.array([1, 2, 3, 4])).all()
    assert (
        tdm_file.channel("channel2_test123$$?", 2)
        == np.array([9, 10, 11, -50, 2147483647, -2147483647 - 1])
    ).all()
    assert (tdm_file.channel("channel2", 1) == np.array([0])).all()


def test_channel_invalid_type(tdm_file):
    invalids = [
        (0.0, 1.0),
        (-1, 0),
        (0, -1),
        (-1, -1),
        (0, "lala"),
        (0, 0, 1),
        (0.0, 1, "lala"),
        (0.0, 1, 1.0),
    ]
    for invalid in invalids:
        with pytest.raises(TypeError):
            tdm_file.channel(invalid)


def test_channel_group_index(tdm_file):
    assert tdm_file.channel_group_index("channel2_test123$$?") == 0
    assert tdm_file.channel_group_index("channel2", 0) == 1

    with pytest.raises(IndexError):
        tdm_file.channel_group_index("channel2", 1)
    with pytest.raises(ValueError):
        tdm_file.channel_group_index("test")
    with pytest.raises(TypeError):
        tdm_file.channel_group_index(0)
    with pytest.raises(TypeError):
        tdm_file.channel_group_index(0.0)
    with pytest.raises(TypeError):
        tdm_file.channel_group_index("channel2", "lala")


def test_channel_group_name(tdm_file):
    assert tdm_file.channel_group_name(0) == "channel2_test123$$?"
    assert tdm_file.channel_group_name(1) == "channel2"

    with pytest.raises(TypeError):
        tdm_file.channel_group_name("lala")
    with pytest.raises(TypeError):
        tdm_file.channel_group_name(0.0)


def test_channel_group_search(tdm_file):
    assert tdm_file.channel_group_search("channel") == [
        ("channel2_test123$$?", 0),
        ("channel2", 1),
        ("channel3", 2),
    ]

    assert tdm_file.channel_group_search("test") == [("channel2_test123$$?", 0)]
    assert tdm_file.channel_group_search("helloworld") == []
    assert tdm_file.channel_group_search("") == [
        ("channel2_test123$$?", 0),
        ("channel2", 1),
        ("channel3", 2),
    ]
    bad_types = [0, -1]
    for bad_type in bad_types:
        with pytest.raises(TypeError):
            tdm_file.channel_group_search(bad_type)


def test_channel_name(tdm_file):
    assert tdm_file.channel_name(0, 0) == "Float_4_Integers"
    assert tdm_file.channel_name(0, 1) == "Float as Float"
    assert tdm_file.channel_name(0, 2) == "Integer32_with_max_min"
    assert tdm_file.channel_name(1, 0) == ""
    assert tdm_file.channel_name(1, 1) == ""

    bad_idxs = [(2, 0), (0, 3)]
    for bad_idx in bad_idxs:
        with pytest.raises(IndexError):
            tdm_file.channel_name(*bad_idx)

    bad_ch_names = [("lala", 0), (0, "lala"), (0, 0.0), (0.0, 0)]
    for bad_ch_name in bad_ch_names:
        with pytest.raises(TypeError):
            tdm_file.channel_name(bad_ch_name)


def test_channel_search(tdm_file):
    assert tdm_file.channel_search("Integers") == [("Float_4_Integers", 0, 0)]
    assert tdm_file.channel_search("Float") == [
        ("Float_4_Integers", 0, 0),
        ("Float as Float", 0, 1),
    ]

    assert tdm_file.channel_search("") == []


def test_channel_dict(tdm_file):
    assert (
        tdm_file.channel_dict(0)["Integer32_with_max_min"]
        == np.array([9, 10, 11, -50, 2147483647, -2147483648])
    ).all()
    assert (
        tdm_file.channel_dict(0)["Float as Float"]
        == np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    ).all()
    assert (
        tdm_file.channel_dict(0)["Float_4_Integers"] == np.array([1, 2, 3, 4])
    ).all()

    assert (tdm_file.channel_dict(1)[""] == np.array([0])).all()


def test_channel_dict_idx_err(tdm_file):
    for bad_idx in [-4, 3]:
        with pytest.raises(IndexError):
            tdm_file.channel_dict(bad_idx)


def test_channel_unit(tdm_file):
    assert tdm_file.channel_unit(0, 0) == "arb. units"
    assert tdm_file.channel_unit(0, 1) == "eV"
    assert tdm_file.channel_unit(1, 0) == ""


def test_channel_unit_err(tdm_file):
    with pytest.raises(IndexError):
        tdm_file.channel_unit("hello", 0)
    with pytest.raises(TypeError):
        tdm_file.channel_unit(0.0, 0)
    with pytest.raises(TypeError):
        tdm_file.channel_unit(0, 0.0)


def test_no_of_channel_groups(tdm_file):
    assert tdm_file.no_channel_groups() == 3


def test_no_of_channels(tdm_file):
    assert tdm_file.no_channels(0) == 3
    assert tdm_file.no_channels(1) == 2
    assert tdm_file.no_channels(-1) == 0
    assert tdm_file.no_channels(-2) == 2
    assert tdm_file.no_channels(-3) == 3


def test_no_of_channels_err(tdm_file):
    for bad_idx in [-4, 5]:
        with pytest.raises(IndexError):
            tdm_file.no_channels(bad_idx)
    with pytest.raises(TypeError):
        tdm_file.no_channels(1.0)


def test_len(tdm_file):
    assert len(tdm_file) == 3


def test_get_item(tdm_file):
    assert (tdm_file[0] == np.array([1, 2, 3, 4])).all()
    assert (tdm_file[1] == np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])).all()
    assert (
        tdm_file[2]
        == np.array(
            [
                9,
                10,
                11,
                -50,
                2147483647,
                -2147483648,
            ]
        )
    ).all()
    assert (tdm_file[1, 0] == np.array([1.7976931348623157e308, 2147483647])).all()
    assert (tdm_file[1, 1] == np.array([0])).all()
    assert (
        tdm_file["Integer32_with_max_min"]
        == np.array(
            [
                9,
                10,
                11,
                -50,
                2147483647,
                -2147483648,
            ]
        )
    ).all()
    assert (
        tdm_file["Float as Float"] == np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    ).all()
    assert (tdm_file["Float_4_Integers"] == np.array([1, 2, 3, 4])).all()


def test_get_item_err(tdm_file):
    with pytest.raises(IndexError):
        tdm_file[5]
    with pytest.raises(IndexError):
        tdm_file[-6]
