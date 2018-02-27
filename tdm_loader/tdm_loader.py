"""This module allows National Instruments TDM/TDX files to be accessed like
NumPy structured arrays.

It can be installed in the standard way::

    python setup.py install

Sample usage::

    import tdm_loader
    data_file = tdm_loader.OpenFile('filename.tdm')

Access a column by number::

    data_file[column_num]

Access a column by number::

    data_file.col(column_num)
    
Access a channel by channel group and channel index combination::
    
    data_file.channel(channel_group, channel)

Search for a column name.  A list of all column names that contain
``search_term`` and their indices will be returned::

    data_file.channel_search(search_term)
"""
import os.path
from struct import pack
import re
from xml.etree import cElementTree as etree
import xml.etree.ElementTree as ElementTree
from codecs import open
import warnings

import numpy as np
try:
    from matplotlib import pyplot as plt
    plt_available = True
except ImportError:
    plt_available = False


__all__ = ('OpenFile', 'ReadTDM')


# XML "QName" in the TDM file
# there has to be an easy way to determine this programmatically
QNAME = '{http://www.ni.com/Schemas/USI/1_0}'


# dictionary for converting from NI to NumPy datatypes
DTYPE_CONVERTERS = {'eInt8Usi':    'i1',
                    'eInt16Usi':   'i2',
                    'eInt32Usi':   'i4',
                    'eInt64Usi':   'i8',
                    'eUInt32Usi':  'u4',
                    'eUInt64Usi':  'u8',
                    'eFloat32Usi': 'f4',
                    'eFloat64Usi': 'f8'}


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
        self.tdm = ReadTDM(tdm_path, encoding = encoding)
        self.num_channels = self.tdm.num_channels

        if tdx_path == '':
            self._tdx_path = os.path.join(self._folder, self.tdm.tdx_filename)
        else:
            self._tdx_path = tdx_path
        self._open_tdx(self._tdx_path)
        self.channel_names = [chan.name for chan in self.tdm.channels]
        
        self._root = ElementTree.parse(tdm_path).getroot()
        
        self._name_to_indices = {self.channel_name(g, c): (g, c)
                                 for g in range(self.no_channel_groups())
                                 for c in range(self.no_channels(g))}

    def _open_tdx(self, tdx_path):
        """Open a TDX file.
        """
        try:
            self._tdx_fobj = open(tdx_path, mode='rb')
        except IOError:
            raise IOError('TDX file not found: ' + tdx_path)
        if self.tdm.exporter_type.find('National Instruments') >= 0:
            # data is in column first order
            # use the hacked solution for the memmap
            self._tdx_memmap = MemmapColumnFirst(self._tdx_fobj, self.tdm)
            self._memmap_type = 'Slow'
        elif self.tdm.exporter_type.find('LabVIEW') >= 0 or \
                self.tdm.exporter_type.find('Data Server') >= 0:
            # data is in row first order
            # use the NumPy memmap directly (almost)
            self._tdx_memmap = MemmapRowFirst(self._tdx_fobj, self.tdm)
            self._memmap_type = 'Fast'
        else:
            message = 'unknown exporter type: {exp_type}'
            raise IOError(message.format(exp_type=self.tdm.exporter_type))
            
    def _get_tdm_channel_usi(self, chg, ch, occurrence=0):
        """Returns the usi identifications of the given channel group and channel indices.
        """
        if isinstance(ch, str):
            _, cg, c = self.channel_search(ch)[occurrence]
            if cg != chg:
                raise IndexError("Channel {0} is not a member of channel group {1}".format(ch, chg))
            else:
                return self._get_tdm_channel_usi(chg, c)
        elif isinstance(ch, int):
            try:
                channel_usis = [x.text for x in self._root.findall(".//tdm_channelgroup/channels")][chg]
            except IndexError:
                raise IndexError("Channelgroup " + str(chg) + " out of range")

            try:
                ch_usi = re.findall("id\(\"(.+?)\"\)", channel_usis)[ch]
            except IndexError:
                raise IndexError("Channel " + str(ch) + " out of range")

            return ch_usi
        else:
            raise TypeError("The given parameter types are unsupported.")

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
                    
    def channel_search(self, search_term, return_column=False):
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
        found_terms : list of (str, int, int) or list of (str, int) (latter case for return_column = True)
            Returns the found channel names as tuple of full name and column index or channel group and channel indices
            depending on the value of return_column.
        """

        ch_names = [x.text for x in self._root.findall(".//tdm_channel/name")]
        search_term = str(search_term).upper().replace(' ', '')
        if search_term == "":
            found_terms = [name for name in ch_names if name is None]
        else:
            found_terms = [name for name in ch_names if name is not None
                           and name.upper().replace(' ', '').find(str(search_term)) >= 0]

        ind = []
        ind_chg_ch = []
        for name in found_terms:
            i = ch_names.index(name)
            ind.append((name, i))
            chg, ch = self.get_channel_indices(i)
            ind_chg_ch.append((name, chg, ch))
            ch_names[i] = ""
            
        if return_column:
            return ind
            
        return ind_chg_ch

    def plot_channels(self, x, ys):
        """Plot multiple channels.

        Parameters
        ----------
        x : (int, int)
            The channel group / channel indices combination of a single channel to plot on the x-axis.
        ys : list of (int, int)
            A list of multiple channel group / channel indices to plot on the y-axis.
        """
        if plt_available:
            plt.style.use("bmh")
            x_data = self.channel(x[0], x[1])
            y_data = [self.channel(y[0], y[1]) for y in ys]
            for i in range(len(ys)):
                plt.plot(x_data, y_data[i])
                
            plt.xlabel(self.channel_name(x[0], x[1]) + " (" + self.channel_unit(x[0], x[1]) + ")")
            plt.ylabel(self.channel_name(ys[0][0], ys[0][1]) + " (" + self.channel_unit(ys[0][0], ys[0][1]) + ")")
            plt.grid()
            plt.show()
        else:
            raise NotImplementedError(('matplotlib must be installed for '
                                       'plotting'))

    def col(self, column_number):
        """Returns a data column by its index number.
        """
        return self._tdx_memmap.col(column_number)
        
    def get_column_index(self, channel_group, channel, occurrence=0):
        """Returns the column index of given channel group and channel indices.
        
        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        """
        try:
            if channel_group < 0 or channel < 0:
                raise IndexError()

            ch_usi = self._get_tdm_channel_usi(channel_group, channel, occurrence=occurrence)
            local_column_usi = re.findall(
                "id\(\"(.+?)\"\)",
               self._root.findall(".//tdm_channel[@id='" + str(ch_usi) + "']/local_columns")[0].text)[0]
            data_usi = re.findall(
                "id\(\"(.+?)\"\)",
               self._root.findall(".//localcolumn[@id='" + str(local_column_usi) + "']/values")[0].text)[0]

            try:
                ext_id = self._root.findall(".//double_sequence/[@id='" + str(data_usi) + "']/values")[0].get('external')
            except IndexError:
                ext_id = self._root.findall(".//long_sequence/[@id='" + str(data_usi) + "']/values")[0].get(
                    'external')
            ch_number = int(re.findall("inc(\d+)", ext_id)[0])
        except IndexError:
            raise IndexError("Channel group " + str(channel_group) +
                             " or Channel " + str(channel) + " not found")
        
        return ch_number
        
    def get_channel_indices(self, column_index):
        """Returns the channel group and channel indices of given column index.
        
        Parameters
        ----------
        column_index : int
            The index of the column.
        """
        
        try:
            inc_usi = (self._root.findall(
                ".//double_sequence/values"
                + "[@external='inc" + str(column_index) + "']..") or
               self._root.findall(
                   ".//long_sequence/values"
                   + "[@external='inc" + str(column_index) + "'].."))[0].get("id")
                        
        except IndexError:
            raise IndexError("Column index " + str(column_index) + " out of range")
        
        try:
            lcol_usi = [cg.get("id") for cg in self._root.findall(".//localcolumn")
                        if cg is not None and inc_usi in cg.findall("values")[0].text][0]
            
            ch_usi = [cg.get("id") for cg in self._root.findall(".//tdm_channel")
                      if cg is not None and lcol_usi in cg.findall("local_columns")[0].text][0]

            chgs = [cg for cg in
                    self._root.findall(".//tdm_channelgroup") if cg is not None]
            
            chg_usi = ""
            for cg in chgs:
                ch = cg.findall("channels")
                if len(ch) > 0:
                    if ch_usi in ch[0].text:
                        chg_usi = cg.get("id")
                     
        except IndexError:
            raise IndexError(
                "Not able to associate the column index " + str(column_index) +
                "to channel group / channel. Likely the tdm file is malformed.")

        chgi = [x.attrib['id'] for x in self._root.findall(".//tdm_channelgroup")
                if len(x.findall("channels")) > 0].index(chg_usi)
        chg = [x for x in self._root.findall(".//tdm_channelgroup")
               if x.attrib['id'] == chg_usi][0]
        
        channel_usis = re.findall(
            "id\(\"(.+?)\"\)",
            [x.text for x in chg.findall("channels") if x is not None][0])
        ch = channel_usis.index(ch_usi)
        
        return chgi, ch
        
    def channel(self, channel_group, channel, occurrence=0, ch_occurrence=0):
        """Returns a data channel by its channel group and channel index.
        
        Parameters
        ----------
        channel_group : int or str
            The index or name of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        occurrence : int, Optional
            Gives the nth occurence of the channel group name. By default the first occurence is returned. 
            This parameter is only used when channel_group is given as a string.
        ch_occurrence : int, Optional
            Gives the nth occurence of the channel name. By default the first occurence is returned. 
            This parameter is only used when channel_group is given as a string.
        """
        
        if isinstance(channel_group, int):
            ch_number = self.get_column_index(channel_group, channel, occurrence=ch_occurrence)
        
            return self._tdx_memmap.col(ch_number)
        elif isinstance(channel_group, str):
            chg_ind = self.channel_group_index(channel_group, occurrence)
        
            return self.channel(chg_ind, channel, ch_occurrence=ch_occurrence)
        else:
            raise TypeError("The given channel group parameter type is unsupported")

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

    def channel_name(self, channel_group, channel):
        """Returns the name of the channel at given channel group and channel indices.
        
        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        """
        ch_usi = self._get_tdm_channel_usi(channel_group, channel)
        name = self._root.findall(".//tdm_channel[@id='" + str(ch_usi) + "']/name")[0].text

        if name is None:
            return ""
        else:
            return name
        
    def channel_unit(self, channel_group, channel):
        """Returns the unit of the channel at given channel group and channel indices.
        
        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        channel : int or str
            The index or name of the channel inside the group.
        """
        ch_usi = self._get_tdm_channel_usi(channel_group, channel)
        
        try:
            unit = self._root.findall(".//tdm_channel[@id='" + str(ch_usi) + "']/unit_string")[0].text
            if unit is None:
                return ""
            else:
                return unit
        except IndexError:
            return ""
        
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
            return [x.text for x in self._root.findall(".//tdm_channelgroup/name")][channel_group]
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
                    for i, x in enumerate(self._root.findall(".//tdm_channelgroup/name")) 
                    if x.text == channel_group_name]
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
        return len([x.text for x in self._root.findall(".//tdm_channelgroup/channels")])
        
    def no_channels(self, channel_group):
        """Returns the total number of channels inside the given channel group.

        Parameters
        ----------
        channel_group : int
            The index of the channel group.
        """
        if not isinstance(channel_group, int):
            raise TypeError("Only integer values allowed.")

        try:
            channel_usis = [x.text for x in self._root.findall(".//tdm_channelgroup/channels")][channel_group]
        except IndexError:
            raise IndexError("Channelgroup " + str(channel_group) + " out of range")
            
        return len(re.findall("id\(\"(.+?)\"\)", channel_usis))
           
    def close(self):
        """Close the file.
        """
        if hasattr(self, '_tdx_fobj'):
            self._tdx_fobj.close()

    def __getitem__(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise IndexError(key)
            channel_group, channel = key
            if isinstance(channel, int):
                return self.channel(channel_group, channel)
            else:
                raise TypeError(channel)
        elif isinstance(key, str):
            channel_group, channel = self._name_to_indices[key]
            if self.channel_names.count(key) > 1:
                warnings.warn("More than one channel with the name '{}'."
                              .format(key))
            return self.channel(channel_group, channel)
        elif isinstance(key, int):
            return self[0, key]  # Use channel_group 0
        else:
            raise TypeError("Unsupported parameter type.")

    def __len__(self):
        return self.num_channels

    def __del__(self):
        self.close()

    def __repr__(self):
        return ''.join(['NI TDM-TDX file\n',
                       'TDM Path: ', os.path.join(self._folder,
                                                  self._tdm_filename),
                       '\nTDX Path: ', self._tdx_path, '\n',
                       'Number of Channels: ',str(self.num_channels), '\n',
                       'Channel Length: ', str(len(self)), '\n',
                       'Memory Map Type: ', self._memmap_type])


class MemmapRowFirst(object):
    """Wrapper class for opening row-ordered TDX files.  This is only needed
    because NumPy memmap objects don't support [i,j] style indexing.
    """
    def __init__(self, fobj, tdm_file):
        self._memmap = np.memmap(fobj, dtype=tdm_file.dtype,
                                 mode='r').view(np.recarray)
        self._col2name = {}
        for i, channel in enumerate(tdm_file.channels):
            self._col2name[i] = channel.name

    def __getitem__(self, key):
        try:
            slices = key.indices(self.__len__()) # input is a slice object
            ind = range(slices[0], slices[1], slices[2])
            return self._memmap[ind]
        except AttributeError:
            pass
        try:
            return self._memmap[key] # input is a row number or column name
        except IndexError:
            return self._memmap[key[0]][key[1]] # input is a tuple

    def __len__(self):
        return len(self._memmap)

    def col(self, col_num):
        """Returns a data column by its index number.
        """
        return self._memmap[self._col2name[col_num]]


class MemmapColumnFirst(object):
    """Wrapper class for opening column-ordered TDX files.
    """
    def __init__(self, fobj, tdm_file):
        self._memmap = []
        self._name2col = {}
        self._col2name = {}
        self._num_channels = tdm_file.num_channels
        self._empty_row = np.recarray((1, ), tdm_file.dtype)
        self._empty_row[0] = 0 # initialize all items to zero
        channels = tdm_file.channels
        for i in range(len(channels)):
            self._name2col[channels[i].name] = i
            self._col2name[i] = channels[i].name
            self._memmap.append(np.memmap(fobj,
                                          offset=channels[i].byte_offset,
                                          shape=(channels[i].length, ),
                                          dtype=channels[i].dtype,
                                          mode='r').view(np.recarray))

    def __getitem__(self, key):
        try:
            slices = key.indices(self.__len__()) # input is a slice object
            ind = range(slices[0], slices[1], slices[2])
            row = self._empty_row.copy()
            row = np.resize(row, (len(ind), ))
            for rowi, i in enumerate(ind):
                for j in range(self._num_channels):
                    row[rowi][self._col2name[j]] = self._memmap[j][i]
            return row
        except AttributeError:
            pass
        try:
            return self._memmap[self._name2col[key]] # input is a column name
        except KeyError:
            pass
        try:
            return self._memmap[key[1]][key[0]] # input is a tuple
        except TypeError:
            pass
        row = self._empty_row.copy() # input is a row number
        for j in range(self._num_channels):
            row[0][self._col2name[j]] = self._memmap[j][key]
        return row[0]

    def __len__(self):
        return len(self._memmap[0])

    def col(self, col_num):
        """Returns a data column by its index number.
        """
        return self._memmap[col_num]


class ReadTDM(object):
    """Class for parsing and storing data from a .TDM file.

    Parameters
    ----------
    tdm_path : str
        The full path to the .TDM file.
    """
    def __init__(self, tdm_path, encoding='utf-8'):
        try:
            self._xmltree = etree.parse(tdm_path)
        except IOError:
            raise IOError('TDM file not found: ' + tdm_path)

        self._extract_file_props()
        self._extract_channel_props()

    def _extract_file_props(self):
        """Extracts file data from a TDM file.
        """
        self.exporter_type = self._xmltree.find(QNAME + 'documentation')\
                                                  .find(QNAME + 'exporter').text

        fileprops = self._xmltree.find(QNAME + 'include').find('file')
        self.tdx_filename = fileprops.get('url')
        self.byte_order = fileprops.get('byteOrder')
        if self.byte_order == 'littleEndian':
            self._endian = '<'
        elif self.byte_order == 'bigEndian':
            self._endian = '>'
        else:
            raise TypeError('Unknown endian format in TDM file')

    def _extract_channel_props(self):
        """Extracts channel data from a TDM file.
        """
        temp = self._xmltree.find(QNAME + 'include').find('file')
        blocks = temp.findall('block_bm')
        if len(blocks) == 0:
            blocks = temp.findall('block')
        channel_names = self._xmltree.find(QNAME + 'data').findall(
                                                                  'tdm_channel')
        self.num_channels = len(channel_names)
        assert(len(blocks) >= len(channel_names))

        formats = []
        names = []
        self.channels = []
        for i in range(self.num_channels):
            chan = ChannelData()
            chan.byte_offset = int(blocks[i].get('byteOffset'))
            chan.length = int(blocks[i].get('length'))
            try:
                chan.dtype = self._convert_dtypes(blocks[i].get('valueType'))
            except KeyError:
                raise TypeError(
                            'Unknown data type in TDM file. Channel ' + str(i))
            chan.name = channel_names[i].find('name').text
            if chan.name is None:
                chan.name = ''
            self.channels.append(chan)
            formats.append(chan.dtype)
            names.append(chan.name)

        #self.dtype = np.format_parser(formats, names, []).dtype
        #Names can not be cept here, otherwise importing of files with duplicate column names would not be possible
        self.dtype = np.format_parser(formats, [], []).dtype 

    def _convert_dtypes(self, tdm_dtype):
        """Convert a TDM data type to a NumPy data type.
        """
        # this will need to be adjusted to work with strings
        # "endianness" doesn't matter, so NumPy uses the '|' symbol
        return self._endian + DTYPE_CONVERTERS[tdm_dtype]


class ChannelData(object):
    """Stores data about a single data channel.
    """
    def __init__(self):
        self.name = u''
        self.dtype = u''
        self.length = 0
        self.byte_offset = 0

    def __repr__(self):
        return u''.join([u'name = ', self.name, u'\ndtype = ', self.dtype, u'\n',
                        u'length = ', str(self.length), '\n',
                        u'byte offset = ', str(self.byte_offset)])
