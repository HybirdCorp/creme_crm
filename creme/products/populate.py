# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from functools import partial

from django.apps import apps
from django.utils.translation import gettext as _

from creme.creme_core.bricks import (
    CustomFieldsBrick,
    HistoryBrick,
    PropertiesBrick,
    RelationsBrick,
)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomFormConfigItem,
    HeaderFilter,
    MenuConfigItem,
    SearchConfigItem,
)

from . import (
    bricks,
    constants,
    custom_forms,
    get_product_model,
    get_service_model,
    menu,
)
from .forms.base import SubCategorySubCell
from .models import Category, SubCategory

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        Product = get_product_model()
        Service = get_service_model()

        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_PRODUCT,
            model=Product,
            name=_('Product view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'images'}),
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'code'}),
                (EntityCellRegularField, {'name': 'user'}),
            ],
        )

        create_hf(
            pk=constants.DEFAULT_HFILTER_SERVICE,
            model=Service,
            name=_('Service view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'images'}),
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'reference'}),
                (EntityCellRegularField, {'name': 'user'}),
            ],
        )

        # ---------------------------
        common_groups_desc = [
            {
                'name': _('Description'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]

        def build_creation_custom_form_item(descriptor, main_cells_desc):
            CustomFormConfigItem.objects.create_if_needed(
                descriptor=descriptor,
                groups_desc=[
                    {
                        'name': _('General information'),
                        'layout': LAYOUT_DUAL_FIRST,
                        'cells': [
                            *main_cells_desc,
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                            ),
                        ],
                    },
                    *common_groups_desc,
                    {
                        'name': _('Properties'),
                        'cells': [
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                            ),
                        ],
                    }, {
                        'name': _('Relationships'),
                        'cells': [
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.RELATIONS},
                            ),
                        ],
                    },
                ],
            )

        def build_edition_custom_form_item(descriptor, main_cells_desc):
            CustomFormConfigItem.objects.create_if_needed(
                descriptor=descriptor,
                groups_desc=[
                    {
                        'name': _('General information'),
                        'layout': LAYOUT_DUAL_FIRST,
                        'cells': [
                            *main_cells_desc,
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                            ),
                        ],
                    },
                    *common_groups_desc,
                ],
            )

        main_product_cells_desc = [
            (EntityCellRegularField, {'name': 'user'}),
            (EntityCellRegularField, {'name': 'name'}),
            (EntityCellRegularField, {'name': 'code'}),
            SubCategorySubCell(model=Product).into_cell(),
            (EntityCellRegularField, {'name': 'unit_price'}),
            (EntityCellRegularField, {'name': 'unit'}),
            (EntityCellRegularField, {'name': 'quantity_per_unit'}),
            (EntityCellRegularField, {'name': 'weight'}),
            (EntityCellRegularField, {'name': 'stock'}),
            (EntityCellRegularField, {'name': 'web_site'}),
        ]
        build_creation_custom_form_item(
            descriptor=custom_forms.PRODUCT_CREATION_CFORM,
            main_cells_desc=[
                *main_product_cells_desc,
                (EntityCellRegularField, {'name': 'images'}),
            ]
        )
        build_edition_custom_form_item(
            descriptor=custom_forms.PRODUCT_EDITION_CFORM,
            main_cells_desc=main_product_cells_desc,
        )

        main_service_cells_desc = [
            (EntityCellRegularField, {'name': 'user'}),
            (EntityCellRegularField, {'name': 'name'}),
            (EntityCellRegularField, {'name': 'reference'}),
            SubCategorySubCell(model=Service).into_cell(),
            (EntityCellRegularField, {'name': 'countable'}),
            (EntityCellRegularField, {'name': 'unit'}),
            (EntityCellRegularField, {'name': 'quantity_per_unit'}),
            (EntityCellRegularField, {'name': 'unit_price'}),
            (EntityCellRegularField, {'name': 'web_site'}),
        ]
        build_creation_custom_form_item(
            descriptor=custom_forms.SERVICE_CREATION_CFORM,
            main_cells_desc=[
                *main_service_cells_desc,
                (EntityCellRegularField, {'name': 'images'}),
            ]
        )
        build_edition_custom_form_item(
            descriptor=custom_forms.SERVICE_EDITION_CFORM,
            main_cells_desc=main_service_cells_desc,
        )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        create_searchconf(Service, ['name', 'description', 'category__name', 'sub_category__name'])

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='products-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Management')},
                defaults={'order': 50},
            )[0]

            create_mitem = partial(MenuConfigItem.objects.create, parent=container)
            create_mitem(entry_id=menu.ProductsEntry.id, order=20)
            create_mitem(entry_id=menu.ServicesEntry.id, order=25)

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
            RIGHT = BrickDetailviewLocation.RIGHT

            for model in (Product, Service):
                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': model, 'zone': BrickDetailviewLocation.LEFT},
                    data=[
                        {
                            'brick': bricks.ImagesBrick, 'order': 10,
                            'zone': BrickDetailviewLocation.TOP,
                        },

                        {'order': 5},  # generic info brick
                        {'brick': CustomFieldsBrick, 'order':  40},
                        {'brick': PropertiesBrick,   'order': 450},
                        {'brick': RelationsBrick,    'order': 500},

                        {'brick': HistoryBrick, 'order': 30, 'zone': RIGHT},
                    ],
                )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail views and portal'
                )

                from creme.assistants import bricks as a_bricks

                for model in (Product, Service):
                    BrickDetailviewLocation.objects.multi_create(
                        defaults={'model': model, 'zone': RIGHT},
                        data=[
                            {'brick': a_bricks.TodosBrick,        'order': 100},
                            {'brick': a_bricks.MemosBrick,        'order': 200},
                            {'brick': a_bricks.AlertsBrick,       'order': 300},
                            {'brick': a_bricks.UserMessagesBrick, 'order': 500},
                        ],
                    )

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'brick': LinkedDocsBrick, 'order': 600, 'zone': RIGHT},
                    data=[{'model': model} for model in (Product, Service)],
                )
