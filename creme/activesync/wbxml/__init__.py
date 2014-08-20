###############################################################################
# __init__.py
#
#
# Initialize WBXML converter package
#
# Dr J A Gow 28/1/2008
#
###############################################################################

from .dtd import InitializeDTD

InitializeDTD()

from .codec import WBXMLEncoder, WBXMLDecoder, WrongXMLType, WrongWBXMLType, prettify
