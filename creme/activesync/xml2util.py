# -*- coding: utf-8 -*-
############################################################################
# XML2UTILS.py
#
# Common XML handy functions used across modules (note these are libxml2
# utilities, not DOM utilities - factored out from conversions.py
#
# Dr J A Gow 15/4/2007
#
############################################################################

import libxml2
#import libxslt

### libxml2 utility functions ###

def FindChildNode(node, name):
	child = node.children
	while child != None:
		if child.name == name:
			return child
		child = child.next
	return None

def GetNodeValue(node):
	if node is None:
		return ""
	else:
		return str(node.content).strip()

def GetNodeAttr(node,attr):
	p=node.hasProp(attr)
	if p:
		return str(p.content).strip()
	else:
		return None

def GetNodeOnLevel(parent, level):
	while level > 0:
		if parent.children != None:
        		for el in parent.children:
            			if el.type == "element":
                			parent = el
                			level -= 1
                			if level > 0:
                    				break
                			else:
                    				return el
		else:
			return None


### libxslt utility functions ###

#def ExtractContexts(ctx):
#	parser_ctx = libxslt.xpathParserContext(_obj=ctx).context()
#	transform_ctx = parser_ctx.transformContext()
#	return parser_ctx, transform_ctx
