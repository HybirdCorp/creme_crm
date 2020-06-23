# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

LF = '\x0a'
# CR = '\x0d'
# FF = '\x0c'
# EC = '\x1b'
# PA = '\x80'
EURO = '\x84'

# SMS_ENCODING_GSM_03_38 = ''.join(
#    (
#     #0     1      2      3      4      5      6      7      8      9      A      B      C      D      E      F           # NOQA
#     '\x00','?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   ' ',   LF,    '?',   FF,    CR,    '?',   '?',    #0  # NOQA
#     '?',   '?',   '?',   '?',   '?',   '?',   '?',  '?',   '?',   '?',   '?',   EC,    '?',   '?',   '?',   '?',     #1  # NOQA
#     ' ',   '!',   '"',   '#',   '$',   '%',   '&',   '\'',  '(',   ')',   '*',   '+',   ',',   '-',   '.',   '/',    #2  # NOQA
#     '0',   '1',   '2',   '3',   '4',   '5',   '6',   '7',   '8',   '9',   ':',   ';',   '<',   '=',   '>',   '?',    #3  # NOQA
#     '@',   'A',   'B',   'C',   'D',   'E',   'F',   'G',   'H',   'I',   'J',   'K',   'L',   'M',   'N',   'O',    #4  # NOQA
#     'P',   'Q',   'R',   'S',   'T',   'U',   'V',   'W',   'X',   'Y',   'Z',   '[',   '\\',  ']',   '^',   '_',    #5  # NOQA
#     '\'',  'a',   'b',   'c',   'd',   'e',   'f',   'g',   'h',   'i',   'j',   'k',   'l',   'm',   'n',   'o',    #6  # NOQA
#     'p',   'q',   'r',   's',   't',   'u',   'v',   'w',   'x',   'y',   'z',   '{',   '|',   '}',   '~',   LF,     #7  # NOQA
#     PA,    '?',   '?',   '?',   EURO,  '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',    #8  # NOQA
#     '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',   '?',    #9  # NOQA
#     ' ',   '\xa1','\xa2','\xa3','\xa4','\xa5','\xa1','\xa7','"',   'C',   'a',   '<',   '!',   '-',   'R',   '-',    #A  # NOQA
#     'o',   '?',   '2',   '3',   '\'',  'u',   '?',   '.',   ',',   'i',   'o',   '>',   '?',   '?',   '?',   '\xbf', #B  # NOQA
#     'A',   'A',   'A',   'A',   '\xc4','\xc5','\xc6','\xc7','E',   '\xc9','E',   'E',   'I',   'I',   'I',   'I',    #C  # NOQA
#     '?',   '\xd1','O',   'O',   'O',   'O',   '\xd6','x',   '\xd8','U',   'U',   'U',   '\xdc','Y',   '?',   '\xdf', #D  # NOQA
#     '\xe0','a',   'a',   'a',   '\xe4','\xe5','\xe6','c',   '\xe8','\xe9','e',   'e',   '\xec','i',   'i',   'i',    #E  # NOQA
#     '?',   '\xf1','\xf2','o',   'o',   'o',   '\xf6','?',   '\xf8','\xf9','u',   'u',   '\xfc','y',   '?',   'y',    #F  # NOQA
#    ))

SMS_EXTENDED_CHARS = {
    '^':  '\x1b\x14',
    '{':  '\x1b\x28',
    '}':  '\x1b\x29',
    '\\': '\x1b\x2f',
    '[':  '\x1b\x3c',
    '~':  '\x1b\x3d',
    ']':  '\x1b\x3e',
    '|':  '\x1b\x40',
    EURO: '\x1b\x65',
}

SMS_MAX_LENGTH = 160


def gsm_encoded_content(content):
    # unicode_encoded = unicode(content, 'utf-8') if content.__class__ != unicode else content

    # print('0x%02x' % ord(char) for char in unicode_encoded)

    # Convert euro sign (allow iso convertion) and \n as \x7f
    # unicode_encoded = unicode_encoded.translate({0x20ac:0x84, 0x0a:0x7f})
    unicode_encoded = content.translate({0x20ac: 0x84, 0x0a: 0x7f})

    # print('0x%02x' % ord(char) for char in unicode_encoded)

    iso_encoded = unicode_encoded.encode('iso-8859-1')
    # gsm_encoded = iso_encoded.translate(SMS_ENCODING_GSM_03_38)

    for special_key, special_value in SMS_EXTENDED_CHARS.items():
        iso_encoded = iso_encoded.replace(special_key, special_value)

    return iso_encoded
