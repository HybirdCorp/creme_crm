import warnings

warnings.warn('creme_config.views.blocks is deprecated ; use creme_config.views.bricks instead.', DeprecationWarning)

from .bricks import *


def add_relation_block(request):
    warnings.warn('creme_config.views.blocks/bricks.add_relation_block() is now deprecated ; '
                  'use bricks.create_rtype_brick() instead.',
                  DeprecationWarning
                 )
    return create_rtype_brick(request)


def edit_ctype_of_relation_block(request, rbi_id, ct_id):
    warnings.warn('creme_config.views.blocks.edit_ctype_of_relation_block() is now deprecated ; '
                  'use bricks.edit_cells_of_rtype_brick() instead.',
                  DeprecationWarning
                 )
    return edit_cells_of_rtype_brick(request, rbi_id, ct_id)


def delete_ctype_of_relation_block(request, rbi_id):
    warnings.warn('creme_config.views.blocks/bricks.delete_ctype_of_relation_block() is now deprecated ; '
                  'use bricks.delete_cells_of_rtype_brick() instead.',
                  DeprecationWarning
                 )
    return delete_cells_of_rtype_brick(request, rbi_id)


def edit_custom_block(request, cbci_id):
    warnings.warn('creme_config.views.blocks/bricks.edit_custom_block() is now deprecated ; '
                  'use bricks.edit_custom_brick() instead.',
                  DeprecationWarning
                 )
    return edit_custom_brick(request, cbci_id)


def delete_relation_block(request):
    warnings.warn('creme_config.views.blocks/bricks.delete_relation_block() is now deprecated ; '
                  'use bricks.delete_rtype_brick() instead.',
                  DeprecationWarning
                 )
    return delete_rtype_brick(request)


def delete_instance_block(request):
    warnings.warn('creme_config.views.blocks/bricks.delete_instance_block() is now deprecated ; '
                  'use bricks.delete_instance_brick() instead.',
                  DeprecationWarning
                 )
    return delete_instance_brick(request)


def delete_custom_block(request):
    warnings.warn('creme_config.views.blocks/bricks.delete_custom_block() is now deprecated ; '
                  'use bricks.delete_custom_brick() instead.',
                  DeprecationWarning
                 )
    return delete_custom_brick(request)
