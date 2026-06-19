################################################################################
#
# Copyright (c) 2019-2026 Hybird
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

from typing import Iterable

from django.utils.text import Truncator


def smart_split(s: str) -> list[str]:
    """Split a string using " character to keep words grouped.

    @param s: Input string.
    @return: List of strings (can be empty).

    >> smart_split('"foo \\"bar" baz')
    ['foo "bar', 'baz']
    """
    result = []

    def find_double_quote(sub, start=0):
        while True:
            dq_index = sub.find('"', start)

            if dq_index < 1 or sub[dq_index - 1] != '\\':
                break

            start = dq_index + 1

        return dq_index

    while True:
        dq_index1 = find_double_quote(s)

        if dq_index1 == -1:
            result.extend(s.replace('\\"', '"').split())
            break
        else:
            if dq_index1:  # There are some chars before the first double quote
                result.extend(s[:dq_index1].split())
                s = s[dq_index1:]

            # NB: the first char is a "
            dq_index2 = find_double_quote(s, start=1)

            if dq_index2 == -1:
                result.extend(s[1:].replace('\\"', '"').split())
                break
            else:
                token = s[1:dq_index2].replace('\\"', '"').strip()
                if token:
                    result.append(token)

                s = s[dq_index2 + 1:]

    return result


def multi_truncate(strings: Iterable[str], length: int) -> list[str]:
    """Returns (potentially) shorter strings in order to the global length
    does not exceed a given value.
    Strings are shortened in a way which tends to make them of the same length.

    @param strings: Strings to truncate.
    @param length: Global (maximum) length.
    @return: The truncated strings.

    >> multi_truncate(['123456', '12', '12'], 9)
    ['1234…', '12', '12']
    """
    class StringToTruncate:
        __slots__ = ('length', 'data')

        def __init__(self, s: str):
            self.length = len(s)
            self.data = s

    str_2_truncate = [StringToTruncate(s) for s in strings]
    total_len = sum(elt.length for elt in str_2_truncate)

    for i in range(max(0, total_len - length)):
        max_idx = -1
        max_value = -1

        for idx, elt in enumerate(str_2_truncate):
            if elt.length > max_value:
                max_value = elt.length
                max_idx = idx

        str_2_truncate[max_idx].length -= 1

    return [Truncator(elt.data).chars(elt.length) for elt in str_2_truncate]
