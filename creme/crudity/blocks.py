# -*- coding: utf-8 -*-

import warnings

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from .bricks import (
    CrudityQuerysetBrick as CrudityQuerysetBlock,
)
from .models import WaitingAction, History


warnings.warn('crudity.blocks is deprecated ; use crudity.bricks instead.', DeprecationWarning)


class WaitingActionBlock(CrudityQuerysetBlock):
    # dependencies  = ()
    verbose_name  = _(u'Waiting actions')
    template_name = 'crudity/templatetags/block_waiting_action.html'

    def __init__(self, backend):
        super(WaitingActionBlock, self).__init__()
        self.backend = backend
        self.ct      = ContentType.objects.get_for_model(backend.model)
        self.id_     = self.generate_id()
        self.buttons = backend.get_rendered_buttons()

    def generate_id(self):
        # return 'block_crudity-%s-%s' % (self.ct.id, CrudityBackend.normalize_subject(self.backend.subject))
        be = self.backend
        subject = be.subject
        name = be.fetcher_name if subject == '*' else \
               '%s|%s|%s' % (be.fetcher_name, be.input_name, be.subject)

        return CrudityQuerysetBlock.generate_id('crudity', 'waiting_actions-' + name)

    def detailview_display(self, context):
        # Credentials are OK: block is not registered in block registry, so reloading is necessarily done with the custom view
        super(WaitingActionBlock, self).detailview_display(context)
        ct   = self.ct
        backend = self.backend

        waiting_actions = WaitingAction.objects.filter(ct=ct, source=backend.source, subject=backend.subject)

        if self.is_sandbox_by_user:
            waiting_actions = waiting_actions.filter(user=context['user'])

        return self._render(self.get_template_context(
                    context,
                    waiting_actions,
                    waiting_ct=ct,
                    buttons=self.buttons,
                    backend=backend,
                    # update_url='/crudity/waiting_actions_blocks/%s/reload' % (self.id_,),
                    update_url=reverse('crudity__reload_actions_block_legacy', args=(self.id_,)),
        ))


class HistoryBlock(CrudityQuerysetBlock):
    # dependencies  = ()
    verbose_name  = _(u'History')
    template_name = 'crudity/templatetags/block_history.html'

    def __init__(self, ct, buttons=None):
        super(HistoryBlock, self).__init__()
        self.ct = ct
        self.id_ = self.generate_id()
        self.buttons = buttons

    def generate_id(self):
        return 'block_crudity-%s' % (self.ct.id,)

    def detailview_display(self, context):
        # Credentials are OK: block is not registered in block registry, so reloading is necessarily done with the custom view
        super(HistoryBlock, self).detailview_display(context)
        ct = self.ct

        histories = History.objects.filter(entity__entity_type=ct)
        if self.is_sandbox_by_user:
            histories = histories.filter(user=context['user'])

        return self._render(self.get_template_context(
                    context,
                    histories,
                    ct=ct,
                    buttons=self.buttons,
                    # update_url='/crudity/history_block/%s/reload' % (self.id_,),
                    update_url=reverse('crudity__reload_history_block_legacy', args=(self.ct.id,)),
        ))
