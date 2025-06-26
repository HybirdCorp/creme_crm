################################################################################
#
# Copyright (c) 2019-2025 Hybird
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
