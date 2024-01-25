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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Product = get_product_model()
        self.Service = get_service_model()

    def _already_populated(self):
        # NB: no straightforward way to test that this script has not been already run
        return Category.objects.exists()

    def _populate(self):
        super()._populate()
        self._populate_doc_categories()

    def _first_populate(self):
        super()._first_populate()
        self._populate_categories()

    def _populate_doc_categories(self):
        DocumentCategory.objects.get_or_create(
            uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
            defaults={
                'name': _('Product image'),
                'is_custom': False,
            },
        )

    def _populate_categories(self):
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
        create_subcat(name=_('Bike'),  category=vehicle)
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
