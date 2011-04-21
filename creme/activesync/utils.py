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
import os
import random
import base64

from PIL import Image

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.files.base import File


DEFAULT_CHUNK_SIZE = File.DEFAULT_CHUNK_SIZE
KNOW_BASE64_INCREASE = 1.33


def generate_id():
    w1 = random.randint(0x0, 0xFFFF)
    w2 = random.randint(0x0, 0xFFFF)
    return (w1 << 16) | w2

def generate_guid():
    d1 = random.randint(0, 0xFFFFFFFF)
    d2 = random.randint(0, 0xFFFF)
    d3 = random.randint(0, 0xFFFF)
    d4 = []
    for i in range(8):
        d4.append(random.randint(0, 0xFF))

    guid = "%08X%04X%04X" % (d1, d2, d3)
    for i in xrange(len(d4)):
        guid += "%02X" % d4[i]

    return guid

def generate_guid2():
    d1 = random.randint(0, 0xFFFFFFFF)
    d2 = random.randint(0, 0xFFFF)
    d3 = random.randint(0, 0xFFFF)
    d4 = []
    for i in range(8):
        d4.append(random.randint(0, 0xFF))

    guid = "{%08X-%04X-%04X-" % (d1, d2, d3)
    for i in xrange(len(d4)):
        guid += "%02X" % d4[i]
        if i == 1:
            guid += "-"
    guid += "}"

    return guid

def b64_encode_file(file_path):
    """Get a file path
    Returns (len(b64encoded file), file in b64)
    """
    encoded = StringIO()
    with open(file_path) as f:
        for ch in f.read(DEFAULT_CHUNK_SIZE):
            encoded.write(base64.b64encode(ch))

    value = encoded.getvalue()
    len_encoded = len(value)
    
    encoded.close()

    return (len_encoded, value)


def b64_from_pil_image(im, quality=75, reduce_by=1,  out_format='JPEG'):
    """Get a PIL Image
    Returns (image content in base64), image content in base64)
    """
    img_content = StringIO()
    width, height = im.size

    im.thumbnail((width*reduce_by, height*reduce_by))
    im.save(img_content, out_format, quality=quality)

    content = base64.b64encode(img_content.getvalue())
    content_size = len(content)
    img_content.close()
    return (content_size, content)


def get_b64encoded_img_of_max_weight(image_file_path, max_weight):
    """
        Get an image file path and max weight (in bytes)
        Returns base64 encoded string of an image file with weight < max_weight
    """

    im = Image.open(image_file_path)

    file_size = os.path.getsize(image_file_path)
    
    if file_size*KNOW_BASE64_INCREASE <= max_weight:
        content_size, content = b64_encode_file(image_file_path)

        if content_size <= max_weight:
            return content

    #TODO: Optimize the end image by a better non-linear reduction, quality, ...
    content_size, content = b64_from_pil_image(im, reduce_by=.5)
    while content_size > max_weight:
        content_size, content = b64_from_pil_image(im, reduce_by=.5)

    return content

