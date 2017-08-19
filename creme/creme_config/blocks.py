# -*- coding: utf-8 -*-

import warnings

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from creme.creme_core.gui.block import QuerysetBlock
from creme.creme_core.models import CremeModel, CustomField

from .bricks import (
    _PAGE_SIZE,
    SettingsBrick as SettingsBlock,
    _ConfigAdminBrick as _ConfigAdminBlock,
    PropertyTypesBrick as PropertyTypesBlock,
    RelationTypesBrick as RelationTypesBlock,
    CustomRelationTypesBrick as CustomRelationTypesBlock,
    SemiFixedRelationTypesBrick as SemiFixedRelationTypesBlock,
    FieldsConfigsBrick as FieldsConfigsBlock,
    UsersBrick as UsersBlock,
    TeamsBrick as TeamsBlock,
    BlockDetailviewLocationsBrick as BlockDetailviewLocationsBlock,
    BlockPortalLocationsBrick as BlockPortalLocationsBlock,
    BlockHomeLocationsBrick as BlockHomeLocationsBlock,
    BlockDefaultMypageLocationsBrick as BlockDefaultMypageLocationsBlock,
    BlockMypageLocationsBrick as BlockMypageLocationsBlock,
    RelationBlocksConfigBrick as RelationBlocksConfigBlock,
    InstanceBlocksConfigBrick as InstanceBlocksConfigBlock,
    CustomBlocksConfigBrick as CustomBlocksConfigBlock,
    ButtonMenuBrick as ButtonMenuBlock,
    SearchConfigBrick as SearchConfigBlock,
    HistoryConfigBrick as HistoryConfigBlock,
    UserRolesBrick as UserRolesBlock,
    UserPreferredMenusBrick as UserPreferedMenusBlock,
    UserSettingValuesBrick as UserSettingValuesBlock,
)

warnings.warn('creme_config.blocks is deprecated ; use creme_config.bricks instead.', DeprecationWarning)


class GenericModelsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('creme_config', 'model_config')
    dependencies  = (CremeModel,)
    page_size     = _PAGE_SIZE
    verbose_name  = u'Model configuration'
    template_name = 'creme_config/templatetags/block_models.html'
    configurable  = False

    def detailview_display(self, context):
        # NB: credentials are OK : we are sure to use the custom reloading view
        #     if 'model', 'model_name' etc... are in the context
        model = context['model']

        try:
            order_by = model._meta.ordering[0]
        except IndexError:
            order_by = 'id'

        meta = model._meta
        fields = meta.fields
        many_to_many = meta.many_to_many

        colspan = len(fields) + len(many_to_many) + 2  # "2" is for 'edit' & 'delete' actions
        if any(field.name == 'is_custom' for field in fields):
            colspan -= 1

        return self._render(self.get_block_template_context(
                    context, model.objects.order_by(order_by),
                    update_url='/creme_config/models/%s/reload/' % ContentType.objects.get_for_model(model).id,
                    model=model,
                    model_name=context['model_name'],
                    app_name=context['app_name'],
                    fields=meta.fields,
                    many_to_many=many_to_many,
                    colspan=colspan,
        ))


class CustomFieldsPortalBlock(_ConfigAdminBlock):
    id_           = _ConfigAdminBlock.generate_id('creme_config', 'custom_fields_portal')
    dependencies  = (CustomField,)
    verbose_name  = u'General configuration of custom fields'
    template_name = 'creme_config/templatetags/block_custom_fields_portal.html'

    def detailview_display(self, context):
        ct_ids = CustomField.objects.distinct().values_list('content_type_id', flat=True)

        return self._render(self.get_block_template_context(
                    context, ContentType.objects.filter(pk__in=ct_ids),
                    # update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                    update_url=reverse('creme_core__reload_blocks', args=(self.id_,)),
        ))


# class CustomFieldsBlock(QuerysetBlock):
#     id_           = QuerysetBlock.generate_id('creme_config', 'custom_fields')
#     dependencies  = (CustomField,)
#     page_size     = _PAGE_SIZE
#     verbose_name  = u'Custom fields configuration'
#     template_name = 'creme_config/templatetags/block_custom_fields.html'
#     configurable  = False
#
#     def detailview_display(self, context):
#         # NB: credentials are OK : we are sure to use the custom reloading view if 'content_type' is in the context
#         ct = context['content_type']  # ct_id instead ??
#
#         btc = self.get_block_template_context(
#                     context, CustomField.objects.filter(content_type=ct),
#                     # update_url='/creme_config/custom_fields/%s/reload/' % ct.id,
#                     update_url=reverse('creme_config__reload_custom_field_block', args=(ct.id,)),
#                     ct=ct,
#         )
#
#         # Retrieve & cache Enum values (in order to display them of course)
#         enums_types = {CustomField.ENUM, CustomField.MULTI_ENUM}
#         enums_cfields = [cfield
#                             for cfield in btc['page'].object_list
#                                 if cfield.field_type in enums_types
#                         ]
#         evalues_map = defaultdict(list)
#
#         for enum_value in CustomFieldEnumValue.objects.filter(custom_field__in=enums_cfields):
#             evalues_map[enum_value.custom_field_id].append(enum_value.value)
#
#         for enums_cfield in enums_cfields:
#             enums_cfield.enum_values = evalues_map[enums_cfield.id]
#
#         return self._render(btc)


generic_models_block = GenericModelsBlock()
settings_block = SettingsBlock()
# custom_fields_block  = CustomFieldsBlock()

blocks_list = (
    generic_models_block,
    settings_block,
    PropertyTypesBlock(),
    RelationTypesBlock(),
    CustomRelationTypesBlock(),
    SemiFixedRelationTypesBlock(),
    CustomFieldsPortalBlock(),
    # custom_fields_block,
    FieldsConfigsBlock(),
    BlockDetailviewLocationsBlock(),
    BlockPortalLocationsBlock(),
    BlockHomeLocationsBlock(),
    BlockDefaultMypageLocationsBlock(),
    BlockMypageLocationsBlock(),
    RelationBlocksConfigBlock(),
    InstanceBlocksConfigBlock(),
    FieldsConfigsBlock(),
    CustomBlocksConfigBlock(),
    ButtonMenuBlock(),
    UsersBlock(),
    TeamsBlock(),
    SearchConfigBlock(),
    HistoryConfigBlock(),
    UserRolesBlock(),
    UserPreferedMenusBlock(),
    UserSettingValuesBlock(),
)
