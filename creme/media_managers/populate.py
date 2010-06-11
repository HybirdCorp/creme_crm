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

from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from media_managers.models import MediaCategory, Image


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        create(MediaCategory, name=u"Image de produit",    is_custom=False)
        create(MediaCategory, name=u"Logo d'organisation", is_custom=False)
        create(MediaCategory, name=u"Photo de contact",    is_custom=False)

        hf_id = create(HeaderFilter, 'media_managers-hf_image', name=u"Vue d'Image", entity_type_id=ContentType.objects.get_for_model(Image).id, is_custom=False).id
        pref  = 'media_managers-hfi_image_'
        create(HeaderFilterItem, pref + 'name',  order=1, name='name',        title=u'Nom',         type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True,  editable=True, filter_string="name__icontains" )
        create(HeaderFilterItem, pref + 'image', order=2, name='image',       title=u'Image',       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=False, editable=False)
        create(HeaderFilterItem, pref + 'descr', order=3, name='description', title=u'Description', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True,  editable=True, filter_string="description__icontains")
        create(HeaderFilterItem, pref + 'user',  order=4, name='user',        title=u'Utilisateur', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True,  editable=True, filter_string="user__username__icontains" )
        create(HeaderFilterItem, pref + 'cat',   order=5, name='categories',  title=u'Catégories',  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=False, editable=False)
