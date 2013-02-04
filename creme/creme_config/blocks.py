# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.gui.block import Block, PaginatedBlock, QuerysetBlock
from creme_core.registry import creme_registry

from creme_config.models import  SettingValue

_PAGE_SIZE = 12


class GenericModelsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'model_config')
    dependencies  = (CremeModel,)
    #order_by      = 'id'
    page_size     = _PAGE_SIZE
    verbose_name  = u'Model configuration'
    template_name = 'creme_config/templatetags/block_models.html'
    configurable  = False

    def detailview_display(self, context):
        #NB: credentials are OK : we are sure to use the custom reloading view
        #    if 'model', 'model_name' etc... are in the context
        model = context['model']

        try:
            #self.order_by = model._meta.ordering[0] #TODO: uncomment when the block is not a singleton any more.... (beware if a 'order' field exists - see template)
            order_by = model._meta.ordering[0]
        except IndexError:
            #pass
            order_by = 'id'

        meta = model._meta
        fields = meta.fields
        many_to_many = meta.many_to_many

        colspan = len(fields) + len(meta.many_to_many) + 2 # "2" is for 'edit' & 'delete' actions
        if any(field.name == 'is_custom' for field in fields):
            colspan -= 1

        return self._render(self.get_block_template_context(context, model.objects.order_by(order_by),
                                                            update_url='/creme_config/models/%s/reload/' % ContentType.objects.get_for_model(model).id,
                                                            model=model,
                                                            model_name=context['model_name'],
                                                            app_name=context['app_name'],
                                                            fields=meta.fields,
                                                            many_to_many=meta.many_to_many,
                                                            colspan=colspan,
                                                           ))


class SettingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'settings')
    dependencies  = (SettingValue,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'App settings'
    template_name = 'creme_config/templatetags/block_settings.html'
    configurable  = False

    def detailview_display(self, context):
        app_name = context['app_name']

        return self._render(self.get_block_template_context(context,
                                                            SettingValue.objects.filter(key__app_label=app_name, key__hidden=False, user=None),
                                                            update_url='/creme_config/settings/%s/reload/' % app_name,
                                                            app_name=app_name,
                                                           )
                           )


class _ConfigAdminBlock(QuerysetBlock):
    page_size    = _PAGE_SIZE
    permission   = 'creme_config.can_admin' #NB: used by the view creme_core.views.blocks.reload_basic
    configurable = False


class PropertyTypesBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'property_types')
    dependencies  = (CremePropertyType,)
    order_by      = 'text'
    verbose_name  = _(u'Property types configuration')
    template_name = 'creme_config/templatetags/block_property_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, CremePropertyType.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class RelationTypesBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'relation_types')
    dependencies  = (RelationType,)
    verbose_name  = _(u'List of standard relation types')
    template_name = 'creme_config/templatetags/block_relation_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, RelationType.objects.filter(is_custom=False, pk__contains='-subject_'),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            custom=False,
                                                           ))


class CustomRelationTypesBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'custom_relation_types')
    dependencies  = (RelationType,)
    verbose_name  = _(u'Custom relation types configuration')
    template_name = 'creme_config/templatetags/block_relation_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, RelationType.objects.filter(is_custom=True, pk__contains='-subject_'),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            custom=True,
                                                           ))


class SemiFixedRelationTypesBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'semifixed_relation_types')
    dependencies  = (RelationType,)
    verbose_name  = _(u'List of semi-fixed relation types')
    template_name = 'creme_config/templatetags/block_semifixed_relation_types.html'

    def detailview_display(self, context):
        btc = self.get_block_template_context(context, SemiFixedRelationType.objects.all(),
                                              update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                             )
        entities = [sfrt.object_entity for sfrt in btc['page'].object_list]
        CremeEntity.populate_real_entities(entities)
        #CremeEntity.populate_credentials([entity.get_real_entity() for entity in entities], context['user'])

        return self._render(btc)


class CustomFieldsPortalBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'custom_fields_portal')
    dependencies  = (CustomField,)
    verbose_name  = _(u'General configuration of custom fields')
    template_name = 'creme_config/templatetags/block_custom_fields_portal.html'

    def detailview_display(self, context):
        ct_ids = CustomField.objects.distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class CustomFieldsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'custom_fields')
    dependencies  = (CustomField,)
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Custom fields configuration')
    template_name = 'creme_config/templatetags/block_custom_fields.html'
    configurable  = False

    def detailview_display(self, context):
        #NB: credentials are OK : we are sure to use the custom reloading view if 'content_type' is in the context
        ct = context['content_type'] #ct_id instead ??

        return self._render(self.get_block_template_context(context, CustomField.objects.filter(content_type=ct),
                                                            update_url='/creme_config/custom_fields/%s/reload/' % ct.id,
                                                            ct=ct
                                                           ))


class UsersBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'users')
    dependencies  = (User,)
    order_by      = 'username'
    verbose_name  = _(u'Users configuration')
    template_name = 'creme_config/templatetags/block_users.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, User.objects.filter(is_team=False),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class TeamsBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'teams')
    dependencies  = (User,)
    order_by      = 'username'
    verbose_name  = u'Teams configuration'
    template_name = 'creme_config/templatetags/block_teams.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, User.objects.filter(is_team=True),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class BlockDetailviewLocationsBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'blocks_dv_locations')
    dependencies  = (BlockDetailviewLocation,)
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = u'Blocks locations on detailviews'
    template_name = 'creme_config/templatetags/block_blocklocations.html'
    configurable  = False

    def detailview_display(self, context):
        ct_ids = BlockDetailviewLocation.objects.exclude(content_type=None)\
                                                .distinct()\
                                                .values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class BlockPortalLocationsBlock(PaginatedBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'blocks_portal_locations')
    dependencies  = (BlockPortalLocation,)
    page_size     = _PAGE_SIZE - 2 #'-1' because there is always the line for default config & home config on each page
    verbose_name  = u'Blocks locations on portals'
    template_name = 'creme_config/templatetags/block_blockportallocations.html'
    permission    = 'creme_config.can_admin' #NB: used by the view creme_core.views.blocks.reload_basic
    configurable  = False

    def detailview_display(self, context):
        get_app = creme_registry.get_app
        apps = [get_app(name) for name in BlockPortalLocation.objects.exclude(app_name='creme_core')\
                                                             .distinct()\
                                                             .values_list('app_name', flat=True)
                                  if name
               ]

        return self._render(self.get_block_template_context(context, apps,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class BlockDefaultMypageLocationsBlock(PaginatedBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'blocks_default_mypage_locations')
    dependencies  = (BlockMypageLocation,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'Default blocks locations on "My page"'
    template_name = 'creme_config/templatetags/block_blockdefmypagelocations.html'
    permission    = 'creme_config.can_admin' #NB: used by the view creme_core.views.blocks.reload_basic
    configurable  = False

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context,
                                                            BlockMypageLocation.objects.filter(user=None).order_by('order'),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class BlockMypageLocationsBlock(PaginatedBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'blocks_mypage_locations')
    dependencies  = (BlockMypageLocation,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'Blocks locations on "My page"'
    template_name = 'creme_config/templatetags/block_blockmypagelocations.html'
    permission    = 'creme_config.can_admin' #NB: used by the view creme_core.views.blocks.reload_basic
    configurable  = False

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context,
                                                            BlockMypageLocation.objects.filter(user=context['user']).order_by('order'),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class RelationBlocksConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'relation_blocks_config')
    dependencies  = (RelationBlockItem, BlockDetailviewLocation) #BlockDetailviewLocation because they can be deleted if we delete a RelationBlockItem
    verbose_name  = u'Relation blocks configuration'
    template_name = 'creme_config/templatetags/block_relationblocksconfig.html'

    def detailview_display(self, context):
        #ct_ids = BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)
        return self._render(self.get_block_template_context(context, RelationBlockItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class InstanceBlocksConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'instance_blocks_config')
    dependencies  = (InstanceBlockConfigItem, BlockDetailviewLocation) #BlockDetailviewLocation because they can be deleted if we delete a InstanceBlockConfigItem
    verbose_name  = u'Instance blocks configuration'
    template_name = 'creme_config/templatetags/block_instanceblocksconfig.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, InstanceBlockConfigItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class ButtonMenuBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'button_menu')
    dependencies  = (ButtonMenuItem,)
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = u'Button menu configuration'
    template_name = 'creme_config/templatetags/block_button_menu.html'

    def detailview_display(self, context):
        ct_ids = ButtonMenuItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class SearchConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'searchconfig')
    dependencies  = (SearchConfigItem,)
    verbose_name  = u'Search configuration'
    template_name = 'creme_config/templatetags/block_searchconfig.html'
    order_by      = 'content_type'

    def detailview_display(self, context):
        btc = self.get_block_template_context(context, SearchConfigItem.objects.all(),
                                              update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                             )

        #NB: DB optimisation
        SearchConfigItem.populate_searchfields(btc['page'].object_list)

        return self._render(btc)


class HistoryConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'historyconfig')
    dependencies  = (HistoryConfigItem,)
    verbose_name  = u'History configuration'
    template_name = 'creme_config/templatetags/block_historyconfig.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, HistoryConfigItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                            ))


class UserRolesBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'user_roles')
    dependencies  = (UserRole,)
    order_by      = 'name'
    verbose_name  = u'User roles configuration'
    template_name = 'creme_config/templatetags/block_user_roles.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, UserRole.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class UserPreferedMenusBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'user_prefered_menus')
    dependencies  = ()
    verbose_name  = u'My prefered menus'
    template_name = 'creme_config/templatetags/block_user_prefered_menus.html'
    configurable  = False
    order_by      = 'order'
    permission    = None #NB: used by the view creme_core.views.blocks.reload_basic ; None means 'No special permission required'

    def detailview_display(self, context):
        #NB: credentials OK: user can only view his own settings
        user = context['request'].user

        return self._render(self.get_block_template_context(context,
                                                            PreferedMenuItem.objects.filter(user=user),
                                                            page_size=self.page_size,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))

generic_models_block = GenericModelsBlock()
settings_block       = SettingsBlock()
custom_fields_block  = CustomFieldsBlock()

blocks_list = (
        generic_models_block,
        settings_block,
        PropertyTypesBlock(),
        RelationTypesBlock(),
        CustomRelationTypesBlock(),
        SemiFixedRelationTypesBlock(),
        CustomFieldsPortalBlock(),
        custom_fields_block,
        BlockDetailviewLocationsBlock(),
        BlockPortalLocationsBlock(),
        BlockDefaultMypageLocationsBlock(),
        BlockMypageLocationsBlock(),
        RelationBlocksConfigBlock(),
        InstanceBlocksConfigBlock(),
        ButtonMenuBlock(),
        UsersBlock(),
        TeamsBlock(),
        SearchConfigBlock(),
        HistoryConfigBlock(),
        UserRolesBlock(),
        UserPreferedMenusBlock(),
    )
