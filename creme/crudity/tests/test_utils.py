from creme.creme_core.models import SettingValue
from creme.creme_core.tests.base import CremeTestCase

# from ..constants import SETTING_CRUDITY_SANDBOX_BY_USER
from ..setting_keys import sandbox_key
from ..utils import decode_b64binary, is_sandbox_by_user


class UtilsTestCase(CremeTestCase):
    def test_decode_b64binary01(self):
        img_blob = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\
\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\x00\tpHYs\x00\x00\x01\xbb\x00\x00\x01\
\xbb\x01:\xec\xe3\xe2\x00\x00\x00\x19tEXtSoftware\x00www.inkscape.org\x9b\xee<\x1a\x00\x00\x01\xf9IDAT8\
\x8d\xa5\x93=kTA\x14\x86\xdfw\xce\xcc\xdc\xdd\xec\xcdn\xa2b\x82\x18\x95\x80`c\xa1M\xc0\xc6\x9f \xe2O\xb0\
\xb0\xb0\x12m\xd4B\x82\x85b\x19;\xff\x89X\x1a\xacmD\xf0+\xeaB\x12\xdc\xa8\xd9M\xb2\x1fs\xef\xcc\xb1\xf0#\
\xc9^E\xc1\x81S\x9c\x03\xe7\x99\xf7=g\x86\xaa\x8a\xff9v\xbc\xd0x\x94=`CN\x9a\x96\x99\x12\xc3\xe6\xec\xe1\x19v\
\xdb\xdb\xed\xd5\x8b\xeb\x17\xfe\n\xe0-\x9e:zy\xe6\xda(\x05K\x03\x94\x83\xd4{\xbd\xfc\xb6\tb\xf6O\n\
\xcc\xbe,!+cT\n`\xad\x80\x80p\x02\x80G\xfa7\x0b\x19\x1ab\xa8\xe2=\xa0\n\x12\x82\x06\x80!D\xee\xf3:\x14E\
\x02\x9e\xe8M}\xf9K\xb5\xaa\xa2\xbeT?\x7fha\xfa!j\xda23f\x8e$\xcbP\xa0\x08\x05\x86_\x87\xabE\x11\x8b\xd0-\
\xc8\x8e\x1eK=<\x8fW\xf5\xcc>\x054\xf1\x9c\x9fw\xa7\x8bQ\x80\xb3\x82\x98v7c\x1ar\xc4'\x82\x8a\xf6\xe8C\x00\
\x05\xb12\x83\xa2\x1b\xd7\x8d!|\xddCle1\xf0\xb5\x0c\xc6\x08\xd8\x04\xf0;\x00\x1cr\x979d\x99\xaf6{\x8fz\xad\
\x06#t\x08\xdfK\x15\x80*_\xf5W\x06\xef\x06\x9d\xb0\x06\x05\xf0\xc3\x81\x11\x03\xe7-\xac\xb1H\x85:\xedc\x13\
\xdbx\xb3\x17\xc0\xbd/\x91\xb7y\xf6\xc4\x95\xb9\xa7\xa8\xe9D1\x08HQ\xb5\xf3\xec\xf3G\x06e\xdc\xd2\xc7i\x03\
\xf7\xf4\xae\xaeT-\xecf]U\x8d\x00 N`\x12\x82\xee\xa4\xe3\xd1\xa9O\x9b\xb81\xde\xbc\x0f@\x92\x8enB\x87IA@\xac\
\x00\x8a\x12\x02\x18\xc1\x10\xab\x18T\x06\xb4\xd7\x02AN.N\x1e\xec\xdb\xfe%\xd7\x92\x05\x99\x96y5\xa95Z\x0b\
\xefm\xcf/Y\xb1_(\x8c$\xcb\x18b\xaf\x8f\xfe'\xbd\xa3%\xc7\x7f#\x17is\xe4\x07\xa2\x8dNKu\xe2\xa4\x89\x08\x8e\
\xdf\x1c\x19{\xf9V\xbeQ\x01T$.\xd2\xe7\xc8\xa7\x14j~\x06,hJS\xec\xbc\xd8\xe9|\x03\x8fa\xdf\\\xf3\xf4\rH\x00\
\x00\x00\x00IEND\xaeB`\x82"  # NOQA

        encoded = b"x0lGQRQAAAABAAAAAAAAAHwCAAAGAAAAYgAuAHAAbgBnAAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgI\
fAhkiAAAAAlwSFlzAAABuwAAAbsBOuzj4gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAH5SURBVDiNpZM9a1RBFIbf\
d87M3N3szW6iYoIYlYBgY6FNwMafIOJPsLCwEm3UQoKFYhk7/4lYGqxtRPAr6kIS3KjZTbIfc+/MsfAjyV5FwYFTnAPnmfc9Z4aqiv85drzQ\
eJQ9YENOmpaZEsPm7OEZdtvb7dWL6xf+CuAtnjp6eebaKAVLA5SD1Hu9/LYJYvZPCsy+LCErY1QKYK2AgHACgEf6NwsZGmKo4j2gChKCBoAh\
RO7zOhRFAp7oTX35S7Wqor5UP39oYfohatoyM2aOJMtQoAgFhl+Hq0URi9AtyI4eSz08j1f1zD4FNPGcn3eni1GAs4KYdjdjGnLEJ4KK9uhD\
AAWxMoOiG9eNIXzdQ2xlMfC1DMYI2ATwOwAccpc5ZJmvNnuPeq0GI3QI30sVgCpf9VcG7wadsAYF8MOBEQPnLayxSIU67WMT23izF8C9L5G3\
efbElbmnqOlEMQhIUbXz7PNHBmXc0sdpA/f0rq5ULexmXVWNACBOYBKC7qTj0alPm7gx3rwPQJKObkKHSUFArACKEgIYwRCrGFQGtNcCQU4u\
Th7s2/4l15IFmZZ5Nak1Wgvvbc8vWbFfKIwkyxhir4/+J72jJcd/Ixdpc+QHoo1OS3XipIkIjt8cGXv5Vr5RAVQkLtLnyKcUan4GLGhKU+y8\
2Ol8A49h31zz9A1IAAAAAElFTkSuQmCC"  # NOQA
        filename, blob = decode_b64binary(encoded)
        self.assertEqual(img_blob, blob)

        encoded_utf8_name = b"x0lGQRQAAAABAAAAAAAAAHwCAAANAAAAcgDpAGcAZwDgAOgA6wB4AS4AcABuAGcAAACJUE5HDQoaCgAAAA1JSERSAAAAEAAAABAIBgAAAB/z/2\
EAAAAEc0JJVAgICAh8CGSIAAAACXBIWXMAAAG7AAABuwE67OPiAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAflJREFU\
OI2lkz1rVEEUht93zszc3ezNbqJighiVgGBjoU3Axp8g4k+wsLASbdRCgoViGTv/iVgarG1E8CvqQhLcqNlNsh9z78yx8CPJXkXBgVOcA+eZ9z\
1nhqqK/zl2vNB4lD1gQ06alpkSw+bs4Rl229vt1YvrF/4K4C2eOnp55tooBUsDlIPUe738tgli9k8KzL4sIStjVApgrYCAcAKAR/o3CxkaYqji\
PaAKEoIGgCFE7vM6FEUCnuhNfflLtaqivlQ/f2hh+iFq2jIzZo4ky1CgCAWGX4erRRGL0C3Ijh5LPTyPV/XMPgU08Zyfd6eLUYCzgph2N2Macs\
Qngor26EMABbEyg6Ib140hfN1DbGUx8LUMxgjYBPA7ABxylzlkma82e496rQYjdAjfSxWAKl/1VwbvBp2wBgXww4ERA+ctrLFIhTrtYxPbeLMX\
wL0vkbd59sSVuaeo6UQxCEhRtfPs80cGZdzSx2kD9/SurlQt7GZdVY0AIE5gEoLupOPRqU+buDHevA9Ako5uQodJQUCsAIoSAhjBEKsYVAa01w\
JBTi5OHuzb/iXXkgWZlnk1qTVaC+9tzy9ZsV8ojCTLGGKvj/4nvaMlx38jF2lz5AeijU5LdeKkiQiO3xwZe/lWvlEBVCQu0ufIpxRqfgYsaEpT\
7LzY6XwDj2HfXPP0DUgAAAAASUVORK5CYII="  # NOQA
        filename, blob = decode_b64binary(encoded_utf8_name)
        self.assertEqual(img_blob, blob)

    def test_is_sandbox_by_user01(self):
        sv = self.get_object_or_fail(
            SettingValue,
            # key_id=SETTING_CRUDITY_SANDBOX_BY_USER,
            key_id=sandbox_key.id,
        )
        self.assertIs(sv.value, False)

        self.assertFalse(is_sandbox_by_user())

    def test_is_sandbox_by_user02(self):
        sv = self.get_object_or_fail(
            SettingValue,
            # key_id=SETTING_CRUDITY_SANDBOX_BY_USER,
            key_id=sandbox_key.id,
        )
        sv.value = True
        sv.save()

        self.assertTrue(is_sandbox_by_user())
