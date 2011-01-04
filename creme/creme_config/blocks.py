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

from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.gui.block import Block, QuerysetBlock, BlocksManager
from creme_core.utils import jsonify

from creme_config.registry import config_registry
from creme_config.constants import MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL
from creme_config.models.config_models import CremeKVConfig

_PAGE_SIZE = 12


class GenericModelsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'model_config')
    dependencies  = (CremeModel,)
    order_by      = 'id'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Model configuration')
    template_name = 'creme_config/templatetags/block_models.html'

    def detailview_display(self, context):
        model = context['model']

        try:
            self.order_by = model._meta.ordering[0]
        except IndexError:
            pass

        return self._render(self.get_block_template_context(context, model.objects.all(),
                                                            update_url='/creme_config/models/%s/reload/' % ContentType.objects.get_for_model(model).id,
                                                            model=model,
                                                            model_name=context['model_name'],
                                                            app_name=context['app_name']))

    @jsonify
    def detailview_ajax(self, request, ct_id, model, app_name):
        context = RequestContext(request)
        context.update({
                'model':      model,
                'model_name': config_registry.get_app(app_name).get_model_conf(ct_id).name_in_url,
                'app_name':   app_name,
            })

        return [(self.id_, self.detailview_display(context))]


class PropertyTypesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'property_types')
    dependencies  = (CremePropertyType,)
    order_by      = 'text'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Property types configuration')
    template_name = 'creme_config/templatetags/block_property_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, CremePropertyType.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class RelationTypesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'relation_types')
    dependencies  = (RelationType,)
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'List of standard relation types')
    template_name = 'creme_config/templatetags/block_relation_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, RelationType.objects.filter(is_custom=False, pk__contains='-subject_'),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            custom=False,
                                                            ))

class CustomRelationTypesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'custom_relation_types')
    dependencies  = (RelationType,)
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Custom relation types configuration')
    template_name = 'creme_config/templatetags/block_relation_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, RelationType.objects.filter(is_custom=True, pk__contains='-subject_'),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            custom=True,
                                                            ))

class CustomFieldsPortalBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'custom_fields_portal')
    dependencies  = (CustomField,)
    page_size     = _PAGE_SIZE
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
        ct = context['content_type'] #ct_id instead ??

        return self._render(self.get_block_template_context(context, CustomField.objects.filter(content_type=ct),
                                                            update_url='/creme_config/custom_fields/%s/reload/' % ct.id,
                                                            ct=ct))

    #TODO: factorise ?? (see emails_block/sms_block) move code to view ??
    @jsonify
    def detailview_ajax(self, request, ct_id):
        context = RequestContext(request)
        context['content_type'] = ContentType.objects.get_for_id(ct_id) #get_ct_or_404() ??

        return [(self.id_, self.detailview_display(context))]


class UsersBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'users')
    dependencies  = (User,)
    order_by      = 'username'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Users configuration')
    template_name = 'creme_config/templatetags/block_users.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, User.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class BlocksConfigBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'blocks_config')
    dependencies  = (BlockConfigItem,)
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = _(u'Blocks configuration')
    template_name = 'creme_config/templatetags/block_blocksconfig.html'

    def detailview_display(self, context):
        ct_ids = BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class RelationBlocksConfigBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'relation_blocks_config')
    dependencies  = (RelationBlockItem, BlockConfigItem) #BlockConfigItem because they can be deleted if we delete a RelationBlockItem
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Relation blocks configuration')
    template_name = 'creme_config/templatetags/block_relationblocksconfig.html'

    def detailview_display(self, context):
        ct_ids = BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, RelationBlockItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))

class InstanceBlocksConfigBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'instance_blocks_config')
    dependencies  = (InstanceBlockConfigItem, BlockConfigItem) #BlockConfigItem because they can be deleted if we delete a InstanceBlockConfigItem
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Instance blocks configuration')
    template_name = 'creme_config/templatetags/block_instanceblocksconfig.html'

    def detailview_display(self, context):

        return self._render(self.get_block_template_context(context, InstanceBlockConfigItem.objects.all(),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                            ))


class ButtonMenuBlock(QuerysetBlock):
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


class SearchConfigBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'searchconfig')
    dependencies  = (SearchConfigItem,)
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Search configuration')
    template_name = 'creme_config/templatetags/block_searchconfig.html'
    order_by      = 'content_type'

    def detailview_display(self, context):
        ctx = self.get_block_template_context(context, SearchConfigItem.objects.all(),
                                              update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                              )

        #NB: DB optimisation
        SearchConfigItem.populate_searchfields(ctx['page'].object_list)

        return self._render(ctx)
#        return self._render(self.get_block_template_context(context, SearchConfigItem.objects.select_related('searchfield_set'),
#                                              update_url='/creme_config/blocks/reload/'))


class UserRolesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'user_roles')
    dependencies  = (UserRole,)
    order_by      = 'name'
    page_size     = _PAGE_SIZE
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

    def detailview_display(self, context):
        request = context['request']
        user    = request.user

        return self._render(self.get_block_template_context(context,
                                                            PreferedMenuItem.objects.filter(user=user),
                                                            page_size=self.page_size,
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                                           ))

class MobileSyncConfigBlock(Block):
    id_           = Block.generate_id('creme_config', 'mobile_sync')
    dependencies  = ()
    verbose_name  = _(u'Mobile synchronization')
    template_name = 'creme_config/templatetags/block_mobile_sync.html'

    def detailview_display(self, context):
        try:
            server_url = CremeKVConfig.objects.get(pk=MAPI_SERVER_URL)
        except CremeKVConfig.DoesNotExist:
            server_url = CremeKVConfig(id=MAPI_SERVER_URL, value="")
            server_url.save()

        try:
            server_domain = CremeKVConfig.objects.get(pk=MAPI_DOMAIN)
        except CremeKVConfig.DoesNotExist:
            server_domain = CremeKVConfig(id=MAPI_DOMAIN, value="")
            server_domain.save()

        try:
    #        server_ssl = CremeKVConfig.objects.get(pk=MAPI_SERVER_SSL)
            is_server_ssl = CremeKVConfig.get_int_value(MAPI_SERVER_SSL)
        except CremeKVConfig.DoesNotExist:
            server_ssl = CremeKVConfig(id=MAPI_SERVER_SSL, value="0")
            server_ssl.save()
            is_server_ssl = 0
        except ValueError:
            is_server_ssl = 0

        return self._render(self.get_block_template_context(context,
                                                            url=server_url.value,
                                                            domain=server_domain.value,
                                                            ssl=bool(is_server_ssl),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,))

generic_models_block = GenericModelsBlock()
custom_fields_block  = CustomFieldsBlock()

blocks_list = (
        generic_models_block,
        PropertyTypesBlock(),
        RelationTypesBlock(),
        CustomRelationTypesBlock(),
        CustomFieldsPortalBlock(),
        custom_fields_block,
        BlocksConfigBlock(),
        RelationBlocksConfigBlock(),
        ButtonMenuBlock(),
        UsersBlock(),
        SearchConfigBlock(),
        InstanceBlocksConfigBlock(),
        UserRolesBlock(),
        DefaultCredentialsBlock(),
        UserPreferedMenusBlock(),
        MobileSyncConfigBlock(),
    )
