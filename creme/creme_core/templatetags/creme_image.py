################################################################################
#
# Copyright (c) 2020-2025 Hybird
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
################################################################################

import logging

from django import template
from PIL.Image import open as open_img

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag
def image_size(*, path: str) -> tuple[int, int]:
    """Get the size of an image from its file path."""
    with open_img(path) as img:
        size = img.size

    return size


@register.simple_tag
def image_scale_to_frame(size: tuple[int, int],
                         width: int | None = None,
                         height: int | None = None,
                         ) -> tuple[int, int]:
    """Scale up/down an image's size to a given frame."""
    i_width, i_height = size

    if not i_width or not i_height:
        logger.warning(
            '{%% scale_to_frame %%} got a zero size: %s x %s ',
            i_width, i_height,
        )

        return 0, 0

    if width:
        w_ratio = width / i_width

        if height:
            h_ratio = height / i_height

            if w_ratio <= h_ratio:
                final_size = (width, round(i_height * w_ratio))
            else:
                final_size = (round(i_width * h_ratio), height)
        else:
            final_size = (width, round(i_height * w_ratio))
    elif height:
        final_size = (round(i_width * height / i_height), height)
    else:
        final_size = size  # TODO: build a new tuple ?

    return final_size
