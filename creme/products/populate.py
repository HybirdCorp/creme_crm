# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import logging

from django.apps import apps
from django.utils.translation import ugettext as _

from creme.creme_core.blocks import relations_block, properties_block, customfields_block, history_block
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import SearchConfigItem, HeaderFilter, BlockDetailviewLocation
from creme.creme_core.management.commands.creme_populate import BasePopulator

from . import blocks, constants, get_product_model, get_service_model
from .models import Category, SubCategory


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Product = get_product_model()
        Service = get_service_model()

        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_PRODUCT,
                  model=Product,
                  name=_(u'Product view'),
                  cells_desc=[# (EntityCellRegularField, {'name': 'images__name'}),
                              (EntityCellRegularField, {'name': 'images'}),
                              (EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'code'}),
                              (EntityCellRegularField, {'name': 'user'}),
                             ],
                 )

        create_hf(pk=constants.DEFAULT_HFILTER_SERVICE,
                  model=Service,
                  name=_(u'Service view'),
                  cells_desc=[# (EntityCellRegularField, {'name': 'images__name'}),
                              (EntityCellRegularField, {'name': 'images'}),
                              (EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'reference'}),
                              (EntityCellRegularField, {'name': 'user'}),
                             ],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        create_searchconf(Service, ['name', 'description', 'category__name', 'sub_category__name'])

        # ---------------------------
        if not Category.objects.exists():  # NB: no straightforward way to test that this populate script has not been already run
            create_cat = Category.objects.create
            create_subcat = SubCategory.objects.create

            jewelry = create_cat(name=_(u"Jewelry"))
            create_subcat(name=_(u"Ring"),     category=jewelry)
            create_subcat(name=_(u"Bracelet"), category=jewelry)
            create_subcat(name=_(u"Necklace"), category=jewelry)
            create_subcat(name=_(u"Earrings"), category=jewelry)

            mobile = create_cat(name=_(u"Mobile"))
            create_subcat(name=_(u"Iphone"),     category=mobile)
            create_subcat(name=_(u"Blackberry"), category=mobile)
            create_subcat(name=_(u"Samsung"),    category=mobile)
            create_subcat(name=_(u"Android"),    category=mobile)

            informatic = create_cat(name=_(u"Informatic"))
            create_subcat(name=_(u"Laptops"),   category=informatic)
            create_subcat(name=_(u"Desktops"), category=informatic)
            create_subcat(name=_(u"Tablet"),   category=informatic)
            create_subcat(name=_(u"Notebook"), category=informatic)

            travels = create_cat(name=_(u"Travels"))
            create_subcat(name=_(u"Fly"),      category=travels)
            create_subcat(name=_(u"Hotel"),    category=travels)
            create_subcat(name=_(u"Week-end"), category=travels)
            create_subcat(name=_(u"Rent"),     category=travels)

            vehicle = create_cat(name=_(u"Vehicle"))
            create_subcat(name=_(u"Car"),   category=vehicle)
            create_subcat(name=_(u"Moto"),  category=vehicle)
            create_subcat(name=_(u"Boat"),  category=vehicle)
            create_subcat(name=_(u"Plane"), category=vehicle)

            games_toys = create_cat(name=_(u"Games & Toys"))
            create_subcat(name=_(u"Boys"),    category=games_toys)
            create_subcat(name=_(u"Girls"),   category=games_toys)
            create_subcat(name=_(u"Teens"),   category=games_toys)
            create_subcat(name=_(u"Baybies"), category=games_toys)

            clothes = create_cat(name=_(u"Clothes"))
            create_subcat(name=_(u"Men"),     category=clothes)
            create_subcat(name=_(u"Women"),   category=clothes)
            create_subcat(name=_(u"Kids"),    category=clothes)
            create_subcat(name=_(u"Baybies"), category=clothes)

        # ---------------------------
        if not BlockDetailviewLocation.config_exists(Product):  # NB: no straightforward way to test that this populate script has not been already run
            create_bdl = BlockDetailviewLocation.create
            TOP   = BlockDetailviewLocation.TOP
            LEFT  = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            for model in (Product, Service):
                create_bdl(block_id=blocks.images_block.id_, order=10,  zone=TOP,   model=model)
                BlockDetailviewLocation.create_4_model_block(order=5,   zone=LEFT,  model=model)
                create_bdl(block_id=customfields_block.id_,  order=40,  zone=LEFT,  model=model)
                create_bdl(block_id=properties_block.id_,    order=450, zone=LEFT,  model=model)
                create_bdl(block_id=relations_block.id_,     order=500, zone=LEFT,  model=model)
                create_bdl(block_id=history_block.id_,       order=30,  zone=RIGHT, model=model)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views and portal')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                for model in (Product, Service):
                    create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=model)
                    create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=model)
                    create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=model)
                    create_bdl(block_id=messages_block.id_, order=500, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.blocks import linked_docs_block

                for model in (Product, Service):
                    create_bdl(block_id=linked_docs_block.id_, order=600, zone=RIGHT, model=model)
