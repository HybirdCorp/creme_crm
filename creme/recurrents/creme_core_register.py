# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu

from recurrents.models import RecurrentGenerator


creme_registry.register_app('recurrents', _(u'Recurrent documents'), '/recurrents')
creme_registry.register_entity_models(RecurrentGenerator)

reg_item = creme_menu.register_app('recurrents', '/recurrents/').register_item
reg_item('/recurrents/',              _(u'Portal'),                   'recurrents')
reg_item('/recurrents/generators',    _(u'All recurrent generators'), 'recurrents')
reg_item('/recurrents/generator/add', _(u'Add a generator'),          'recurrents.add_recurrentgenerator')
