################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomFormConfigItem,
    HeaderFilter,
    MenuConfigItem,
    SearchConfigItem,
)
from creme.documents.models import DocumentCategory

from . import (
    bricks,
    constants,
    custom_forms,
    get_product_model,
    get_service_model,
    menu,
)
from .models import Category, SubCategory

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'documents']

    SEARCH = {
        'PRODUCT': [
            'name', 'description', 'category__name', 'sub_category__name',
        ],
        'SERVICE': [
            'name', 'description', 'category__name', 'sub_category__name',
        ],
    }
    DOC_CATEGORIES = [
        DocumentCategory(
            uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
            name=_('Product image'),
            is_custom=False,
        ),
    ]
    CATEGORIES = [
        [
            Category(uuid='3fb0ef3c-45d0-40bd-8e71-b1ab49fca8d3', name=_('Jewelry')),
            [
                SubCategory(uuid='2d6555fe-4c25-4098-8128-25395cf2c10b', name=_('Ring')),
                SubCategory(uuid='c160d58f-6878-4dd6-87d6-ee05db310f3a', name=_('Bracelet')),
                SubCategory(uuid='83b79894-122e-4212-bf18-929573f57c74', name=_('Necklace')),
                SubCategory(uuid='6514cb2a-ee59-4abf-bdef-92488fac3a42', name=_('Earrings')),
            ]
        ], [
            Category(uuid='74c91fab-d671-4054-984f-ba395d7dffcb', name=_('Mobile')),
            [
                SubCategory(uuid='2abfa34f-d30f-4629-9a45-8cd63ce0a362', name=_('Iphone')),
                SubCategory(uuid='4c55bae2-44d3-44ca-aade-e8433339f2aa', name=_('Blackberry')),
                SubCategory(uuid='5fc12768-bc62-4412-a9d4-91aa9967bfac', name=_('Samsung')),
                SubCategory(uuid='62e549a1-f132-4c82-a836-e8d94ee8b29b', name=_('Android')),
            ]
        ], [
            Category(uuid='69084c8f-068c-41e3-80e3-42ed312e9815', name=_('Electronics')),
            [
                SubCategory(uuid='25f7c8db-a0d1-42af-a342-97727a2229fd', name=_('Laptops')),
                SubCategory(uuid='6e3c21d1-f81e-492c-b2ce-da1fbc46727f', name=_('Desktops')),
                SubCategory(uuid='13463841-90df-4036-b830-62ad75668213', name=_('Tablet')),
                SubCategory(uuid='3a14d682-77b5-43b7-9b9c-8db9bcd44b0d', name=_('Notebook')),
            ]
        ], [
            Category(uuid='213e14fa-bda1-4850-a22d-d3e6bb832a98', name=_('Travels')),
            [
                SubCategory(uuid='79c7d28f-eed2-4565-9815-1d1887f3ccaf', name=_('Fly')),
                SubCategory(uuid='9812ff36-b3f3-4670-8d4a-b8e9c916bf0d', name=_('Hotel')),
                SubCategory(uuid='15e6f072-bd3e-4591-9963-be2af1888520', name=_('Weekend')),
                SubCategory(uuid='abaca40b-51c9-49c1-95c4-ba93e51bdc40', name=_('Rent')),
            ]
        ], [
            Category(uuid='684f4e8a-aad8-4eb5-980c-fbb8fc28776e', name=_('Vehicle')),
            [
                SubCategory(uuid='7c3492c1-7621-456f-a849-1fc6af829435', name=_('Car')),
                SubCategory(uuid='1f5664c6-2a88-42d0-a554-e271dbe7fd84', name=_('Bike')),
                SubCategory(uuid='669d7604-0d71-48b1-aa4e-6ca52f8923f8', name=_('Boat')),
                SubCategory(uuid='886757aa-e019-4683-b83b-942ca9798e0b', name=_('Plane')),
            ]
        ], [
            Category(uuid='8ef405ac-9109-4ea6-94eb-f068b33c617d', name=_('Games & Toys')),
            [
                SubCategory(uuid='f5f5efc4-b03e-47b9-b485-f85dfb1a2630', name=_('Boys')),
                SubCategory(uuid='39d811f7-707b-4419-8750-b15179d5b3eb', name=_('Girls')),
                SubCategory(uuid='d92fd9d0-a8cd-4d6e-9d8c-24037a2121fe', name=_('Teens')),
                SubCategory(uuid='dc8d1368-55d7-4abc-80c2-28ba1d3d1d3b', name=_('Babies')),
            ]
        ], [
            Category(uuid='14474aee-9ba7-4a0e-816e-e19bab639af9', name=_('Clothes')),
            [
                SubCategory(uuid='01109ac2-e539-45fd-a2a8-b3fff7992933', name=_('Men')),
                SubCategory(uuid='eaf8bc61-e1a1-4181-a679-84c606037922', name=_('Women')),
                SubCategory(uuid='ecf095f8-f3a7-4271-921c-81b1dff714a6', name=_('Kids')),
                SubCategory(uuid='ba170185-892e-400a-b212-1810fc86f204', name=_('Babies')),
            ]
        ],
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Product = get_product_model()
        self.Service = get_service_model()

    def _already_populated(self):
        # return Category.objects.exists()
        return HeaderFilter.objects.filter(id=constants.DEFAULT_HFILTER_PRODUCT).exists()

    def _populate(self):
        super()._populate()
        self._populate_doc_categories()

    def _first_populate(self):
        super()._first_populate()
        self._populate_categories()

    def _populate_doc_categories(self):
        # DocumentCategory.objects.get_or_create(
        #     uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
        #     defaults={
        #         'name': _('Product image'),
        #         'is_custom': False,
        #     },
        # )
        self._save_minions(self.DOC_CATEGORIES)

    def _populate_categories(self):
        # create_cat = Category.objects.create
        # create_subcat = SubCategory.objects.create
        #
        # jewelry = create_cat(name=_('Jewelry'))
        # create_subcat(name=_('Ring'),     category=jewelry)
        # create_subcat(name=_('Bracelet'), category=jewelry)
        # create_subcat(name=_('Necklace'), category=jewelry)
        # create_subcat(name=_('Earrings'), category=jewelry)
        #
        # mobile = create_cat(name=_('Mobile'))
        # create_subcat(name=_('Iphone'),     category=mobile)
        # create_subcat(name=_('Blackberry'), category=mobile)
        # create_subcat(name=_('Samsung'),    category=mobile)
        # create_subcat(name=_('Android'),    category=mobile)
        #
        # electronics = create_cat(name=_('Electronics'))
        # create_subcat(name=_('Laptops'),  category=electronics)
        # create_subcat(name=_('Desktops'), category=electronics)
        # create_subcat(name=_('Tablet'),   category=electronics)
        # create_subcat(name=_('Notebook'), category=electronics)
        #
        # travels = create_cat(name=_('Travels'))
        # create_subcat(name=_('Fly'),      category=travels)
        # create_subcat(name=_('Hotel'),    category=travels)
        # create_subcat(name=_('Week-end'), category=travels)
        # create_subcat(name=_('Rent'),     category=travels)
        #
        # vehicle = create_cat(name=_('Vehicle'))
        # create_subcat(name=_('Car'),   category=vehicle)
        # create_subcat(name=_('Bike'),  category=vehicle)
        # create_subcat(name=_('Boat'),  category=vehicle)
        # create_subcat(name=_('Plane'), category=vehicle)
        #
        # games_toys = create_cat(name=_('Games & Toys'))
        # create_subcat(name=_('Boys'),   category=games_toys)
        # create_subcat(name=_('Girls'),  category=games_toys)
        # create_subcat(name=_('Teens'),  category=games_toys)
        # create_subcat(name=_('Babies'), category=games_toys)
        #
        # clothes = create_cat(name=_('Clothes'))
        # create_subcat(name=_('Men'),    category=clothes)
        # create_subcat(name=_('Women'),  category=clothes)
        # create_subcat(name=_('Kids'),   category=clothes)
        # create_subcat(name=_('Babies'), category=clothes)
        for category, sub_categories in self.CATEGORIES:
            category.save()

            for sub_category in sub_categories:
                sub_category.category = category
                sub_category.save()

    def _populate_header_filters(self):
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_PRODUCT,
            model=self.Product,
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
            model=self.Service,
            name=_('Service view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'images'}),
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'reference'}),
                (EntityCellRegularField, {'name': 'user'}),
            ],
        )

    def _populate_custom_forms(self):
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        create_cfci(descriptor=custom_forms.PRODUCT_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.PRODUCT_EDITION_CFORM)
        create_cfci(descriptor=custom_forms.SERVICE_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.SERVICE_EDITION_CFORM)

    def _populate_search_config(self):
        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(model=self.Product, fields=self.SEARCH['PRODUCT'])
        create_sci(model=self.Service, fields=self.SEARCH['SERVICE'])

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Management')},
            role=None, superuser=False,
            defaults={'order': 50},
        )[0]

        create_mitem = partial(MenuConfigItem.objects.create, parent=menu_container)
        create_mitem(entry_id=menu.ProductsEntry.id, order=20)
        create_mitem(entry_id=menu.ServicesEntry.id, order=25)

    def _populate_bricks_config(self):
        Product = self.Product
        Service = self.Service
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

            import creme.assistants.bricks as a_bricks

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
