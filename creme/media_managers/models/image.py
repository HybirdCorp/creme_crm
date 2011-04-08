# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

import mimetypes

from django.db.models import CharField, TextField, ImageField, ManyToManyField
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import escape

from creme_core.models.entity import CremeEntity

from other_models import MediaCategory

from settings import MEDIA_URL


class Image(CremeEntity):
    name        = CharField(_(u'Name'), max_length=100, blank=True, null=True)
    description = TextField(_(u'Description'), max_length=500, blank=True, null=True)
    height      = CharField(_(u'Height'), max_length=50, blank=True, null=True)
    width       = CharField(_(u'Width'), max_length=50, blank=True, null=True)
    image       = ImageField(_('Image'), height_field='height', width_field='width',
                             upload_to='upload/images', max_length=500)
    categories = ManyToManyField(MediaCategory, verbose_name=_(u'Categories'),
                                 related_name="Image_media_category_set", blank=True, null=True)

    research_fields = CremeEntity.research_fields + ['description', 'name', 'image']

    class Meta:
        app_label = 'media_managers'
        verbose_name = _(u'Image')
        verbose_name_plural = _(u'Images')

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
        return "%s%s" % (MEDIA_URL, self.image)

    def get_entity_summary(self):
        from creme_core.templatetags.creme_core_tags import image_size #TODO: move this templatetag to 'media_managers' ????
        url = self.get_image_url()
        name = escape(self.get_image_name())
        return mark_safe("""<a href="javascript:creme.utils.openWindow('%s','image_popup');"><img src="%s" %s alt="%s" title="%s"/></a>""" % \
            (url, url, image_size(self, 150, 150), name, name))

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

#    image_file = property(get_image_file)
