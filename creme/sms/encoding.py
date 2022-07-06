################################################################################
#
# Copyright (c) 2009-2022 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

LF = b'\x0a'  # XX: not used ?!
# CR = '\x0d'
# FF = '\x0c'
# EC = '\x1b'
# PA = '\x80'
EURO = b'\x84'

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
    b'^':  b'\x1b\x14',
    b'{':  b'\x1b\x28',
    b'}':  b'\x1b\x29',
    b'\\': b'\x1b\x2f',
    b'[':  b'\x1b\x3c',
    b'~':  b'\x1b\x3d',
    b']':  b'\x1b\x3e',
    b'|':  b'\x1b\x40',
    EURO: b'\x1b\x65',
}
SMS_MAX_LENGTH = 160


def gsm_encoded_content(content):
    # print('0x%02x' % ord(char) for char in unicode_encoded)

    # Convert euro sign (allow ISO conversion) and \n as \x7f
    unicode_encoded = content.translate({
        0x20ac: 0x84,  # € => '\x84'
        0x0a: 0x7f,    # \n => '\x7f'
    })

    # print('0x%02x' % ord(char) for char in unicode_encoded)

    iso_encoded = unicode_encoded.encode('iso-8859-1')
    # gsm_encoded = iso_encoded.translate(SMS_ENCODING_GSM_03_38)

    for special_key, special_value in SMS_EXTENDED_CHARS.items():
        iso_encoded = iso_encoded.replace(special_key, special_value)

    return iso_encoded
