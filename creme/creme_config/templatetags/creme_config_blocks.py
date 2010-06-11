# -*- coding: utf-8 -*-

from django.template import Library

#TODO: use * and __all__ ???
from creme_config.blocks import (generic_models_block, property_types_block, relation_types_block,
                                 users_block, blocks_config_block, button_menu_block,
                                 app_credentials_block, entity_credentials_block)


register = Library()

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_model_config(context):
    return {'blocks': [generic_models_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_property_types(context):
    return {'blocks': [property_types_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_relation_types(context):
    return {'blocks': [relation_types_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_users(context):
    return {'blocks': [users_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_blocksconfig(context):
    return {'blocks': [blocks_config_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_app_credentials(context):
    return {'blocks': [app_credentials_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_entity_credentials(context):
    return {'blocks': [entity_credentials_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_buttonmenu_config(context):
    return {'blocks': [button_menu_block.detailview_display(context)]}
