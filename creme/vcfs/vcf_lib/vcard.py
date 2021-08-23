"""Definitions and behavior for vCard 3.0"""

from .base import ContentLine, backslashEscape, behavior_registry
from .behavior import Behavior
from .utils import stringToTextValues

# ------------------------ vCard structs ---------------------------------------


class Name:
    def __init__(self, family='', given='', additional='', prefix='', suffix=''):
        """Each name attribute can be a string or a list of strings."""
        self.family = family
        self.given = given
        self.additional = additional
        self.prefix = prefix
        self.suffix = suffix

    def __repr__(self):
        return '<Name({})>'.format(
            ', '.join(f'{k}="{v}"' for k, v in self.__dict__.items())
        )


class Address:
    def __init__(self, street='', city='', region='', code='',
                 country='', box='', extended=''):
        """Each name attribute can be a string or a list of strings."""
        self.box = box
        self.extended = extended
        self.street = street
        self.city = city
        self.region = region
        self.code = code
        self.country = country

    def __repr__(self):
        return '<Address({})>'.format(
            ', '.join(f'{k}="{v}"' for k, v in self.__dict__.items())
        )


# ------------------------ Registered Behavior subclasses ----------------------

class VCardTextBehavior(Behavior):
    """Provide backslash escape encoding/decoding for single valued properties.

    TextBehavior also deals with base64 encoding if the ENCODING parameter is
    explicitly set to BASE64.

    """
    allowGroup = True
    base64string = 'B'

    @classmethod
    def decode(cls, line):
        """Remove backslash escaping from line.valueDecode line, either to remove
        backslash espacing, or to decode base64 encoding. The content line should
        contain a ENCODING=b for base64 encoding, but Apple Addressbook seems to
        export a singleton parameter of 'BASE64', which does not match the 3.0
        vCard spec. If we encouter that, then we transform the parameter to
        ENCODING=b
        """
        if line.encoded:
            if 'BASE64' in line.singletonparams:
                line.singletonparams.remove('BASE64')
                line.encoding_param = cls.base64string

            encoding = getattr(line, 'encoding_param', None)

            # Original code of vobject 0.8.1c fixed by Yann PRIME :
            # if encoding:
            if encoding == cls.base64string:
                line.value = line.value.decode('base64')
            else:
                line.value = stringToTextValues(line.value)[0]

            line.encoded = False

    @classmethod
    def encode(cls, line):
        """Backslash escape line.value."""
        if not line.encoded:
            encoding = getattr(line, 'encoding_param', None)
            if encoding and encoding.upper() == cls.base64string:
                line.value = line.value.encode('base64').replace('\n', '')
            else:
                line.value = backslashEscape(line.value)

            line.encoded = True


class VCardBehavior(Behavior):
    allowGroup = True
    defaultBehavior = VCardTextBehavior


@behavior_registry.register(default=True)
class VCard3_0(VCardBehavior):
    """vCard 3.0 behavior."""
    name = 'VCARD'
    description = 'vCard 3.0, defined in rfc2426'
    versionString = '3.0'
    isComponent = True
    sortFirst = ('version', 'prodid', 'uid')
    knownChildren = {
        'N':          (1, 1, None),  # min, max, behaviorRegistry id
        'FN':         (1, 1, None),
        'VERSION':    (1, 1, None),  # required, auto-generated
        'PRODID':     (0, 1, None),
        'LABEL':      (0, None, None),
        'UID':        (0, None, None),
        'ADR':        (0, None, None),
        'ORG':        (0, None, None),
        'PHOTO':      (0, None, None),
        'CATEGORIES': (0, None, None),
    }

    @classmethod
    def generateImplicitParameters(cls, obj):
        """Create PRODID, VERSION, and VTIMEZONEs if needed.

        VTIMEZONEs will need to exist whenever TZID parameters exist or when
        datetimes with tzinfo exist.
        """
        if not hasattr(obj, 'version'):
            obj.add(ContentLine('VERSION', [], cls.versionString))


@behavior_registry.register
class FN(VCardTextBehavior):
    name = 'FN'
    description = 'Formatted name'


@behavior_registry.register
class Label(VCardTextBehavior):
    name = 'Label'
    description = 'Formatted address'


wacky_apple_photo_serialize = True
REALLY_LARGE = 1E50


@behavior_registry.register
class Photo(VCardTextBehavior):
    name = 'Photo'
    description = 'Photograph'

    @classmethod
    def valueRepr(cls, line):
        return " (BINARY PHOTO DATA at 0x{}) ".format(id(line.value))

    @classmethod
    def serialize(cls, obj, buf, lineLength, validate):
        """Apple's Address Book is *really* weird with images, it expects
        base64 data to have very specific whitespace.  It seems Address Book
        can handle PHOTO if it's not wrapped, so don't wrap it.
        """
        if wacky_apple_photo_serialize:
            lineLength = REALLY_LARGE

        VCardTextBehavior.serialize(obj, buf, lineLength, validate)


def toListOrString(string):
    stringList = stringToTextValues(string)
    if len(stringList) == 1:
        return stringList[0]
    else:
        return stringList


def splitFields(string):
    "Return a list of strings or lists from a Name or Address."
    return [
        toListOrString(i)
        for i in stringToTextValues(string, listSeparator=';', charList=';')
    ]


def toList(stringOrList):
    if isinstance(stringOrList, str):
        return [stringOrList]

    return stringOrList


def serializeFields(obj, order=None):
    """Turn an object's fields into a ';' and ',' separated string.

    If order is None, obj should be a list, backslash escape each field and
    return a ';' separated string.
    """
    if order is None:
        fields = (backslashEscape(val) for val in obj)
    else:
        fields = (
            ','.join(
                backslashEscape(val)
                for val in toList(getattr(obj, field))
            ) for field in order
        )

    return ';'.join(fields)


@behavior_registry.register('N')
class NameBehavior(VCardBehavior):
    """A structured name."""
    hasNative = True
    _ORDER = ('family', 'given', 'additional', 'prefix', 'suffix')

    @classmethod
    def transformToNative(cls, obj):
        "Turn obj.value into a Name."
        if obj.isNative:
            return obj

        obj.isNative = True
        obj.value = Name(**dict(zip(cls._ORDER, splitFields(obj.value))))

        return obj

    @classmethod
    def transformFromNative(cls, obj):
        "Replace the Name in obj.value with a string."
        obj.isNative = False
        obj.value = serializeFields(obj.value, cls._ORDER)

        return obj


@behavior_registry.register('ADR')
class AddressBehavior(VCardBehavior):
    """A structured address."""
    hasNative = True
    _ORDER = ('box', 'extended', 'street', 'city', 'region', 'code', 'country')

    @classmethod
    def transformToNative(cls, obj):
        "Turn obj.value into an Address."
        if obj.isNative:
            return obj

        obj.isNative = True
        obj.value = Address(**dict(zip(cls._ORDER, splitFields(obj.value))))

        return obj

    @classmethod
    def transformFromNative(cls, obj):
        "Replace the Address in obj.value with a string."
        obj.isNative = False
        obj.value = serializeFields(obj.value, cls._ORDER)

        return obj


@behavior_registry.register('ORG')
class OrgBehavior(VCardBehavior):
    """A list of organization values and sub-organization values."""
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        "Turn obj.value into a list."
        if obj.isNative:
            return obj

        obj.isNative = True
        obj.value = splitFields(obj.value)

        return obj

    @staticmethod
    def transformFromNative(obj):
        "Replace the list in obj.value with a string."
        if not obj.isNative:
            return obj

        obj.isNative = False
        obj.value = serializeFields(obj.value)

        return obj
