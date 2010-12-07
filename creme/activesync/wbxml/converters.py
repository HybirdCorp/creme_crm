###############################################################################
# CONVERTERS.py
#
# Converter functions that use the low level wbxml codec to convert between
# libxml2 structures and wbxml strings - and vice versa.
#
# Dr J A Gow 27/1/2008
#
###############################################################################

import dtd 
import libxml2
import codec
import StringIO

###############################################################################
# _processNode
#
# INTERNAL
#
# Handy helper to allow us to recurse into an XML document structure and
# pluck out the juicy bits for WBXML conversion
#
###############################################################################

DEBUG = False
#DEBUG = True

def _debuglog(*msg):
    if DEBUG:
        print msg

def _processNode(node,encoder):
		
	_debuglog("processNode")
	
	if node.type == 'element':
	
		_debuglog("content flag:")
			
		nocontent = (node.children == None)
	
		# We have a tag. Handle attrs later
	
		_debuglog("pn: get namespace")
		_debuglog("node.ns():", str(node.ns()))

		ns=node.ns();
		_debuglog("pn: got namespace")
		if ns!=None:
			prefix = ns.content
		else:
			prefix = None
			
		tag = (prefix,str(node.name).strip())
		
		_debuglog("TAG ",tag)
		encoder.StartTag(tag,False,nocontent)
			
		# process the children
	
		if node.children != None:
			_processNode(node.children,encoder)
		
		if not nocontent:
			encoder.EndTag();
	
	# process node text content
			
	elif node.type == 'text':
		_debuglog("text node")
		encoder.Content(node.content)
	
	# process only tags for the moment

	if node.next != None:
		_debuglog("next node - ", node.next.type)
		_processNode(node.next,encoder)
		
	return

###############################################################################
# WBXMLToXML
#
# EXPORTED
#
# Taking a WBXML string as an argument, this function produces a libxml2 
# document structure corresponding to it.
#
###############################################################################

def WBXMLToXML(wbxml):
	
	# create our new document
	
	doc = libxml2.newDoc("1.0")
	
	# if we have no input, then just quit. But always return a valid
	# (but empty) document
	
	if wbxml==None or wbxml=='':
		return doc

	# first create a string file for the wbxml. We may take a slight
	# efficiency hit with this approach, however I like Jonny's original
	# architecture from codec.py of making the codec usable with anything
	# that has a read() and write() function. Amount of any efficiency
	# hit remains to be seen.
	
	wbxfile = StringIO.StringIO(wbxml)

	# create the decoder
	
	decoder = codec.WBXMLDecoder(wbxfile,dtd.AirsyncDTD)
	
	# and go do it
	
	curTag = None
	curNs = None

	while True:

		e=decoder.GetElement()

		if not e:
			break

		# Ok, check the element. We must first be looking for a start tag
		
		# check the element type:

		if e[codec.EN_TYPE] == codec.EN_TYPE_STARTTAG:

			ns,name = e[codec.EN_TAG]

			if curTag == None:
				curTag = doc.newChild(None,name,None)
			else:	
				curTag = curTag.newChild(None,name,None)

			if ns!=None:
				if curNs!=None:
					if curNs.name != ns:
						curNs = curTag.newNs(ns,None)
						curTag.setNs(curNs)
				else:
					curNs = curTag.newNs(ns,None)
					curTag.setNs(curNs)

			if e[codec.EN_FLAGS]&2:
				_debuglog("must get attrs")
			
			if  not (e[codec.EN_FLAGS]&1):
				curTag = curTag.parent

		elif e[codec.EN_TYPE] == codec.EN_TYPE_ENDTAG:
			if curTag:
				curTag = curTag.parent
			else:
				curTag = None
				_debuglog("error: no parent")

		elif e[codec.EN_TYPE] == codec.EN_TYPE_CONTENT:
			if curTag:
				curTag.addContent(e[codec.EN_CONTENT])
			else:
				_debuglog("error: no node")

	# and we should have it.

	wbxfile.close()
	
	return doc


###############################################################################
# XMLToWBXML
#
# EXPORTED
#
# Going from an XML document, this function returns a WBXML string. The
# tree passed into the function should be a valid libxml2 document structure
#
###############################################################################

def XMLToWBXML(doc):
	
	# start at the root node
	
	root=doc.getRootElement()
	
	# get a string buffer for the wbxml output
	
	wbxml = StringIO.StringIO()
	
	# get the encoder
	_debuglog("get encoder")
	encoder = codec.WBXMLEncoder(wbxml,dtd.AirsyncDTD)

	# Send the headers and process the doc.

	_debuglog("write header")
	encoder.StartWBXML()
	_debuglog("enter processNode")
	_processNode(root,encoder)
	
	# recover the string and we're done
	
	s=wbxml.getvalue()
	wbxml.close()
	return s

	


