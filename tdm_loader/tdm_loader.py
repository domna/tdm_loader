"""This module allows National Instruments TDM/TDX files to be accessed like
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
"""
import os.path
import re
import xml.etree.ElementTree as ElementTree
import warnings

import numpy as np

try:
    from matplotlib import pyplot as plt

    plt_available = True
except ImportError:
    plt_available = False

__all__ = ('OpenFile',)

# XML "QName" in the TDM file
# there has to be an easy way to determine this programmatically
QNAME = '{http://www.ni.com/Schemas/USI/1_0}'

# dictionary for converting from NI to NumPy datatypes
DTYPE_CONVERTERS = {'eInt8Usi': 'i1',
                    'eInt16Usi': 'i2',
                    'eInt32Usi': 'i4',
                    'eInt64Usi': 'i8',
                    'eUInt8Usi': 'u1',
                    'eUInt16Usi': 'u2',
                    'eUInt32Usi': 'u4',
                    'eUInt64Usi': 'u8',
                    'eFloat32Usi': 'f4',
                    'eFloat64Usi': 'f8',
                    'eStringUsi': 'U'}


class OpenFile(object):
    """Class for opening a National Instruments TDM/TDX file.

    Parameters
    ----------
    tdm_path : str
        The full path to the .TDM file.
    tdx_path : str, Optional
        The full path to the .TDX file.  If not present, it will be assumed the
        TDX file is located in the same directory as the .TDM file, and the
        filename specified in the .TDM file will be used.
    """

    def __init__(self, tdm_path, tdx_path='', encoding='utf-8'):
        self._folder, self._tdm_filename = os.path.split(tdm_path)

        self._root = ElementTree.parse(tdm_path).getroot()
        self._namespace = {'usi': self._root.tag.split('}')[0].strip('{')}

        self._xml_tdm_root = self._root.find('.//tdm_root')
        self._xml_chgs = list(map(lambda usi: self._root.find('.//tdm_channelgroup[@id=\'{0}\']'.format(usi)),
                                  re.findall("id\(\"(.+?)\"\)", self._xml_tdm_root.findtext('channelgroups'))))

        byte_order = self._root.find('.//file').get('byteOrder')
        if byte_order == 'littleEndian':
            self._endian = '<'
        elif byte_order == 'bigEndian':
            self._endian = '>'
        else:
            raise TypeError('Unknown endian format in TDM file')

        self._tdx_order = 'C'  # Set binary file reading to column-major style
        if tdx_path == '':
            self._tdx_path = os.path.join(self._folder, self._root.find('.//file').get('url'))
        else:
            self._tdx_path = tdx_path

    def _channel_xml(self, channel_group, channel, occurrence=0, ch_occurrence=0):
        chs = self._channels_xml(channel_group, occurrence)

        if isinstance(channel, int):
            if len(chs) <= channel or channel < -len(chs):
                raise IndexError('Channel {0} out of range'.format(channel))

            ch = chs[channel]
        elif isinstance(channel, str):
            chns = list(filter(lambda x: x.findtext('name') == channel, chs))
            if len(chns) < ch_occurrence:
                raise IndexError('Channel {0} (occurrence {1}) not found'.format(channel, ch_occurrence))

            ch = chns[ch_occurrence]
        else:
            raise TypeError('The given channel parameter type is unsupported')

        return ch

    def _channels_xml(self, channel_group, occurrence=0):
        if isinstance(channel_group, int):
            if len(self._xml_chgs) <= channel_group or channel_group < -len(self._xml_chgs):
                raise IndexError('Channel group {0} out of range'.format(channel_group))

            chg = self._xml_chgs[channel_group]
        elif isinstance(channel_group, str):
            chgns = list(filter(lambda x: x.findtext('name') == channel_group, self._xml_chgs))
            if len(chgns) <= occurrence:
                raise IndexError('Channel group {0} (occurrence {1}) not found'.format(channel_group, occurrence))

            chg = chgns[occurrence]
        else:
            raise TypeError("The given channel group parameter type is unsupported")

        chs = list(map(lambda usi: self._root.find(".//tdm_channel[@id='{0}']".format(usi)),
                       OpenFile._get_usi_from_txt(chg.findtext('channels'.format(chg.get('id'))))))

        return chs

    @staticmethod
    def _get_usi_from_txt(txt):
        if txt is None or txt.strip() == '':
            return []
        else:
            return re.findall("id\(\"(.+?)\"\)", txt)

    def channel_group_search(self, search_term):
        """Returns a list of channel group names that contain ``search term``.
        Results are independent of case and spaces in the channel name.
        
        Parameters
        ----------
            search_term : str
                The term to search for in the channel group names
        
        Returns
        -------
        found_terms : list of (str, int)
            Returns the found channel group names as tuple of full name and channel group index.
        """
        if not isinstance(search_term, str):
            raise TypeError("I can search for str terms only.")

        chg_names = [x.text for x in self._root.findall(".//tdm_channelgroup/name")
                     if x.text is not None]
        search_term = search_term.upper().replace(' ', '')
        found_terms = [name for name in chg_names if
                       name.upper().replace(' ', '').find(search_term) >= 0]

        ind = []
        for name in found_terms:
            i = chg_names.index(name)
            ind.append((name, i))

        return ind

    def channel_search(self, search_term):
        """Returns a list of channel names that contain ``search term``.
        Results are independent of case and spaces in the channel name.
        
        Parameters
        ----------
            search_term : str
                The term to search for in the channel names
            return_column : bool
                If True the function returns the column index instead of channel group and channel indices
        
        Returns
        -------
        found_terms : list of (str, int, int) or löist of (str, int) (latter case for return_column = True)
            Returns the found channel names as tuple of full name and column index or channel group and channel indices
            depending on the value of return_column.
        """
        search_term = str(search_term).upper().replace(' ', '')

        ind_chg_ch = []
        for j, chg in enumerate(self._xml_chgs):
            chs = self._channels_xml(j)

            if search_term == "":
                found_terms = [ch.findtext('name') for ch in chs if ch.findtext('name') is None]
            else:
                found_terms = [ch.findtext('name') for ch in chs if ch.findtext('name') is not None
                               and ch.findtext('name').upper().replace(' ', '').find(str(search_term)) >= 0]

            for name in found_terms:
                i = [ch.findtext('name') for ch in chs].index(name)
                ind_chg_ch.append((name, j, i))

        return ind_chg_ch

    def channel(self, channel_group, channel, occurrence=0, ch_occurrence=0):
        """Returns a data channel by its channel group and channel index.
        
        Parameters
        ----------
        channel_group : int or str
            The index or name of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        occurrence : int, Optional
            Gives the nth occurrence of the channel group name. By default the first occurrence is returned.
            This parameter is only used when channel_group is given as a string.
        ch_occurrence : int, Optional
            Gives the nth occurrence of the channel name. By default the first occurrence is returned.
            This parameter is only used when channel_group is given as a string.
        """

        ch = self._channel_xml(channel_group, channel, occurrence, ch_occurrence)

        datatype = ch.findtext('datatype').split('_')[1].lower() + '_sequence'
        lc_usi = OpenFile._get_usi_from_txt(ch.findtext('local_columns'))[0]
        lc = self._root.find(".//localcolumn[@id='{0}']".format(lc_usi))
        repr = lc.findtext('sequence_representation')
        data_usi = OpenFile._get_usi_from_txt(lc.findtext('values'))[0]
        inc = self._root.find(".//{0}[@id='{1}']/values".format(datatype, data_usi))

        if inc.get('external') is None:
            data = list(map(lambda x: x.text,
                            self._root.findall(".//{0}[@id='{1}']/values/*".format(datatype, data_usi))))
        else:
            ext_attribs = self._root.find(".//file/block[@id='{0}']".format(inc.get('external'))).attrib

            data = np.memmap(self._tdx_path,
                             offset=int(ext_attribs['byteOffset']),
                             shape=(int(ext_attribs['length']),),
                             dtype=np.dtype(self._endian + DTYPE_CONVERTERS[ext_attribs['valueType']]),
                             mode='r',
                             order=self._tdx_order).view(np.recarray)

        # ToDo: Support for implicit linear data
        # if repr == 'implicit_linear':
        # if repr == 'explicit':
        # if repr == 'raw_linear':

        return data

    def channel_dict(self, channel_group, occurrence=0):
        """Returns a dict representation of a channel group.

        Parameters
        ----------
        channel_group : int or str
            The index or name of the channel group.
        occurrence : int
            Gives the nth occurrence of the channel group name. By default the first occurrence is returned.
            This parameter is only used when channel_group is given as a string."""

        if isinstance(channel_group, int):
            channel_dict = {}
            name_doublets = set()
            for i in range(self.no_channels(channel_group)):
                name = self.channel_name(channel_group, i)
                ch = self.channel(channel_group, i)
                if name in channel_dict:
                    name_doublets.add(name)
                channel_dict[name] = np.array(ch)
            if len(name_doublets) > 0:
                warnings.warn("Duplicate channel name(s): {}"
                              .format(name_doublets))
            return channel_dict
        elif isinstance(channel_group, str):
            chg_ind = self.channel_group_index(channel_group, occurrence)

            return self.channel_dict(chg_ind)

    def channel_name(self, channel_group, channel, occurrence=0):
        """Returns the name of the channel at given channel group and channel indices.
        
        Parameters
        ----------
        channel_group : int or str
            The index of the channel group.
        channel : int
            The index or name of the channel inside the group.
        occurrence : int
            The nth occurrence of the channel_group name
        """
        ch = self._channel_xml(channel_group, channel, occurrence=occurrence)

        return ch.findtext('name')

    def channel_unit(self, channel_group, channel, occurrence=0, ch_occurrence=0):
        """Returns the unit of the channel at given channel group and channel indices.
        
        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        occurrence : int
            The nth occurrence of the channel group name
        ch_occurrence : int
            The nth occurrence of the channel name
        """
        ch = self._channel_xml(channel_group, channel, occurrence, ch_occurrence)

        return ch.findtext('unit_string')

    def channel_description(self, channel_group, channel, occurrence=0, ch_occurrence=0):
        """Returns the description of the channel at given channel group and channel indices.

        Parameters
        ----------
        channel_group : int or str
            The index of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        occurrence : int
            The nth occurrence of the channel group name
        ch_occurrence : int
            The nth occurrence of the channel name
        """
        ch = self._channel_xml(channel_group, channel, occurrence, ch_occurrence)

        return ch.findtext('description')

    def channel_group_name(self, channel_group):
        """Returns the name of the channel group at the channel group index.
        
        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        """
        if not isinstance(channel_group, int):
            raise TypeError("Only integer values allowed.")

        try:
            return [chg.findtext('name') for chg in self._xml_chgs][channel_group]
        except IndexError:
            raise IndexError("Channelgroup " + str(channel_group) + " out of range")

    def channel_group_index(self, channel_group_name, occurrence=0):
        """Returns the index of a channel group with the given name.
        
        Parameters
        ----------
        channel_group_name : str
            The name of the channel group.
        occurrence : int, Optional
            Gives the nth occurrence of the channel group name. By default the first occurrence is returned.
        """
        if not isinstance(channel_group_name, str):
            raise TypeError("Only str is accepted as input channel_group_name.")
        list_len = -1
        try:
            chgn = [i
                    for i, chg in enumerate(self._xml_chgs)
                    if chg.findtext('name') == channel_group_name]
            list_len = len(chgn)

            return chgn[occurrence]
        except IndexError:
            if list_len == 0:
                raise ValueError("Channel group name {0} does not exist".format(channel_group_name))
            else:
                raise IndexError(
                    "The channel group name {0} does only occur {1} time(s)".format(channel_group_name, str(list_len)))

    def no_channel_groups(self):
        """Returns the total number of channel groups.
        """
        return len(self._xml_chgs)

    def no_channels(self, channel_group):
        """Returns the total number of channels inside the given channel group.

        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        """
        if isinstance(channel_group, str):
            return len(OpenFile._get_usi_from_txt(list(
                filter(lambda x: x.findtext('name') == channel_group, self._xml_chgs))[0].findtext('channels')))
        elif isinstance(channel_group, int):
            if len(self._xml_chgs) <= channel_group or channel_group < -len(self._xml_chgs):
                raise IndexError('Channel group {0} out of range'.format(channel_group))

            return len(OpenFile._get_usi_from_txt(self._xml_chgs[channel_group].findtext('channels')))
        else:
            raise TypeError('Unsupported channel_group type')

    def __getitem__(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise IndexError(key)
            channel_group, channel = key

            if (isinstance(channel_group, str) or isinstance(channel_group, int)) and (isinstance(channel, str) or isinstance(channel, int)):
                return self.channel(channel_group, channel)
            else:
                raise TypeError('Unsupported parameter type.')
        elif isinstance(key, int) or isinstance(key, str):
            return self[0, key]  # Use channel_group 0
        else:
            raise TypeError("Unsupported parameter type.")

    def __len__(self):
        return self.no_channel_groups()

    def __repr__(self):
        return ''.join(['NI TDM-TDX file\n',
                        'TDM Path: ', os.path.join(self._folder, self._tdm_filename),
                        '\nTDX Path: ', self._tdx_path, '\n',
                        'Number of Channelgroups: ', str(self.no_channel_groups()), '\n',
                        'Channel Length: ', str(len(self))])

