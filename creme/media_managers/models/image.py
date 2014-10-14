# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import base64
import mimetypes
import warnings
import os

from PIL import ImageFile as PILImageFile

from django.conf import settings
from django.db.models import CharField, TextField, ImageField, ManyToManyField
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import escape

from creme.creme_core.models.entity import CremeEntity
from creme.creme_core.gui.field_printers import image_size

from .other_models import MediaCategory


class Image(CremeEntity):
    name        = CharField(_(u'Name'), max_length=100, blank=True, null=True)
    description = TextField(_(u'Description'), max_length=500, blank=True, null=True)
    height      = CharField(_(u'Height'), max_length=50, blank=True, null=True, editable=False)
    width       = CharField(_(u'Width'), max_length=50, blank=True, null=True, editable=False)
    image       = ImageField(_('Image'), height_field='height', width_field='width',
                             upload_to='upload/images', max_length=500)
    categories = ManyToManyField(MediaCategory, verbose_name=_(u'Categories'),
                                 related_name="Image_media_category_set", blank=True, null=True)

    creation_label = _('Add an image')

    encodings = {
        "base64": lambda x: base64.b64encode(x),
    }

    class Meta:
        app_label = 'media_managers'
        verbose_name = _(u'Image')
        verbose_name_plural = _(u'Images')
        ordering = ('name',)

    def get_absolute_url(self):
        return "/media_managers/image/%s" % self.id

    def get_image_name(self):
        if self.name:
            name = self.name
        else:
            name = self.image.path.rpartition('/')[2].split('.')[0] #TODO: use os.path ????
        return name

    def __unicode__(self):
        return self.get_image_name()

    def get_image_url(self):
        return settings.MEDIA_URL + unicode(self.image).replace(os.sep, '/') #TODO credentials static/dynamic image

    def get_entity_summary(self, user):
        if not user.has_perm_to_view(self):
            return self.allowed_unicode(user)

        return mark_safe("""<img src="%(url)s" %(size)s alt="%(name)s" title="%(name)s"/>""" % {
                            'url':  self.get_image_url(),
                            'size': image_size(self.image, 150, 150),
                            'name': escape(self.get_image_name())
                        }
                      )

    def get_entity_m2m_summary(self, user):
        warnings.warn("Image.get_entity_m2m_summary() method is deprecated; use Image.get_entity_summary() instead",
                      DeprecationWarning
                     )

        if not user.has_perm_to_view(self):
            return self.allowed_unicode(user)

        return '<img src="%(url)s" alt="%(title)s" title="%(title)s" %(size)s class="magnify"/>' % {
                      'url':   self.image.url,
                      'title': escape(self),
                      'size':  image_size(self, 80, 80),
                  }

    @staticmethod
    def get_lv_absolute_url():
        return '/media_managers/images'

    def get_edit_absolute_url(self):
        return "/media_managers/image/edit/%s" % self.id

    def get_image_file(self):
#        return (self.image.file,  'image/jpeg')#mimetypes.guess_type(self.image.path))
        self.image.file.open()
        #return (self.image.file, "image/gif")
        return (self.image.file, mimetypes.guess_type(self.image.path)[0])

    def get_encoded(self, encoding="base64"):
        encoded = u""
        encoder = self.encodings.get(encoding, "base64")
        for ch in self.image.file.chunks():
            encoded += encoder(ch)
        return encoded

    @staticmethod
    def get_image_format(image_base64_str):
        p = PILImageFile.Parser()
        p.feed(base64.decodestring(image_base64_str))
        return p.close().format


#    image_file = property(get_image_file)
