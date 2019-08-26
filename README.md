This module allows National Instruments TDM/TDX files to be accessed like
NumPy structured arrays.

It can be installed in the standard way::

    python setup.py install

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
