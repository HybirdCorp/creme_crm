# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

import xml.etree.ElementTree as ET

from django.utils.encoding import smart_str


def _element_iterator(tree):
    elements = [[tree]]
    deep_change = 0

    while elements:
        siblings = elements[-1]

        if siblings:
            element = siblings.pop(0)

            yield deep_change, element

            children = list(element.getchildren())
            if children:
                elements.append(children)
                deep_change = 1
                continue

            deep_change = 0
        else:
            elements.pop(-1)
            deep_change -= 1


class XMLDiffError(Exception):
    pass

class XMLDiff(object):
    def __init__(self, msg, node, root):
        self._msg  = msg
        self._node = node
        self._root = root

        node.text = ' -================= HERE : %s ==========%s' % (msg, node.text or '')
        #node.tail = ' -================= HERE : %s ==========%s' % (msg, node.tail or '')

    @property
    def short_msg(self):
        return '<%s> ===> %s' % (self._node.tag, self._msg)

    @property
    def long_msg(self):
        return ET.tostring(self._root, 'utf-8')

def xml_diff(xml1, xml2):
    """Get the FIRST difference between 2 XML documents.
    @param xml1 String representing the first XML document.
    @param xml2 String representing the second XML document.
    @return XMLDiff instance, or None if there is no difference.
    """
    if isinstance(xml1, unicode):
        xml1 = smart_str(xml1)

    if isinstance(xml2, unicode):
        xml2 = smart_str(xml2)

    XML = ET.XML

    try:
        tree1 = XML(xml1)
    except Exception as e:
        raise XMLDiffError('First document contains errors (base exception: %s)' % e)

    try:
        tree2 = XML(xml2)
    except Exception as e:
        raise XMLDiffError('Second document contains errors (base exception: %s)' % e)

    iter1 = _element_iterator(tree1)
    iter2 = _element_iterator(tree2)
    previous_node1 = None

    try:
        while True:
            #length comparison -------------------------------------------------
            try:
                deep_change1, node1 = iter1.next()
            except StopIteration:
                try:
                    deep_change2, node2 = iter2.next()
                except StopIteration:
                    raise
                else:
                    return XMLDiff(u'Additional sibling or child element in the second document',
                                   previous_node1, tree1
                                  )

            try:
                deep_change2, node2 = iter2.next()
            except StopIteration:
                return XMLDiff(u'Does not exist in second document', node1, tree1)

            #deep comparison ---------------------------------------------------
            if deep_change1 != deep_change2:
                if deep_change1 > deep_change2:
                    return XMLDiff(u'Does not exist', node1, tree1)

                return XMLDiff(u'Additional sibling or child element in the second document',
                               previous_node1, tree1
                              )

            #tag comparison ----------------------------------------------------
            if node1.tag != node2.tag:
                return XMLDiff(u'Tag "%s" != "%s"' % (node1.tag, node2.tag), node1, tree1)

            #attributes comparison ---------------------------------------------
            attrs1 = dict(node1.items())

            for attr_name2, attr_value2 in node2.items():
                attr_value1 = attrs1.pop(attr_name2, None)

                if attr_value1 is None:
                    return XMLDiff(u'Attribute "%s" is missing in the first document' % attr_name2,
                                   node1, tree1
                                  )

                if attr_value1 != attr_value2:
                    return XMLDiff(u'Attribute "%s": "%s" != "%s"' % (
                                        attr_name2, attr_value1, attr_value2),
                                   node1, tree1
                                  )
            if attrs1:
                return XMLDiff(u'Attribute "%s" is missing in the second document' % attrs1.keys()[0],
                                node1, tree1
                              )

            #text comparison ---------------------------------------------------
            text1 = node1.text or ''; text1 = text1.strip()
            text2 = node2.text or ''; text2 = text2.strip()

            if text1 != text2:
                return XMLDiff(u'Text "%s" != "%s"' % (text1, text2), node1, tree1)

            #tail comparison ---------------------------------------------------
            tail1 = node1.tail or ''; tail1 = tail1.strip()
            tail2 = node2.tail or ''; tail2 = tail2.strip()

            if tail1 != tail2:
                return XMLDiff(u'Tail "%s" != "%s"' % (tail1, tail2), node1, tree1)

            previous_node1 = node1
    except StopIteration:
        pass
