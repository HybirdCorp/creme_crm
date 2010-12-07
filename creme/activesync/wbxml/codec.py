###############################################################################
# CODEC.py
#
# Low-level WBXML codecs functions
#
# From original code by Jonny Lamb - updated for sync-engine use 27/1/2008 by
# Dr J A Gow.
#
###############################################################################

WBXML_SWITCH_PAGE   = 0x00
WBXML_END           = 0x01
WBXML_ENTITY        = 0x02
WBXML_STR_I         = 0x03
WBXML_LITERAL       = 0x04
WBXML_EXT_I_0       = 0x40
WBXML_EXT_I_1       = 0x41
WBXML_EXT_I_2       = 0x42
WBXML_PI            = 0x43
WBXML_LITERAL_C     = 0x44
WBXML_EXT_T_0       = 0x80
WBXML_EXT_T_1       = 0x81
WBXML_EXT_T_2       = 0x82
WBXML_STR_T         = 0x83
WBXML_LITERAL_A     = 0x84
WBXML_EXT_0         = 0xC0
WBXML_EXT_1         = 0xC1
WBXML_EXT_2         = 0xC2
WBXML_OPAQUE        = 0xC3
WBXML_LITERAL_AC    = 0xC4

EN_TYPE             = 1
EN_TAG              = 2
EN_CONTENT          = 3
EN_FLAGS            = 4
EN_ATTRIBUTES       = 5

EN_TYPE_STARTTAG    = 1
EN_TYPE_ENDTAG      = 2
EN_TYPE_CONTENT     = 3

EN_FLAGS_CONTENT    = 1
EN_FLAGS_ATTRIBUTES = 2

WBXML_DEBUG         = True

###############################################################################
# WBXMLDecoder
#
# EXPORTED
#
# This object is a generic WBXML decoder object - provide it with the binary 
# string to decode from and the DTD - and the XML can be extracted by calling
# the appropriate functions
#
###############################################################################

class WBXMLDecoder(object):
	
	# Decoder state
	
	dtd = None
	input = None

	version = None
	publicid = None
	publicstringid = None
	charsetid = None
	string_table = None
	
	tagcp = 0
	attrcp = 0
	
	unget_buffer = None

	log_stack = []

	def __init__(self, input, dtd):
        
		self.input = input
		self.dtd = dtd[0]

		self.version = self.GetByte()
		self.publicid = self.GetMBUInt()

		if self.publicid == 0:
			self.publicstringid = self.GetMBUInt()

		self.charsetid = self.GetMBUInt()
		self.string_table = self.GetStringTable()

	#
	# GetElement
	#
	# Pull down the element at this point in the WBXML stream
	#

	def GetElement(self):

		element = self.GetToken()

		if element.has_key(EN_TYPE):
			
			if (element[EN_TYPE] == EN_TYPE_STARTTAG):
				return element
			
			elif (element[EN_TYPE] == EN_TYPE_ENDTAG):
				return element
			
			elif (element[EN_TYPE] == EN_TYPE_CONTENT):

				while True:
					
					next = self.GetToken()
					
					if next == False:
						break
					
					elif next[EN_TYPE] == EN_CONTENT:
						element[EN_CONTENT] += next[EN_CONTENT]
					else:
						self.UngetElement(next)
						break;
				return element
		return False

	#
	# Peek
	#
	# Return the next element without changing the position in the
	# input byte stream.
	#

	def Peek(self):
		element = self.GetElement()
		self.UngetElement(element)

		return element

	#
	# GetElementStartTag
	#
	# Return the start tag for a given tag - or return false if no match
	#

	def GetElementStartTag(self, tag):
		element = self.GetToken()

		if element[EN_TYPE] == EN_TYPE_STARTTAG and element[EN_TAG] == tag:
			return element
		else:
			self.UngetElement(element)
			
		return False

	#
	# GetElementEndTag
	#
	# Return the end tag.
	#

	def GetElementEndTag(self):
		
		element = self.GetToken()

		if element[EN_TYPE] == EN_TYPE_ENDTAG:
			return element
		else:
			self.UngetElement(element)
			
		return False

	#
	# GetElementContent
	#
	# Return the content of an element
	#

	def GetElementContent(self):
		
		element = self.GetToken()

		if element[EN_TYPE] == EN_TYPE_CONTENT:
			return element
		else:
			self.UngetElement(element)

		return False

	#
	# GetToken
	#
	# Return the next token in the stream
	#

	def GetToken(self):
 
		if self.unget_buffer:
			element = self.unget_buffer
			self.unget_buffer = False
			return element

		el = self._GetToken()

		return el

	#
	# _GetToken
	#
	# INTERNAL
	#
	# Low level call to retrieve a token from the wbxml stream
	#

	def _GetToken(self):
		
		element = {}

		while True:
			byte = self.GetByte()

			if byte == None:
				break

			if byte == WBXML_SWITCH_PAGE:
				self.tagcp = self.GetByte()
				continue

			elif byte == WBXML_END:
				element[EN_TYPE] = EN_TYPE_ENDTAG
				return element

			elif byte == WBXML_ENTITY:
				entity = self.GetMBUInt()
				element[EN_TYPE] = EN_TYPE_CONTENT
				element[EN_CONTENT] = self.EntityToCharset(entity)
				return element

			elif byte == WBXML_STR_I:
				element[EN_TYPE] = EN_TYPE_CONTENT
				element[EN_CONTENT] = self.GetTermStr()
				return element

			elif byte == WBXML_LITERAL:
				element[EN_TYPE] = EN_TYPE_STARTTAG
				element[EN_TAG] = self.GetStringTableEntry(self.GetMBUInt())
				element[EN_FLAGS] = 0
				return element

			elif byte == WBXML_EXT_I_0 or \
				byte == WBXML_EXT_I_1 or \
				byte == WBXML_EXT_I_2:
				self.GetTermStr()
				continue

			elif byte == WBXML_PI:
				self.GetAttributes()
				continue

			elif byte == WBXML_LITERAL_C:
				element[EN_TYPE] = EN_TYPE_STARTTAG
				element[EN_TAG] = self.GetStringTableEntry(self.GetMBUInt())
				element[EN_FLAGS] = EN_FLAGS_CONTENT
				return element

			elif byte == WBXML_EXT_T_0 or \
				byte == WBXML_EXT_T_1 or \
				byte == WBXML_EXT_T_2:
				self.GetMBUInt()
				continue

			elif byte == WBXML_STR_T:
				element[EN_TYPE] = EN_TYPE_CONTENT
				element[EN_CONTENT] = self.GetStringTableEntry(self.GetMBUInt())
				return element

			elif byte == WBXML_LITERAL_A:
				element[EN_TYPE] = EN_TYPE_STARTTAG
				element[EN_TAG] = self.GetStringTableEntry(self.GetMBUInt())
				element[EN_ATTRIBUTES] = self.GetAttributes()
				element[EN_FLAGS] = EN_FLAGS_ATTRIBUTES
				return element

			elif byte == WBXML_EXT_0 or \
				byte == WBXML_EXT_1:
				continue

			elif byte == WBXML_OPAQUE:
				length = self.GetMBUInt()
				element[EN_TYPE] = EN_TYPE_CONTENT
				element[EN_CONTENT] = self.GetOpaque(length)
				return element

			elif byte == WBXML_LITERAL_AC:
				element[EN_TYPE] = EN_TYPE_STARTTAG
				element[EN_TAG] = self.GetStringTableEntry(self.GetMBUInt())
				element[EN_ATTRIBUTES] = self.GetAttributes()
				element[EN_FLAGS] = EN_FLAGS_ATTRIBUTES | EN_FLAGS_CONTENT
				return element

			else:
				element[EN_TYPE] = EN_TYPE_STARTTAG
				element[EN_TAG] = self.GetMapping(self.tagcp, byte & 0x3F)
				
				if byte & 0x80:
					flag1 = EN_FLAGS_ATTRIBUTES
				else:
					flag1 = 0

				if byte & 0x40:
					flag2 = EN_FLAGS_CONTENT
				else:
					flag2 = 0

				element[EN_FLAGS] = flag1 | flag2

				if byte & 0x80:
					element[EN_ATTRIBUTES] = self.GetAttributes()
					
				return element
		
		return element

	#
	# UngetElement
	#
	# Put it back if we do not use it
	#

	def UngetElement(self, element):
		
		if self.unget_buffer:
			pass

		self.unget_buffer = element

	#
	# GetAttributes
	#
	# Retrieve a list of attributes for a given tag
	#

	def GetAttributes(self):

		attributes = []
		attr = ''

		while True:
			byte = self.GetByte()

			if len(byte) == 0:
				break

			if byte == WBXML_SWITCH_PAGE:
				
				self.attrcp = self.GetByte()
				break

			elif byte == WBXML_END:
				
				if attr != '':
					attributes.append(self.SplitAttribute(attr))
				return attributes

			elif byte == WBXML_ENTITY:
				
				entity = self.GetMBUInt()
				attr += self.EntityToCharset(entity)
#				return element

			elif byte == WBXML_STR_I:
				
				attr += self.GetTermStr()
#				return element

			elif byte == WBXML_LITERAL:
				
				if attr != '':
					attributes.append(self.SplitAttribute(attr))
				attr = self.GetStringTableEntry(self.GetMBUInt())
#				return element

			elif byte == WBXML_EXT_I_0 or \
			     byte == WBXML_EXT_I_1 or \
			     byte == WBXML_EXT_I_2:
				
				self.GetTermStr()
				continue

			elif byte == WBXML_PI or \
			     byte == WBXML_LITERAL_C:
				
				return False

			elif byte == WBXML_EXT_T_0 or \
			     byte == WBXML_EXT_T_1 or \
			     byte == WBXML_EXT_T_2:
				
				self.GetMBUInt()
				continue

			elif byte == WBXML_STR_T:
				
				attr += self.GetStringTableEntry(self.GetMBUInt())
				return element

			elif byte == WBXML_LITERAL_A:
				
				return False

			elif byte == WBXML_EXT_0 or \
			     byte == WBXML_EXT_1 or \
			     byte == WBXML_EXT_2:

				continue

			elif byte == WBXML_OPAQUE:

				length = self.GetMBUInt()
				attr += self.GetOpaque(length)
				return element

			elif byte == WBXML_LITERAL_AC:
				return False

			else:
				
				if byte < 128:
					if attr != '':
						attributes.append(self.SplitAttribute(attr))
						attr = ''

				attr += self.GetMapping(self.attrcp, byte)
				break
					
		return attributes
	#
	# SplitAttribute
	#
	# Split attribute into name and content
	#

	def SplitAttribute(self, attr):


		pos = attr.find(chr(61))

		if pos:
			attribute = (attr[0:pos], attr[(pos+1):])
		else:
			attribute = (attr,None)

		return attribute

	#
	# GetTermStr
	#
	# Return a string up until the next null
	#

	def GetTermStr(self):

		str = ''
		while True:
			input = self.GetByte()

			if input == 0:
				break
			else:
				str += chr(input)
		return str

	#
	# GetOpaque
	#
	# Return up to len bytes from the input
	#

	def GetOpaque(self, len):
		return self.input.read(len)
	
	#
	# GetByte
	# 
	# Retrieve a byte from the input stream
	#

	def GetByte(self):
		
		ch = self.input.read(1)
		if len(ch) > 0:
			return ord(ch)
		else:
			return None

	#
	# GetMBUInt
	#
	# 

	def GetMBUInt(self):

		uint = 0

		while True:

			byte = self.GetByte()
			uint |= byte & 0x7f
			if byte & 0x80:
				uint = uint << 7
			else:
				break

		return uint

	#
	# GetStringTable
	#
	# Read and return the string table
	#

	def GetStringTable(self):
		
		string_table = ''

		length = self.GetMBUInt()

		if length > 0:
			string_table = self.input.read(length)

		return string_table

	#
	# GetMapping
	#
	# Interrogate the DTD for tag and namespace code pairs
	#

	def GetMapping(self, cp, id):
		
		if not self.dtd['codes'][cp] or not self.dtd['codes'][cp][id]:
			return False
		else:
			if self.dtd['namespaces'][cp]:
				return (self.dtd['namespaces'][cp],self.dtd['codes'][cp][id])
			else:
				return (None,self.dtd['codes'][cp][id])


###############################################################################
# WBXMLEncoder
#
# EXPORTED
#
# This object is a generic WBXML encoder object - parsing XML externally and
# calling the appropriate methods will build up a WBXML representation in the
# internal string
#
###############################################################################

class WBXMLEncoder(object):

	# Encoder globals

	_dtd = None
	_out = None

	_tagcp = None
	_attrcp = None

	log_stack = []

	#
	# Initialization
	#

	def __init__(self, output, dtd):

	        self._out = output
		self._dtd = dtd[1]
        	self._tagcp = 0
	        self._attrcp = 0
        	self._stack = []

	#
	# StartWBXML
	#
	# Write the initial WBXML header
	#

	def StartWBXML(self):

		# Content-Type: application/vnd.ms-sync.wbxml'

		self.OutByte(0x03)
		self.OutMBUInt(0x01)
		self.OutMBUInt(106)
		self.OutMBUInt(0x00)

	#
	# StartTag
	#
	# Call to create a new tag. Pass in a tuple of (ns,name) for tag.
	#

	def StartTag(self, tag, attributes=False, nocontent=False):

		stackelem = {}

		if not nocontent:
			stackelem['tag'] = tag
			stackelem['attributes'] = attributes
			stackelem['nocontent'] = nocontent
			stackelem['sent'] = False
			self._stack.append(stackelem)
		else:
			self._OutputStack()
			self._StartTag(tag, attributes, nocontent)

	#
	# EndTag
	#
	# Called at end of tag (only one with content)
	#

	def EndTag(self):

		stackelem = self._stack.pop()

		if stackelem['sent']:
			self._EndTag()

	#
	# Content
	#
	# Called to output tag content

	def Content(self, content):

		content = content.replace('\0', '')

		if 'x' + content == 'x':
			return
		
		self._OutputStack()
		self._Content(content)

	#
	# _OutputStack
	#
	# INTERNAL
	#
	# Spool all stacked tags to the output file.
	#

	def _OutputStack(self):
		
		for i in range(len(self._stack)):
			if not self._stack[i]['sent']:
				self._StartTag(self._stack[i]['tag'], self._stack[i]['attributes'], self._stack[i]['nocontent'])
				self._stack[i]['sent'] = True

	#
	# _StartTag
	#
	# INTERNAL
	#
	# Set up a new tag and handle the DTD mappings

	def _StartTag(self, tag, attributes = False, nocontent = False):
		
		mapping = self.GetMapping(tag)

		if self._tagcp != mapping['cp']:
			self.OutSwitchPage(mapping['cp'])
			self._tagcp = mapping['cp']

		code = mapping['code']
		if attributes and len(attributes) > 0:
			code |= 0x80

		if not nocontent:
			code |= 0x40

		self.OutByte(code)

		if code & 0x80:
			self.OutAttributes(attributes)

	#
	# _Content
	#
	# INTERNAL
	#
	# Send tag content to the file
	#

	def _Content(self, content):
		self.OutByte(WBXML_STR_I)
		self.OutTermStr(content)

	#
	# _EndTag
	#
	# INTERNAL
	#
	# Send end tag data to the file
	#

	def _EndTag(self):
		
	        self.OutByte(WBXML_END)

	#
	# OutByte
	#
	# Send a byte to the output stream

	def OutByte(self, byte):
        	self._out.write(chr(byte))

	#
	# OutMBUInt
	#
	# Send a multi byte value to the output stream
	#

	def OutMBUInt(self, uint):
		
		while True:
			byte = uint & 0x7f
			uint = uint >> 7

			if uint == 0:
				self.OutByte(byte)
				break
			else:
				self.OutByte(byte | 0x80)

	#
	# OutTermStr
	#
	# Send a null terminated string to the output stream

	def OutTermStr(self, content):

		self._out.write(content)
		self._out.write(chr(0))

	#
	# OutAttributes
	#
	# Send attributes to the stream (needs work)
	#

	def OutAttributes(self):
		self.OutByte(WBXML_END)

	#
	# OutSwitchPage
	#
	# Send a switch page command to the stream

	def OutSwitchPage(self, page):

		self.OutByte(WBXML_SWITCH_PAGE)
		self.OutByte(page)

	#
	# GetMapping
	#
	# Return a mapping between a tag and a DTD code pair
	# 'tag' is a tuple of (namespace,tagname)
	#

	def GetMapping(self, tag):
		
		mapping = {}
		
		ns,name = tag

		if ns:
			cp = self._dtd['namespaces'][ns]
		else:
			cp = 0

		code = self._dtd['codes'][cp][name]

		mapping['cp'] = cp
		mapping['code'] = code

		return mapping
