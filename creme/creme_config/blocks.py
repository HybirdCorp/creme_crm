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

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import (CremePropertyType, RelationType, CustomField,
                               BlockConfigItem, ButtonMenuItem,
                               CremeAppDroit, CremeDroitEntityType)
from creme_core.gui.block import Block

from creme_config.registry import config_registry

__all__ = ('generic_models_block', 'property_types_block', 'relation_types_block',
           'custom_fields_portal_block', 'custom_fields_block',
           'blocks_config_block', 'button_menu_block',
           'users_block', 'app_credentials_block', 'entity_credentials_block')


_PAGE_SIZE = 12


class GenericModelsBlock(Block):
    id_           = Block.generate_id('creme_config', 'model_config')
    order_by      = 'id'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration de modèle')
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

    def detailview_ajax(self, request, ct_id):
        ct_id = int(ct_id)
        model = ContentType.objects.get_for_id(ct_id).model_class()
        app_name = model._meta.app_label
        model_name_in_url = config_registry.get_app(app_name).get_model_conf(ct_id).name_in_url

        return super(GenericModelsBlock, self).detailview_ajax(request, model=model, model_name=model_name_in_url, app_name=app_name)


class PropertyTypesBlock(Block):
    id_           = Block.generate_id('creme_config', 'property_type')
    order_by      = 'text'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration des types de propriété')
    template_name = 'creme_config/templatetags/block_property_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, CremePropertyType.objects.all(),
                                                            update_url='/creme_config/property_types/reload/'))


class RelationTypesBlock(Block):
    id_           = Block.generate_id('creme_config', 'relation_type')
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration des types de relation')
    template_name = 'creme_config/templatetags/block_relation_types.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, RelationType.get_customs().filter(pk__contains='-subject_'),
                                                            update_url='/creme_config/relation_types/reload/'))


class CustomFieldsPortalBlock(Block):
    id_           = Block.generate_id('creme_config', 'custom_fields_portal')
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration générale des champs personnalisés')
    template_name = 'creme_config/templatetags/block_custom_fields_portal.html'

    def detailview_display(self, context):
        ct_ids = CustomField.objects.distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_config/custom_fields/portal/reload/'))


class CustomFieldsBlock(Block):
    id_           = Block.generate_id('creme_config', 'custom_fields')
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration des champs personnalisés')
    template_name = 'creme_config/templatetags/block_custom_fields.html'

    def detailview_display(self, context):
        ct = context['content_type'] #ct_id instead ??

        return self._render(self.get_block_template_context(context, CustomField.objects.filter(content_type=ct),
                                                            update_url='/creme_config/custom_fields/%s/reload/' % ct.id,
                                                            ct=ct))

    def detailview_ajax(self, request, ct_id):
        ct = ContentType.objects.get_for_id(ct_id) #get_ct_or_404() ??

        return super(CustomFieldsBlock, self).detailview_ajax(request, content_type=ct)


class UsersBlock(Block):
    id_           = Block.generate_id('creme_config', 'user')
    order_by      = 'username'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration des utilisateurs')
    template_name = 'creme_config/templatetags/block_users.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, User.objects.all(),
                                                            update_url='/creme_config/users/reload/'))


class BlocksConfigBlock(Block):
    id_           = Block.generate_id('creme_config', 'blocksconfig')
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = _(u'Configuration des blocs')
    template_name = 'creme_config/templatetags/block_blocksconfig.html'

    def detailview_display(self, context):
        ct_ids = BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_config/blocks/reload/'))


class ButtonMenuBlock(Block):
    id_           = Block.generate_id('creme_config', 'button_menu')
    page_size     = _PAGE_SIZE - 1 #'-1' because there is always the line for default config on each page
    verbose_name  = _(u'Configuration du menu bouton')
    template_name = 'creme_config/templatetags/block_button_menu.html'

    def detailview_display(self, context):
        ct_ids = ButtonMenuItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(context, ContentType.objects.filter(pk__in=ct_ids),
                                                            update_url='/creme_config/button_menu/reload/'))


class AppCredentialsBlock(Block):
    id_           = Block.generate_id('creme_config', 'app_credentials')
    order_by      = 'name_app'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration des droits des applications')
    template_name = 'creme_config/templatetags/block_app_credentials.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, CremeAppDroit.objects.all(),
                                                            update_url='/creme_config/roles/app_credentials/reload/'))


class EntityCredentialsBlock(Block):
    id_           = Block.generate_id('creme_config', 'entity_credentials')
    order_by      = 'content_type'
    page_size     = _PAGE_SIZE
    verbose_name  = _(u'Configuration des droits des entités')
    template_name = 'creme_config/templatetags/block_entity_credentials.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context, CremeDroitEntityType.objects.all(),
                                                            update_url='/creme_config/roles/entity_credentials/reload/'))


generic_models_block       = GenericModelsBlock()
property_types_block       = PropertyTypesBlock()
relation_types_block       = RelationTypesBlock()
custom_fields_portal_block = CustomFieldsPortalBlock()
custom_fields_block        = CustomFieldsBlock()
blocks_config_block        = BlocksConfigBlock()
button_menu_block          = ButtonMenuBlock()
users_block                = UsersBlock()
app_credentials_block      = AppCredentialsBlock()
entity_credentials_block   = EntityCredentialsBlock()
