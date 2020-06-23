# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from django.utils.translation import gettext as _

from creme.creme_core.bricks import (
    CustomFieldsBrick,
    HistoryBrick,
    PropertiesBrick,
    RelationsBrick,
)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    SearchConfigItem,
)

from . import bricks, constants, get_product_model, get_service_model
from .models import Category, SubCategory

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Product = get_product_model()
        Service = get_service_model()

        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(pk=constants.DEFAULT_HFILTER_PRODUCT,
                  model=Product,
                  name=_('Product view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'images'}),
                              (EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'code'}),
                              (EntityCellRegularField, {'name': 'user'}),
                              ],
                  )

        create_hf(pk=constants.DEFAULT_HFILTER_SERVICE,
                  model=Service,
                  name=_('Service view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'images'}),
                              (EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'reference'}),
                              (EntityCellRegularField, {'name': 'user'}),
                              ],
                  )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        create_searchconf(Service, ['name', 'description', 'category__name', 'sub_category__name'])

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not Category.objects.exists():
            create_cat = Category.objects.create
            create_subcat = SubCategory.objects.create

            jewelry = create_cat(name=_('Jewelry'))
            create_subcat(name=_('Ring'),     category=jewelry)
            create_subcat(name=_('Bracelet'), category=jewelry)
            create_subcat(name=_('Necklace'), category=jewelry)
            create_subcat(name=_('Earrings'), category=jewelry)

            mobile = create_cat(name=_('Mobile'))
            create_subcat(name=_('Iphone'),     category=mobile)
            create_subcat(name=_('Blackberry'), category=mobile)
            create_subcat(name=_('Samsung'),    category=mobile)
            create_subcat(name=_('Android'),    category=mobile)

            electronics = create_cat(name=_('Electronics'))
            create_subcat(name=_('Laptops'),  category=electronics)
            create_subcat(name=_('Desktops'), category=electronics)
            create_subcat(name=_('Tablet'),   category=electronics)
            create_subcat(name=_('Notebook'), category=electronics)

            travels = create_cat(name=_('Travels'))
            create_subcat(name=_('Fly'),      category=travels)
            create_subcat(name=_('Hotel'),    category=travels)
            create_subcat(name=_('Week-end'), category=travels)
            create_subcat(name=_('Rent'),     category=travels)

            vehicle = create_cat(name=_('Vehicle'))
            create_subcat(name=_('Car'),   category=vehicle)
            create_subcat(name=_('Moto'),  category=vehicle)
            create_subcat(name=_('Boat'),  category=vehicle)
            create_subcat(name=_('Plane'), category=vehicle)

            games_toys = create_cat(name=_('Games & Toys'))
            create_subcat(name=_('Boys'),   category=games_toys)
            create_subcat(name=_('Girls'),  category=games_toys)
            create_subcat(name=_('Teens'),  category=games_toys)
            create_subcat(name=_('Babies'), category=games_toys)

            clothes = create_cat(name=_('Clothes'))
            create_subcat(name=_('Men'),    category=clothes)
            create_subcat(name=_('Women'),  category=clothes)
            create_subcat(name=_('Kids'),   category=clothes)
            create_subcat(name=_('Babies'), category=clothes)

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(Product).exists():
            create_bdl = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_4_model = BrickDetailviewLocation.objects.create_for_model_brick
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            for model in (Product, Service):
                create_bdl(brick=bricks.ImagesBrick, order=10, zone=TOP, model=model)
                create_bdl_4_model(order=5, zone=LEFT, model=model)
                create_bdl(brick=CustomFieldsBrick, order=40,  zone=LEFT,  model=model)
                create_bdl(brick=PropertiesBrick,   order=450, zone=LEFT,  model=model)
                create_bdl(brick=RelationsBrick,    order=500, zone=LEFT,  model=model)
                create_bdl(brick=HistoryBrick,      order=30,  zone=RIGHT, model=model)

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail views and portal'
                )

                from creme.assistants.bricks import (
                    AlertsBrick,
                    MemosBrick,
                    TodosBrick,
                    UserMessagesBrick,
                )

                for model in (Product, Service):
                    create_bdl(brick=TodosBrick,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick=MemosBrick,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick=AlertsBrick,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick=UserMessagesBrick, order=500, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                for model in (Product, Service):
                    create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=model)
