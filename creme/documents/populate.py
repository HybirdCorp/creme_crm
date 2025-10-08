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
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

import creme.creme_core.bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
)

from . import (
    bricks,
    constants,
    custom_forms,
    folder_model_is_custom,
    get_document_model,
    get_folder_model,
    menu,
)
from .models import FolderCategory

logger = logging.getLogger(__name__)

Document = get_document_model()
Folder = get_folder_model()


class Populator(BasePopulator):
    dependencies = ['creme_core']

    RELATION_TYPES = [
        RelationType.objects.builder(
            id=constants.REL_SUB_RELATED_2_DOC,
            predicate=_('related to the document'),
        ).symmetric(
            id=constants.REL_OBJ_RELATED_2_DOC,
            predicate=_('document related to'),
            models=[Document],
        ),
    ]
    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_FOLDER,
            model=Folder,
            name=_('Folder view'),
            cells=[
                (EntityCellRegularField, 'title'),
                (EntityCellRegularField, 'description'),
                (EntityCellRegularField, 'category'),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_DOCUMENT,
            model=Document,
            name=_('Document view'),
            cells=[
                (EntityCellRegularField, 'title'),
                (EntityCellRegularField, 'linked_folder__title'),
                (EntityCellRegularField, 'mime_type'),
            ],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.FOLDER_CREATION_CFORM,
        custom_forms.FOLDER_EDITION_CFORM,
        custom_forms.DOCUMENT_CREATION_CFORM,
        custom_forms.DOCUMENT_EDITION_CFORM,
    ]
    # SEARCH = {
    #     'FOLDER': ['title', 'description', 'category__name'],
    #     'DOCUMENT': [
    #         'title', 'description', 'linked_folder__title', 'categories__name',
    #     ],
    # }
    SEARCH = [
        SearchConfigItem.objects.builder(
            model=Folder, fields=['title', 'description', 'category__name'],
        ),
        SearchConfigItem.objects.builder(
            model=Document,
            fields=['title', 'description', 'linked_folder__title', 'categories__name'],
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.Document = get_document_model()
        # self.Folder   = get_folder_model()
        self.Document = Document
        self.Folder   = Folder

        self.entities_category = None

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_RELATED_2_DOC,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_folder_categories()
        self._populate_folders()

    def _populate_folder_categories(self):
        self.entities_category = FolderCategory.objects.get_or_create(
            uuid=constants.UUID_FOLDER_CAT_ENTITIES,
            defaults={
                'name': _('Documents related to entities'),
                'is_custom': False,
            },
        )[0]

    def _populate_folders(self):
        assert self.entities_category is not None

        if folder_model_is_custom():
            return

        user = get_user_model().objects.get_admin()

        get_create_folder = self.Folder.objects.get_or_create
        get_create_folder(
            uuid=constants.UUID_FOLDER_RELATED2ENTITIES,
            defaults={
                'user':        user,
                'title':       settings.SOFTWARE_LABEL,
                'category':    self.entities_category,
                'description': _(
                    'Folder containing all the documents related to entities'
                ),
            },
        )
        get_create_folder(
            uuid=constants.UUID_FOLDER_IMAGES,
            defaults={
                'user':  user,
                'title': _('Images'),
            },
        )

    # def _populate_relation_types(self):
    #     RelationType.objects.smart_update_or_create(
    #         (constants.REL_SUB_RELATED_2_DOC, _('related to the document')),
    #         (constants.REL_OBJ_RELATED_2_DOC, _('document related to'),      [self.Document])
    #     )

    def _populate_entity_filters(self):
        EntityFilter.objects.smart_update_or_create(
            constants.EFILTER_IMAGES, name=_('Images'), model=self.Document,
            is_custom=False, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=self.Document,
                    operator=operators.StartsWithOperator,
                    field_name='mime_type__name',
                    values=[constants.MIMETYPE_PREFIX_IMG],
                ),
            ],
        )

    # def _populate_header_filters_for_document(self):
    #     HeaderFilter.objects.create_if_needed(
    #         pk=constants.DEFAULT_HFILTER_DOCUMENT, model=self.Document,
    #         name=_('Document view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'title'}),
    #             (EntityCellRegularField, {'name': 'linked_folder__title'}),
    #             (EntityCellRegularField, {'name': 'mime_type'}),
    #         ],
    #     )
    #
    # def _populate_header_filters_for_folder(self):
    #     HeaderFilter.objects.create_if_needed(
    #         pk=constants.DEFAULT_HFILTER_FOLDER, model=self.Folder,
    #         name=_('Folder view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'title'}),
    #             (EntityCellRegularField, {'name': 'description'}),
    #             (EntityCellRegularField, {'name': 'category'}),
    #         ],
    #     )
    #
    # def _populate_header_filters(self):
    #     self._populate_header_filters_for_document()
    #     self._populate_header_filters_for_folder()

    # def _populate_search_config(self):
    #     create_sci = SearchConfigItem.objects.create_if_needed
    #     create_sci(model=self.Folder,   fields=self.SEARCH['FOLDER'])
    #     create_sci(model=self.Document, fields=self.SEARCH['DOCUMENT'])

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Tools')},
            role=None, superuser=False,
            defaults={'order': 100},
        )[0]

        create_mitem = partial(MenuConfigItem.objects.create, parent=menu_container)
        create_mitem(entry_id=menu.DocumentsEntry.id, order=10)
        create_mitem(entry_id=menu.FoldersEntry.id,   order=20)

    def _populate_bricks_config_for_folder(self):
        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Folder, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},  # generic info brick
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.ChildFoldersBrick,      'order':  50},
                {'brick': bricks.FolderDocsBrick,        'order':  60},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed'
            ' => we use the assistants blocks on detail view'
        )

        import creme.assistants.bricks as a_bricks

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Folder, 'zone': BrickDetailviewLocation.RIGHT},
            data=[
                {'brick': a_bricks.TodosBrick,        'order': 100},
                {'brick': a_bricks.MemosBrick,        'order': 200},
                {'brick': a_bricks.AlertsBrick,       'order': 300},
                {'brick': a_bricks.UserMessagesBrick, 'order': 400},
            ],
        )

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_folder()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()
