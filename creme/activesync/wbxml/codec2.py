# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

################################################################################
# Low-level WBXML codecs functions
WBXML_SWITCH_PAGE   = 0x00
WBXML_END           = 0x01
WBXML_ENTITY        = 0x02
WBXML_STR_I         = 0x03
WBXML_LITERAL       = 0x04
WBXML_EXT_I_0       = 0x40
WBXML_EXT_I_1       = 0x41
WBXML_EXT_I_2       = 0x42
WBXML_PI            = 0x43
WBXML_LITERAL_C     = 0x44
WBXML_EXT_T_0       = 0x80
WBXML_EXT_T_1       = 0x81
WBXML_EXT_T_2       = 0x82
WBXML_STR_T         = 0x83
WBXML_LITERAL_A     = 0x84
WBXML_EXT_0         = 0xC0
WBXML_EXT_1         = 0xC1
WBXML_EXT_2         = 0xC2
WBXML_OPAQUE        = 0xC3
WBXML_LITERAL_AC    = 0xC4

EN_TYPE             = 1
EN_TAG              = 2
EN_CONTENT          = 3
EN_FLAGS            = 4
EN_ATTRIBUTES       = 5

EN_TYPE_STARTTAG    = 1
EN_TYPE_ENDTAG      = 2
EN_TYPE_CONTENT     = 3

EN_FLAGS_CONTENT    = 1
EN_FLAGS_ATTRIBUTES = 2

WBXML_DEBUG         = True
################################################################################

import StringIO
from xml.etree.ElementTree import fromstring, XML, Element, _ElementInterface

#DEBUG = True
DEBUG = False

def _debuglog(*msg):
    if DEBUG:
        print msg

class WrongXMLType(Exception):
    pass

class WBXMLEncoder(object):
    """
        Encode xml to wbxml

        import doctest
        import creme.activesync.wbxml.codec2
        doctest.testmod(creme.activesync.wbxml.codec2)

        >>> from creme.activesync.wbxml.dtd import AirsyncDTD_Reverse
        >>> from xml.etree.ElementTree import XML
        >>> xml_str = '<?xml version="1.0" encoding="UTF-8"?><FolderSync xmlns="FolderHierarchy:"><SyncKey>0</SyncKey></FolderSync>'
        >>> xml = XML(xml_str)
        >>> encoder = WBXMLEncoder(AirsyncDTD_Reverse)
        >>> wbxml = '\x03\x01j\x00\x00\x07VR\x030\x00\x01\x01'
        >>> encoder.encode(xml) == wbxml
        True
    """
    def __init__(self, dtd):
        self._out    = StringIO.StringIO()
        self._dtd    = dtd
        self._tagcp  = 0
        self._attrcp = 0
        self._stack  = []

    def encode(self, to_encode):
        _debuglog('Enter encode')

        if isinstance(to_encode, (unicode, basestring)):
            self.xml = XML(to_encode)
        elif isinstance(to_encode, (_ElementInterface, )):
            self.xml = to_encode
        else:
            raise WrongXMLType("to_encode has to be an instance of unicode or basestring or xml.etree.ElementTree.Element not %s" % to_encode.__class__)

        #Writting the wbxml header
        self.write_header()

        #Writting the content from the root element
        self._encode_node(self.xml)

        #Get the stream value
        out = self._out.getvalue()
        
        self._out.close()
        
        _debuglog('Exit encode with', out)
        return out

    def get_ns(self, name):
        """Get the namespace"""
        _debuglog('Enter get_ns with', name)
        ns = None
        if name[0] == "{":
            ns, sep, tag = name[1:].rpartition("}")
        _debuglog('Exit get_ns with', ns)
        return ns

    def get_tag(self, tag, ns=None):
        _debuglog('Enter get_tag with tag:', tag," ns:", ns)
        _debuglog('Exit get_tag with ', tag.replace('{%s}' % ns, ''))
        return tag.replace('{%s}' % ns, '')

    def _encode_node(self, node):
        children  = node.getchildren()
        node_text = node.text

        ns  = self.get_ns(node.tag)
        tag = (ns, self.get_tag(node.tag, ns))

        if children or node_text:
            self.start_tag(tag, False, False)
        else:
            self.start_tag(tag, False, True)

        if children:
            for child in children:
                self._encode_node(child)
                
        elif node_text:
            self.content(node_text)

        if not children and not node_text:
            self._output_stack()
        else:
            self.end_tag()

    def write_byte(self, byte):
        """Send a byte to the output stream"""
        self._out.write(chr(byte))

    def write_multi_byte(self, bytes):
        """Send a multi byte value to the output stream"""
        while True:
            byte = bytes & 0x7f
            bytes = bytes >> 7

            if bytes == 0:
                self.write_byte(byte)
                break
            else:
                self.write_byte(byte | 0x80)

    def write_header(self):
        """Write the initial WBXML header"""
        _debuglog('write_header')
        self.write_byte(0x03)
        self.write_multi_byte(0x01)
        self.write_multi_byte(106)
        self.write_multi_byte(0x00)

    def start_tag(self, tag, attributes=False, nocontent=False):
        """Call to create a new tag. Pass in a tuple of (ns, name) for tag."""
        stackelem = {}

        _debuglog('Enter start_tag with tag:', tag, " attributes:", attributes, " nocontent:", nocontent)

        if not nocontent:
            stackelem['tag'] = tag
            stackelem['attributes'] = attributes
            stackelem['nocontent'] = nocontent
            stackelem['sent'] = False
            self._stack.append(stackelem)
            
        else:
            self._output_stack()
            self._start_tag(tag, attributes, nocontent)

        _debuglog('Exit start_tag')


    def _end_tag(self):
        """Send end tag data to the file"""
        _debuglog('_end_tag')
        self.write_byte(WBXML_END)

    def end_tag(self):
        """Called at end of tag (only one with content)"""


        stackelem = self._stack.pop()

        _debuglog('end_tag with stackelem:', stackelem)


        if stackelem['sent']:
            self._end_tag()

    def content(self, content):
        """Called to output tag content"""

        _debuglog("Enter content with content :", content)

        content = content.replace('\0', '')

        if 'x' + content == 'x':
            return

        self._output_stack()
        self._content(content)

        _debuglog("Exit content")

    def _output_stack(self):
        """Spool all stacked tags to the output file."""

        _debuglog("Enter _output_stack")

        for i in range(len(self._stack)):
            if not self._stack[i]['sent']:
                self._start_tag(self._stack[i]['tag'], self._stack[i]['attributes'], self._stack[i]['nocontent'])
                self._stack[i]['sent'] = True

        _debuglog("Exit _output_stack")


    def _start_tag(self, tag, attributes = False, nocontent = False):
        """Set up a new tag and handle the DTD mappings"""

        _debuglog("Enter _start_tag with:", "tag :",tag, " attributes :",attributes , " nocontent :", nocontent)

        mapping = self.get_mapping(tag)

        if self._tagcp != mapping['cp']:
            self.write_switch_page(mapping['cp'])
            self._tagcp = mapping['cp']

        code = mapping['code']
        if attributes and len(attributes) > 0:
            code |= 0x80

        if not nocontent:
            code |= 0x40

        self.write_byte(code)

        if code & 0x80:
            self.write_attributes(attributes)

        _debuglog("Exit _start_tag")

    def _content(self, content):
        """Send tag content to the file"""

        _debuglog("Enter _content with ", content)

        self.write_byte(WBXML_STR_I)
        self.write_null_str(content)

        _debuglog("Exit _content")

    def write_null_str(self, content):
        """Send a null terminated string to the output stream"""
        _debuglog("Enter write_null_str")
        self._out.write(content)
        self._out.write(chr(0))
        _debuglog("Exit write_null_str")

    def write_attributes(self):
        """Send attributes to the stream (needs work)"""
        _debuglog("Enter write_attributes")
        self.write_byte(WBXML_END)
        _debuglog("Exit write_attributes")

    def write_switch_page(self, page):
        """Send a switch page command to the stream"""

        _debuglog("Enter write_switch_page with page:", page)

        self.write_byte(WBXML_SWITCH_PAGE)
        self.write_byte(page)

        _debuglog("Exit write_switch_page")


    def get_mapping(self, tag):
        """Return a mapping between a tag and a DTD code pair
            'tag' is a tuple of (namespace,tagname)
        """
        _debuglog("Enter get_mapping with tag:", tag)
        mapping = {}

        ns, name = tag

        if ns:
            cp = self._dtd['namespaces'][ns]
        else:
            cp = 0

        code = self._dtd['codes'][cp][name]

        mapping['cp']   = cp
        mapping['code'] = code

        _debuglog("Exit get_mapping with mapping:", mapping)
        return mapping

################################################################################

class WBXMLDecoder(object):

    def __init__(self, dtd):
        pass

    def decode(self, to_decode):
        pass