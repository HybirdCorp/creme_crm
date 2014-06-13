# -*- coding: utf-8 -*-

################################################################################
#    This file is a modified version of codec.py from SynCE project
#    Original file located at http://synce.svn.sourceforge.net/viewvc/synce/trunk/sync-engine/SyncEngine/wbxml/codec.py
################################################################################

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#
#    Copyright (c) 2006 Ole André Vadla Ravnås <oleavr@gmail.com>
#    Copyright (c) 2007 Dr J A Gow <J.A.Gow@furrybubble.co.uk>
#    Copyright (C) 2009-2014  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging
import StringIO
from xml.etree.ElementTree import XML, Element, ElementTree, _ElementInterface #SubElement, tostring, fromstring


logger = logging.getLogger(__name__)

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

#WBXML_DEBUG         = False
################################################################################
# Pretty printing util found on http://www.doughellmann.com/PyMOTW/xml/etree/ElementTree/create.html
def prettify(elem):
    """Return a pretty-printed XML string for the Element (etree._ElementInterface).
    """
    #from xml.etree import ElementTree
    from xml.dom import minidom

    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
################################################################################

#DEBUG = True
#DEBUG = WBXML_DEBUG


#def _debuglog(*msg):
    #if DEBUG:
        #print msg

class WrongXMLType(Exception):
    pass

class WrongWBXMLType(Exception):
    pass

class WBXMLEncoder(object):
    """
        Encode xml to wbxml

        import doctest
        import activesync.wbxml.codec2
        doctest.testmod(activesync.wbxml.codec2)

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
        self._dtd    = dtd

    def encode(self, to_encode):
        logger.debug('Enter encode')

        self._out    = StringIO.StringIO()
        self._tagcp  = 0
        self._attrcp = 0
        self._stack  = []

        if isinstance(to_encode, basestring):
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

        logger.debug('Exit encode with %s', out)
        return out

    def get_ns(self, name):
        """Get the namespace"""
        logger.debug('Enter get_ns with %s', name)
        ns = None
        if name[0] == "{":
            ns, sep, tag = name[1:].rpartition("}")
        logger.debug('Exit get_ns with %s', ns)
        return ns

    def get_tag(self, tag, ns=None):
        logger.debug('Enter get_tag with tag="%s" ns=%s', tag, ns)
        logger.debug('Exit get_tag with %s', tag.replace('{%s}' % ns, '')) #TODO: variable for tag.replace(...)
        return tag.replace('{%s}' % ns, '')

    def _encode_node(self, node):
        #children  = node.getchildren()
        children  = list(node)
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
        logger.debug('write_header')
        self.write_byte(0x03)
        self.write_multi_byte(0x01)
        self.write_multi_byte(106)
        self.write_multi_byte(0x00)

    def start_tag(self, tag, attributes=False, nocontent=False):
        """Call to create a new tag. Pass in a tuple of (ns, name) for tag."""
        stackelem = {}

        logger.debug('Enter start_tag with tag="%s" attributes=%s nocontent=%s', tag, attributes, nocontent)

        if not nocontent:
            stackelem['tag'] = tag
            stackelem['attributes'] = attributes
            stackelem['nocontent'] = nocontent
            stackelem['sent'] = False
            self._stack.append(stackelem)

        else:
            self._output_stack()
            self._start_tag(tag, attributes, nocontent)

        logger.debug('Exit start_tag')

    def _end_tag(self):
        """Send end tag data to the file"""
        logger.debug('_end_tag')
        self.write_byte(WBXML_END)

    def end_tag(self):
        """Called at end of tag (only one with content)"""
        stackelem = self._stack.pop()

        logger.debug('end_tag with stackelem: %s', stackelem)

        if stackelem['sent']:
            self._end_tag()

    def content(self, content):
        """Called to output tag content"""
        logger.debug("Enter content with content: %s", content)

        content = content.replace('\0', '')

        if 'x' + content == 'x':
            return

        self._output_stack()
        self._content(content)

        logger.debug("Exit content")

    def _output_stack(self):
        """Spool all stacked tags to the output file."""
        logger.debug("Enter _output_stack")

        for i in range(len(self._stack)):
            if not self._stack[i]['sent']:
                self._start_tag(self._stack[i]['tag'], self._stack[i]['attributes'], self._stack[i]['nocontent'])
                self._stack[i]['sent'] = True

        logger.debug("Exit _output_stack")

    def _start_tag(self, tag, attributes=False, nocontent=False):
        """Set up a new tag and handle the DTD mappings"""
        logger.debug('Enter _start_tag with tag="%s" attributes=%s nocontent=%s', tag, attributes, nocontent)

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

        logger.debug("Exit _start_tag")

    def _content(self, content):
        """Send tag content to the file"""
        logger.debug("Enter _content with %s", content)

        self.write_byte(WBXML_STR_I)
        self.write_null_str(content)

        logger.debug("Exit _content")

    def write_null_str(self, content):
        """Send a null terminated string to the output stream"""
        logger.debug("Enter write_null_str")
        self._out.write(content)
        self._out.write(chr(0))
        logger.debug("Exit write_null_str")

    def write_attributes(self):
        """Send attributes to the stream (needs work)"""
        logger.debug("Enter write_attributes")
        self.write_byte(WBXML_END)
        logger.debug("Exit write_attributes")

    def write_switch_page(self, page):
        """Send a switch page command to the stream"""
        logger.debug("Enter write_switch_page with page: %s", page)

        self.write_byte(WBXML_SWITCH_PAGE)
        self.write_byte(page)

        logger.debug("Exit write_switch_page")

    def get_mapping(self, tag):
        """Return a mapping between a tag and a DTD code pair
            'tag' is a tuple of (namespace,tagname)
        """
        logger.debug('Enter get_mapping with tag="%s"', tag)
        mapping = {}

        ns, name = tag

        if ns: #TODO cp = .. if .. else ..
            cp = self._dtd['namespaces'][ns]
        else:
            cp = 0

        code = self._dtd['codes'][cp][name]

        mapping['cp']   = cp
        mapping['code'] = code

        logger.debug("Exit get_mapping with mapping: %s", mapping)
        return mapping

################################################################################

class WBXMLDecoder(object):
    """
        Decode wbxml to xml

        import doctest
        import activesync.wbxml.codec2
        doctest.testmod(activesync.wbxml.codec2)

        >>> from creme.activesync.wbxml.dtd import AirsyncDTD_Forward
        >>> from xml.etree.ElementTree import tostring, XML
        >>> xml_str = '<?xml version="1.0" encoding="UTF-8"?><FolderSync xmlns="FolderHierarchy:"><SyncKey>0</SyncKey></FolderSync>'
        >>> wbxml   = '\x03\x01j\x00\x00\x07VR\x030\x00\x01\x01'
        >>> decoder = WBXMLDecoder(AirsyncDTD_Forward)
        >>> tostring(decoder.decode(wbxml)) == tostring(XML(xml_str))
        True
    """

    def __init__(self, dtd):
        self._dtd   = dtd

    def _decode(self, to_decode):
        self.tagcp  = 0
        self.attrcp = 0
        self.unget_buffer = None

        self.input    =  StringIO.StringIO(to_decode)
        self.version  = self.get_byte()
        self.publicid = self.get_mbuint()

        if self.publicid == 0:
            self.publicstringid = self.get_mbuint()

        self.charsetid    = self.get_mbuint()
        self.string_table = self.get_string_table()

    def _format_name(self, name, ns):
        return "%s%s" % ("{%s}" % ns if ns is not None else "", name)

    def decode(self, to_decode):
        if to_decode in (None, ''):
            raise WrongWBXMLType(u"Empty wbxml is invalid")

        self._decode(to_decode)
        root   = None
        curTag = None

        _format_name = self._format_name

        while True:
            e = self.get_element()

            if not e:
                break

            if e[EN_TYPE] == EN_TYPE_STARTTAG:
                ns, name = e[EN_TAG]

                if root is None:
                    root = curTag = Element(_format_name(name, ns))
                    root.parent = None

                else:
                    node = Element(_format_name(name, ns))
                    node.parent = curTag#ElementTree doesn't store the parent..
                    curTag.append(node)
                    curTag = node

                if e[EN_FLAGS]&2:
                    logger.debug("must get attrs, %s", e[EN_FLAGS]&2)#WTF?

                if not (e[EN_FLAGS]&1):
                    curTag = curTag.parent

            elif e[EN_TYPE] == EN_TYPE_ENDTAG:
                curTag = curTag.parent if curTag is not None else None
#                if curTag is not None:
#                    curTag = curTag.parent
#                else:
#                    curTag = None
#                    logger.debug("error: no parent")


            elif e[EN_TYPE] == EN_TYPE_CONTENT and curTag is not None:
                curTag.text = e[EN_CONTENT]
#
#            elif e[EN_TYPE] == EN_TYPE_CONTENT:
#                if curTag is not None:
#                    curTag.text = e[EN_CONTENT]
#                else:
#                    logger.debug("error: no node")

        self.input.close()
        return root

    def get_element(self):
        """Pull down the element at this point in the WBXML stream"""
        element = self.get_token()

        if element.has_key(EN_TYPE):
            if element[EN_TYPE] == EN_TYPE_STARTTAG:
                return element
            elif element[EN_TYPE] == EN_TYPE_ENDTAG:
                return element
            elif element[EN_TYPE] == EN_TYPE_CONTENT:
                get_token     = self.get_token
                unget_element = self.unget_element

                while True:
                    next = get_token()

                    if next == False:#TODO: not next ?
                        break
                    elif next[EN_TYPE] == EN_CONTENT:
                        element[EN_CONTENT] += next[EN_CONTENT]
                    else:
                        unget_element(next)
                        break

                return element

        return False

    def peek(self):
        """Return the next element without changing the position in the
           input byte stream."""
        element = self.get_element()
        self.unget_element(element)

        return element

    def get_element_start_tag(self, tag):
        """Return the start tag for a given tag - or return false if no match"""
        element = self.get_token()

        if element[EN_TYPE] == EN_TYPE_STARTTAG and element[EN_TAG] == tag:
            return element
        else:
            self.unget_element(element)

        return False

    def get_element_end_tag(self):
        """Return the end tag."""
        element = self.get_token()

        if element[EN_TYPE] == EN_TYPE_ENDTAG:
            return element
        else:
            self.unget_element(element)

        return False

    def get_element_content(self):
        """Return the content of an element"""
        element = self.get_token()

        if element[EN_TYPE] == EN_TYPE_CONTENT:
            return element
        else:
            self.unget_element(element)

        return False

    def get_token(self):
        """Return the next token in the stream"""
        if self.unget_buffer:
            element           = self.unget_buffer
            self.unget_buffer = False
            return element

        el = self._get_token()

        return el

    def _get_token(self):
        """Low level call to retrieve a token from the wbxml stream"""
        element = {}

        get_attributes = self.get_attributes
        get_byte       = self.get_byte
        get_mbuint     = self.get_mbuint
        get_term_str   = self.get_term_str
        get_opaque     = self.get_opaque
        get_mapping    = self.get_mapping

        while True:
            byte = get_byte()

            if byte == None:
                break

            if byte == WBXML_SWITCH_PAGE:
                self.tagcp = get_byte()
                continue

            elif byte == WBXML_END:
                element[EN_TYPE] = EN_TYPE_ENDTAG
                return element

            elif byte == WBXML_ENTITY:
                entity              = get_mbuint()
                element[EN_TYPE]    = EN_TYPE_CONTENT
                #This function doesn't seem defined neither in original code nor in Z-push implementation
                #Active sync doesn't need this part ???
                element[EN_CONTENT] = self.EntityToCharset(entity)
                return element

            elif byte == WBXML_STR_I:
                element[EN_TYPE]    = EN_TYPE_CONTENT
                element[EN_CONTENT] = get_term_str()
                return element

            elif byte == WBXML_LITERAL:
                element[EN_TYPE]  = EN_TYPE_STARTTAG
                element[EN_TAG]   = self.GetStringTableEntry(get_mbuint())
                element[EN_FLAGS] = 0
                return element

            elif byte in (WBXML_EXT_I_0, WBXML_EXT_I_1, WBXML_EXT_I_2):
                get_term_str()
                continue

            elif byte == WBXML_PI:
                get_attributes()
                continue

            elif byte == WBXML_LITERAL_C:
                element[EN_TYPE]  = EN_TYPE_STARTTAG
                element[EN_TAG]   = self.GetStringTableEntry(get_mbuint())
                element[EN_FLAGS] = EN_FLAGS_CONTENT
                return element

            elif byte in (WBXML_EXT_T_0, WBXML_EXT_T_1, WBXML_EXT_T_2):
                get_mbuint()
                continue

            elif byte == WBXML_STR_T:
                element[EN_TYPE]    = EN_TYPE_CONTENT
                element[EN_CONTENT] = self.GetStringTableEntry(get_mbuint())
                return element

            elif byte == WBXML_LITERAL_A:
                element[EN_TYPE]       = EN_TYPE_STARTTAG
                element[EN_TAG]        = self.GetStringTableEntry(get_mbuint())
                element[EN_ATTRIBUTES] = get_attributes()
                element[EN_FLAGS]      = EN_FLAGS_ATTRIBUTES
                return element

            elif byte in (WBXML_EXT_0, WBXML_EXT_1):
                continue

            elif byte == WBXML_OPAQUE:
                length              = get_mbuint()
                element[EN_TYPE]    = EN_TYPE_CONTENT
                element[EN_CONTENT] = get_opaque(length)
                return element

            elif byte == WBXML_LITERAL_AC:
                element[EN_TYPE]       = EN_TYPE_STARTTAG
                element[EN_TAG]        = self.GetStringTableEntry(get_mbuint())
                element[EN_ATTRIBUTES] = get_attributes()
                element[EN_FLAGS]      = EN_FLAGS_ATTRIBUTES | EN_FLAGS_CONTENT
                return element

            else:
                element[EN_TYPE] = EN_TYPE_STARTTAG
                element[EN_TAG]  = get_mapping(self.tagcp, byte & 0x3F)

                if byte & 0x80: #TODO: flag1 = .. if .. else ..
                    flag1 = EN_FLAGS_ATTRIBUTES
                else:
                    flag1 = 0

                if byte & 0x40: #TODO: flag2 = .. if .. else ..
                    flag2 = EN_FLAGS_CONTENT
                else:
                    flag2 = 0

                element[EN_FLAGS] = flag1 | flag2

                if byte & 0x80:
                    element[EN_ATTRIBUTES] = get_attributes()

                return element

        return element

    def unget_element(self, element):
        """Put it back if we do not use it"""
        if self.unget_buffer:
            pass

        self.unget_buffer = element

    def get_attributes(self):
        """Retrieve a list of attributes for a given tag"""
        attributes = []
        attributes_append = attributes.append
        attr = ''

        get_byte        = self.get_byte
        split_attribute = self.split_attribute
        get_mbuint      = self.get_mbuint
        EntityToCharset = self.EntityToCharset
        get_term_str    = self.get_term_str
        get_opaque      = self.get_opaque
        get_mapping     = self.get_mapping

        while True:
            byte = get_byte()

            if len(byte) == 0:
                    break

            if byte == WBXML_SWITCH_PAGE: #TODO: use a dict instead of if elif elif etc...
                self.attrcp = get_byte()
                break
            elif byte == WBXML_END:
                if attr != '':
                    attributes_append(split_attribute(attr))
                return attributes
            elif byte == WBXML_ENTITY:
                entity = get_mbuint()
                attr  += EntityToCharset(entity)
#				return element
            elif byte == WBXML_STR_I:
                attr += get_term_str()
#				return element
            elif byte == WBXML_LITERAL:
                if attr != '':
                    attributes_append(split_attribute(attr))
                attr = self.GetStringTableEntry(get_mbuint())
#				return element
            elif byte in (WBXML_EXT_I_0, WBXML_EXT_I_1, WBXML_EXT_I_2):
                get_term_str()
                continue
            elif byte in (WBXML_PI, WBXML_LITERAL_C):
                return False
            elif byte in (WBXML_EXT_T_0, WBXML_EXT_T_1, WBXML_EXT_T_2):
                get_mbuint()
                continue
            elif byte == WBXML_STR_T:
                attr += self.GetStringTableEntry(get_mbuint())
#                    return element
            elif byte == WBXML_LITERAL_A:
                return False
            elif byte in (WBXML_EXT_0, WBXML_EXT_1, WBXML_EXT_2):
                continue
            elif byte == WBXML_OPAQUE:
                length = get_mbuint()
                attr  += get_opaque(length)
#                    return element
            elif byte == WBXML_LITERAL_AC:
                return False
            else:
                if byte < 128 and attr != '':
                    attributes_append(split_attribute(attr))
                    attr = ''

                attr += get_mapping(self.attrcp, byte)
                break

        return attributes

    def split_attribute(self, attr):
        """Split attribute into name and content"""
        pos = attr.find(chr(61))#TODO: chr(61) == '=' => Replace with?

        if pos:
            attribute = (attr[0:pos], attr[(pos+1):])
        else:
            attribute = (attr, None)

        return attribute #TODO: return ... if .. else ...

    def get_term_str(self):
        """Return a string up until the next null"""
        str = ''
        get_byte = self.get_byte
        while True:
            input = get_byte()

            if input == 0:
                break
            else:
                str += chr(input)
        return str #TODO: use join + genexpr + itertools.takewhile

    def get_opaque(self, len):
        """Return up to len bytes from the input"""
        return self.input.read(len)

    def get_byte(self):
        """Retrieve a byte from the input stream"""
        ch = self.input.read(1)
        if len(ch) > 0:
            return ord(ch)
        else:
            return None #TODO: useless

    def get_mbuint(self):
        uint = 0
        get_byte = self.get_byte
        while True:
            byte = get_byte()
            uint |= byte & 0x7f
            if byte & 0x80:
                uint = uint << 7
            else:
                break

        return uint

    def get_string_table(self):
        """Read and return the string table"""
        string_table = ''
        length = self.get_mbuint()

        if length > 0:
            string_table = self.input.read(length)

        return string_table

    def get_mapping(self, cp, id):
        """Interrogate the DTD for tag and namespace code pairs"""
        dtd = self._dtd
        dtd_codes_cp = dtd['codes'][cp]

        if not (dtd_codes_cp and dtd_codes_cp[id]):
            return False
        elif dtd['namespaces'][cp]:
            return (dtd['namespaces'][cp], dtd_codes_cp[id])
        else:
            return (None, dtd_codes_cp[id])
