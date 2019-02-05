# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019  Hybird
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


def smart_split(s):
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
