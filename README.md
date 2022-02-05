[![PyPI](https://img.shields.io/pypi/v/tdm_loader)](https://pypi.org/project/tdm_loader/)
[![Pytest](https://github.com/domna/tdm_loader/actions/workflows/pytest.yml/badge.svg)](https://github.com/domna/tdm_loader/actions/workflows/pytest.yml)
[![Coverage Status](https://coveralls.io/repos/github/domna/tdm_loader/badge.svg?branch=master)](https://coveralls.io/github/domna/tdm_loader?branch=master)
[![Documentation Status](https://readthedocs.org/projects/tdm_loader/badge/?version=latest)](https://tdm-loader.readthedocs.io/en/latest/?badge=latest)

This module allows National Instruments TDM/TDX files to be accessed like
NumPy structured arrays.

To install the newest version use::

    pip install tdm-loader

Sample usage::

    import tdm_loader
    data_file = tdm_loader.OpenFile('filename.tdm')
    
Access a channel by channel group and channel index combination::
    
    data_file.channel(channel_group, channel)

Get a dict of all channels in a channel group:

    data_file.channel_dict(channel_group)

Search for a column name.  A list of all column names that contain
``search_term`` and their indices will be returned::

    data_file.channel_search(search_term)
