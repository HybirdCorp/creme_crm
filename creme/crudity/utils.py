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

import base64
import re
import htmlentitydefs
import struct
import uuid

html_mark = re.compile(r"""(?P<html>(</|<!|<|&lt;)[-="' ;/.#:@\w]*(>|/>|&gt;))""")

def get_unicode_decoded_str(content, encodings):
    for encoding in encodings:
        try:
            return unicode(content, encoding) if not isinstance(content, unicode) else content
        except:
            continue

    return u"".join(i if ord(i) < 128 else '?' for i in content)

def strip_html_(html_content):
    is_html = True
    while is_html:
        reg = re.search(html_mark, html_content)
        if reg:
            html_content = html_content.replace(reg.groupdict().get('html'), '')
        else:
            is_html = False

    return html_content

def unescape(text):
   """Removes HTML or XML character references
      and entities from a text string.
      keep &amp;, &gt;, &lt; in the source code.
   from Fredrik Lundh
   http://effbot.org/zone/re-sub.htm#unescape-html
   """
   def fixup(m):
      text = m.group(0)
      if text[:2] == "&#":
         # character reference
         try:
            if text[:3] == "&#x":
               return unichr(int(text[3:-1], 16))
            else:
               return unichr(int(text[2:-1]))
         except ValueError:
#            print "erreur de valeur"
            pass
      else:
         # named entity
         frag = text[1:-1]
         try:
            if frag == "amp":
               text = "&amp;amp;"
            elif frag == "gt":
               text = "&amp;gt;"
            elif frag == "lt":
               text = "&amp;lt;"
            else:
               text = unichr(htmlentitydefs.name2codepoint[frag])
         except KeyError:
            pass
      return text # leave as is
   return re.sub("&#?\w+;", fixup, text)

def strip_html(text):
    """
    http://effbot.org/zone/re-sub.htm#strip-html
    """
    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
#            import htmlentitydefs
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)

def generate_guid_for_field(urn, model, field_name):
    return "{%s}" % str(uuid.uuid5(uuid.NAMESPACE_X500, str('%s.%s.%s' % (urn, model._meta.object_name, field_name)) )).upper()

def decode_b64binary(blob_b64):
    """Decode base64binary encoded files (Usually found in xsd:base64Binary http://www.w3.org/TR/xmlschema-2/#base64Binary)
        @returns file name
        @returns decoded content (a string with binaries data)
    """
    blob_str = base64.decodestring(blob_b64)
    blob_str_len = len(blob_str)

    header, filesize, filename_len, rest  = struct.unpack('16sII%ss' % (blob_str_len - 16 - 2 * 4), blob_str)
    filename_len *= 2

    header, filesize, filename_len, filename, blob  = struct.unpack('16sII%ss%ss' % (filename_len, (blob_str_len - 16 - 2 * 4 - filename_len)), blob_str)

    filename = "".join([unichr(i) for i in struct.unpack('%sh' % (len(filename)/2), filename) if i > 0])
    filename = str(filename.encode('utf8'))
    return filename, blob


