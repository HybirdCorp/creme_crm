# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from creme_core.gui.block import Block, QuerysetBlock

from creme_config.models import  SettingValue

_PAGE_SIZE = 12


class GenericModelsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'model_config')
    dependencies  = (CremeModel,)
    order_by      = 'id'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Model configuration')
    template_name = 'creme_config/templatetags/block_models.html'

    def detailview_display(self, context):
        #NB: credentials are OK : we are sure to use the custom reloading view
        #    if 'model', 'model_name' etc... are in the context
        model = context['model']

        try:
            self.order_by = model._meta.ordering[0]
        except IndexError:
            pass

        return self._render(self.get_block_template_context(context, model.objects.all(),
                                                            update_url='/creme_config/models/%s/reload/' % ContentType.objects.get_for_model(model).id,
                                                            model=model,
                                                            model_name=context['model_name'],
                                                            app_name=context['app_name']
                                                           ))


class SettingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'settings')
    dependencies  = (SettingValue,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'App settings'
    template_name = 'creme_config/templatetags/block_settings.html'

    def detailview_display(self, context):
        app_name = context['app_name']

        return self._render(self.get_block_template_context(context,
                                                            SettingValue.objects.filter(key__app_label=app_name, key__hidden=False, user=None),
                                                            update_url='/creme_config/settings/%s/reload/' % app_name,
                                                            app_name=app_name,
                                                           )
                           )


class _ConfigAdminBlock(QuerysetBlock):
    page_size  = _PAGE_SIZE
    permission = 'creme_config.can_admin' #NB: used by the view creme_core.views.blocks.reload_basic


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


class BlocksConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'blocks_config')
    dependencies  = (BlockConfigItem,)
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = _(u'Blocks configuration')
    template_name = 'creme_config/templatetags/block_blocksconfig.html'

    def detailview_display(self, context):
        ct_user = ContentType.objects.get_for_model(User)
        #Why .exclude(content_type__in=[...]) doesn't work ?...
        ct_ids = BlockConfigItem.objects.exclude(content_type=None)\
                                        .exclude(content_type=ct_user)\
                                        .distinct()\
                                        .values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class RelationBlocksConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'relation_blocks_config')
    dependencies  = (RelationBlockItem, BlockConfigItem) #BlockConfigItem because they can be deleted if we delete a RelationBlockItem
    verbose_name  = _(u'Relation blocks configuration')
    template_name = 'creme_config/templatetags/block_relationblocksconfig.html'

    def detailview_display(self, context):
        ct_ids = BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, RelationBlockItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class InstanceBlocksConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'instance_blocks_config')
    dependencies  = (InstanceBlockConfigItem, BlockConfigItem) #BlockConfigItem because they can be deleted if we delete a InstanceBlockConfigItem
    verbose_name  = _(u'Instance blocks configuration')
    template_name = 'creme_config/templatetags/block_instanceblocksconfig.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, InstanceBlockConfigItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class ButtonMenuBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'button_menu')
    dependencies  = (ButtonMenuItem,)
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = _(u'Button menu configuration')
    template_name = 'creme_config/templatetags/block_button_menu.html'

    def detailview_display(self, context):
        ct_ids = ButtonMenuItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class SearchConfigBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'searchconfig')
    dependencies  = (SearchConfigItem,)
    verbose_name  = _(u'Search configuration')
    template_name = 'creme_config/templatetags/block_searchconfig.html'
    order_by      = 'content_type'

    def detailview_display(self, context):
        btc = self.get_block_template_context(context, SearchConfigItem.objects.all(),
                                              update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                             )

        #NB: DB optimisation
        SearchConfigItem.populate_searchfields(btc['page'].object_list)

        return self._render(btc)


class UserRolesBlock(_ConfigAdminBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'user_roles')
    dependencies  = (UserRole,)
    order_by      = 'name'
    verbose_name  = _(u'User roles configuration')
    template_name = 'creme_config/templatetags/block_user_roles.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, UserRole.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class DefaultCredentialsBlock(Block):
    id_           = Block.generate_id('creme_config', 'default_credentials')
    dependencies  = (EntityCredentials,)
    verbose_name  = _(u'Default credentials')
    template_name = 'creme_config/templatetags/block_default_credentials.html'
    permission    = 'creme_config.can_admin' #NB: used by the view creme_core.views.blocks.reload_basic

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context,
                                                            creds=EntityCredentials.get_default_creds(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))


class UserPreferedMenusBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'user_prefered_menus')
    dependencies  = ()
    verbose_name  = _(u'My prefered menus')
    template_name = 'creme_config/templatetags/block_user_prefered_menus.html'
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
        CustomFieldsPortalBlock(),
        custom_fields_block,
        BlocksConfigBlock(),
        RelationBlocksConfigBlock(),
        ButtonMenuBlock(),
        UsersBlock(),
        TeamsBlock(),
        SearchConfigBlock(),
        InstanceBlocksConfigBlock(),
        UserRolesBlock(),
        DefaultCredentialsBlock(),
        UserPreferedMenusBlock(),
    )
