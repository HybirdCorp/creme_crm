################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

Product = get_product_model()
Service = get_service_model()

# UUIDs for instances which can be deleted
UUID_CATEGORY_JEWELRY     = '3fb0ef3c-45d0-40bd-8e71-b1ab49fca8d3'
UUID_CATEGORY_MOBILE      = '74c91fab-d671-4054-984f-ba395d7dffcb'
UUID_CATEGORY_ELECTRONICS = '69084c8f-068c-41e3-80e3-42ed312e9815'
UUID_CATEGORY_TRAVELS     = '213e14fa-bda1-4850-a22d-d3e6bb832a98'
UUID_CATEGORY_VEHICLE     = '684f4e8a-aad8-4eb5-980c-fbb8fc28776e'
UUID_CATEGORY_GAMES       = '8ef405ac-9109-4ea6-94eb-f068b33c617d'
UUID_CATEGORY_CLOTHES     = '14474aee-9ba7-4a0e-816e-e19bab639af9'

UUID_SUBCAT_JEWELRY_RING     = '2d6555fe-4c25-4098-8128-25395cf2c10b'
UUID_SUBCAT_JEWELRY_BRACELET = 'c160d58f-6878-4dd6-87d6-ee05db310f3a'
UUID_SUBCAT_JEWELRY_NECKLACE = '83b79894-122e-4212-bf18-929573f57c74'
UUID_SUBCAT_JEWELRY_EARRINGS = '6514cb2a-ee59-4abf-bdef-92488fac3a42'

UUID_SUBCAT_MOBILE_IPHONE     = '2abfa34f-d30f-4629-9a45-8cd63ce0a362'
UUID_SUBCAT_MOBILE_BLACKBERRY = '4c55bae2-44d3-44ca-aade-e8433339f2aa'
UUID_SUBCAT_MOBILE_SAMSUNG    = '5fc12768-bc62-4412-a9d4-91aa9967bfac'
UUID_SUBCAT_MOBILE_ANDROID    = '62e549a1-f132-4c82-a836-e8d94ee8b29b'

UUID_SUBCAT_ELECTRONICS_LAPTOPS  = '25f7c8db-a0d1-42af-a342-97727a2229fd'
UUID_SUBCAT_ELECTRONICS_DESKTOPS = '6e3c21d1-f81e-492c-b2ce-da1fbc46727f'
UUID_SUBCAT_ELECTRONICS_TABLET   = '13463841-90df-4036-b830-62ad75668213'
UUID_SUBCAT_ELECTRONICS_NOTEBOOK = '3a14d682-77b5-43b7-9b9c-8db9bcd44b0d'

UUID_SUBCAT_TRAVELS_FLY     = '79c7d28f-eed2-4565-9815-1d1887f3ccaf'
UUID_SUBCAT_TRAVELS_HOTEL   = '9812ff36-b3f3-4670-8d4a-b8e9c916bf0d'
UUID_SUBCAT_TRAVELS_WEEKEND = '15e6f072-bd3e-4591-9963-be2af1888520'
UUID_SUBCAT_TRAVELS_RENT    = 'abaca40b-51c9-49c1-95c4-ba93e51bdc40'

UUID_SUBCAT_VEHICLE_CAR   = '7c3492c1-7621-456f-a849-1fc6af829435'
UUID_SUBCAT_VEHICLE_BIKE  = '1f5664c6-2a88-42d0-a554-e271dbe7fd84'
UUID_SUBCAT_VEHICLE_BOAT  = '669d7604-0d71-48b1-aa4e-6ca52f8923f8'
UUID_SUBCAT_VEHICLE_PLANE = '886757aa-e019-4683-b83b-942ca9798e0b'

UUID_SUBCAT_GAMES_CARS   = '0b846e9f-6523-4a08-b7c1-a9017378df1d'
UUID_SUBCAT_GAMES_DOLLS  = 'd97d1e98-d29a-4e45-9285-e03d6f460271'
UUID_SUBCAT_GAMES_PUZZLE = '6df6be5e-d275-4c4a-9bda-f9e527b7db70'
UUID_SUBCAT_GAMES_BABIES = 'dc8d1368-55d7-4abc-80c2-28ba1d3d1d3b'

UUID_SUBCAT_CLOTHES_MEN    = '01109ac2-e539-45fd-a2a8-b3fff7992933'
UUID_SUBCAT_CLOTHES_WOMEN  = 'eaf8bc61-e1a1-4181-a679-84c606037922'
UUID_SUBCAT_CLOTHES_UNISEX = '9c9e97bd-3fc4-4d6a-bf61-1e750d03154a'
UUID_SUBCAT_CLOTHES_KIDS   = 'ecf095f8-f3a7-4271-921c-81b1dff714a6'
UUID_SUBCAT_CLOTHES_BABIES = 'ba170185-892e-400a-b212-1810fc86f204'


class Populator(BasePopulator):
    dependencies = ['creme_core', 'documents']

    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_PRODUCT,
            model=Product,
            name=_('Product view'),
            cells=[
                (EntityCellRegularField, 'images'),
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'code'),
                (EntityCellRegularField, 'user'),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_SERVICE,
            model=Service,
            name=_('Service view'),
            cells=[
                (EntityCellRegularField, 'images'),
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'reference'),
                (EntityCellRegularField, 'user'),
            ],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.PRODUCT_CREATION_CFORM,
        custom_forms.PRODUCT_EDITION_CFORM,
        custom_forms.SERVICE_CREATION_CFORM,
        custom_forms.SERVICE_EDITION_CFORM,
    ]
    # SEARCH = {
    #     'PRODUCT': [
    #         'name', 'description', 'category__name', 'sub_category__name',
    #     ],
    #     'SERVICE': [
    #         'name', 'description', 'category__name', 'sub_category__name',
    #     ],
    # }
    SEARCH = [
        SearchConfigItem.objects.builder(
            model=Product,
            fields=['name', 'description', 'category__name', 'sub_category__name'],
        ),
        SearchConfigItem.objects.builder(
            model=Service,
            fields=['name', 'description', 'category__name', 'sub_category__name'],
        ),
    ]
    DOC_CATEGORIES = [
        DocumentCategory(
            uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
            name=_('Product image'),
            is_custom=False,
        ),
    ]
    CATEGORIES = [
        [
            Category(uuid=UUID_CATEGORY_JEWELRY, name=_('Jewelry')),
            [
                SubCategory(uuid=UUID_SUBCAT_JEWELRY_RING,     name=_('Ring')),
                SubCategory(uuid=UUID_SUBCAT_JEWELRY_BRACELET, name=_('Bracelet')),
                SubCategory(uuid=UUID_SUBCAT_JEWELRY_NECKLACE, name=_('Necklace')),
                SubCategory(uuid=UUID_SUBCAT_JEWELRY_EARRINGS, name=_('Earrings')),
            ]
        ], [
            Category(uuid=UUID_CATEGORY_MOBILE, name=_('Mobile')),
            [
                SubCategory(uuid=UUID_SUBCAT_MOBILE_IPHONE,     name=_('Iphone')),
                SubCategory(uuid=UUID_SUBCAT_MOBILE_BLACKBERRY, name=_('Blackberry')),
                SubCategory(uuid=UUID_SUBCAT_MOBILE_SAMSUNG,    name=_('Samsung')),
                SubCategory(uuid=UUID_SUBCAT_MOBILE_ANDROID,    name=_('Android')),
            ]
        ], [
            Category(uuid=UUID_CATEGORY_ELECTRONICS, name=_('Electronics')),
            [
                SubCategory(uuid=UUID_SUBCAT_ELECTRONICS_LAPTOPS,  name=_('Laptops')),
                SubCategory(uuid=UUID_SUBCAT_ELECTRONICS_DESKTOPS, name=_('Desktops')),
                SubCategory(uuid=UUID_SUBCAT_ELECTRONICS_TABLET,   name=_('Tablet')),
                SubCategory(uuid=UUID_SUBCAT_ELECTRONICS_NOTEBOOK, name=_('Notebook')),
            ]
        ], [
            Category(uuid=UUID_CATEGORY_TRAVELS, name=_('Travels')),
            [
                SubCategory(uuid=UUID_SUBCAT_TRAVELS_FLY,     name=_('Fly')),
                SubCategory(uuid=UUID_SUBCAT_TRAVELS_HOTEL,   name=_('Hotel')),
                SubCategory(uuid=UUID_SUBCAT_TRAVELS_WEEKEND, name=_('Weekend')),
                SubCategory(uuid=UUID_SUBCAT_TRAVELS_RENT,    name=_('Rent')),
            ]
        ], [
            Category(uuid=UUID_CATEGORY_VEHICLE, name=_('Vehicle')),
            [
                SubCategory(uuid=UUID_SUBCAT_VEHICLE_CAR,   name=_('Car')),
                SubCategory(uuid=UUID_SUBCAT_VEHICLE_BIKE,  name=_('Bike')),
                SubCategory(uuid=UUID_SUBCAT_VEHICLE_BOAT,  name=_('Boat')),
                SubCategory(uuid=UUID_SUBCAT_VEHICLE_PLANE, name=_('Plane')),
            ]
        ], [
            Category(uuid=UUID_CATEGORY_GAMES, name=_('Games & Toys')),
            [
                SubCategory(uuid=UUID_SUBCAT_GAMES_CARS,   name=_('Cars')),
                SubCategory(uuid=UUID_SUBCAT_GAMES_DOLLS,  name=_('Dolls')),
                SubCategory(uuid=UUID_SUBCAT_GAMES_PUZZLE, name=_('Puzzle')),
                SubCategory(uuid=UUID_SUBCAT_GAMES_BABIES, name=_('Babies')),
            ]
        ], [
            Category(uuid=UUID_CATEGORY_CLOTHES, name=_('Clothes')),
            [
                SubCategory(uuid=UUID_SUBCAT_CLOTHES_MEN,    name=_('Men')),
                SubCategory(uuid=UUID_SUBCAT_CLOTHES_WOMEN,  name=_('Women')),
                SubCategory(uuid=UUID_SUBCAT_CLOTHES_UNISEX, name=_('Unisex')),
                SubCategory(uuid=UUID_SUBCAT_CLOTHES_KIDS,   name=_('Kids')),
                SubCategory(uuid=UUID_SUBCAT_CLOTHES_BABIES, name=_('Babies')),
            ]
        ],
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.Product = get_product_model()
        # self.Service = get_service_model()
        self.Product = Product
        self.Service = Service

    def _already_populated(self):
        return HeaderFilter.objects.filter(id=constants.DEFAULT_HFILTER_PRODUCT).exists()

    def _populate(self):
        super()._populate()
        self._populate_doc_categories()

    def _first_populate(self):
        super()._first_populate()
        self._populate_categories()

    def _populate_doc_categories(self):
        self._save_minions(self.DOC_CATEGORIES)

    def _populate_categories(self):
        for category, sub_categories in self.CATEGORIES:
            category.save()

            for sub_category in sub_categories:
                sub_category.category = category
                sub_category.save()

    # def _populate_header_filters(self):
    #     create_hf = HeaderFilter.objects.create_if_needed
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_PRODUCT,
    #         model=self.Product,
    #         name=_('Product view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'images'}),
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'code'}),
    #             (EntityCellRegularField, {'name': 'user'}),
    #         ],
    #     )
    #
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_SERVICE,
    #         model=self.Service,
    #         name=_('Service view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'images'}),
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'reference'}),
    #             (EntityCellRegularField, {'name': 'user'}),
    #         ],
    #     )

    # def _populate_search_config(self):
    #     create_sci = SearchConfigItem.objects.create_if_needed
    #     create_sci(model=self.Product, fields=self.SEARCH['PRODUCT'])
    #     create_sci(model=self.Service, fields=self.SEARCH['SERVICE'])

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
