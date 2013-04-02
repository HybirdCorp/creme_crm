###############################################################################
# __init__.py
#
#
# Initialize WBXML converter package
#
# Dr J A Gow 28/1/2008
#
###############################################################################

import dtd

dtd.InitializeDTD()

from .codec import WBXMLEncoder, WBXMLDecoder, WrongXMLType, WrongWBXMLType, prettify