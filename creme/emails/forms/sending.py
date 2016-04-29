# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from datetime import datetime, time

import logging
from pickle import dumps

from django.forms import IntegerField, EmailField, DateTimeField
from django.forms.utils import ValidationError
from django.template.base import Template, VariableNode
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _ # ugettext

from creme.creme_core.forms import CremeModelForm, CreatorEntityField
from creme.creme_core.forms.widgets import CalendarWidget
from creme.creme_core.models import SettingValue
from creme.creme_core.utils.dates import make_aware_dt

from .. import get_emailtemplate_model
from ..constants import SETTING_EMAILCAMPAIGN_SENDER  # MAIL_STATUS_NOTSENT
from ..models.sending import EmailSending, LightWeightEmail, SENDING_TYPE_DEFERRED # SENDING_TYPES SENDING_STATE_PLANNED


logger = logging.getLogger(__name__)


class SendingCreateForm(CremeModelForm):
    sender       = EmailField(label=_(u"Sender address"))
    template     = CreatorEntityField(label=_(u'Email template'), model=get_emailtemplate_model())
    sending_date = DateTimeField(label=_(u"Sending date"), required=False, widget=CalendarWidget,
                                 help_text=_(u"Required only of the sending is deferred."))
    hour         = IntegerField(label=_("Sending hour"), required=False, min_value=0, max_value=23)
    minute       = IntegerField(label=_("Sending minute"), required=False, min_value=0, max_value=59)

    error_messages = {
        'forbidden': _(u"You are not allowed to modify the sender address, please contact your administrator."),
    }

    blocks = CremeModelForm.blocks.new(('sending_date', _(u"Sending date"), ['type', 'sending_date', 'hour', 'minute']))

    class Meta:
        model   = EmailSending
        exclude = ()

    def __init__(self, entity, *args, **kwargs):
        super(SendingCreateForm, self).__init__(*args, **kwargs)
        self.campaign = entity
        self.can_admin_emails = can_admin_emails = self.user.has_perm_to_admin("emails")

        try:
            sender_setting = SettingValue.objects.get(key_id=SETTING_EMAILCAMPAIGN_SENDER)
        except SettingValue.DoesNotExist:
            # sender_setting = None
            logger.critical('SettingValue with key=%s cannot be found !'
                            ' ("creme_populate" command has not been run correctly)',
                            SETTING_EMAILCAMPAIGN_SENDER
                        )
            raise

        sender_field = self.fields['sender']
        self.can_edit_sender_value = can_edit_sender_value = not sender_setting.value and can_admin_emails
        if not can_edit_sender_value:
            sender_field.widget.attrs['readonly'] = True

        if not sender_setting.value:
            if not can_admin_emails:
                sender_field.initial = _(u"No sender email address has been configured, please contact your administrator.")
        else:
            sender_field.help_text = _(u"Only an administrator can modify the sender address.")
            sender_field.initial = sender_setting.value

        self.sender_setting = sender_setting

    def clean_sender(self):
        sender_value = self.cleaned_data.get('sender')

        if not self.can_edit_sender_value and sender_value != self.sender_setting.value:
            raise ValidationError(self.error_messages['forbidden'], code='forbidden')

        return sender_value

    def clean(self):
        cleaned_data = super(SendingCreateForm, self).clean()

        if cleaned_data['type'] == SENDING_TYPE_DEFERRED:
            sending_date = cleaned_data['sending_date']

            if sending_date is None:
                self.add_error('sending_date', _(u"Sending date required for a deferred sending"))
            else:
                get_data = cleaned_data.get
                sending_date = make_aware_dt(datetime.combine(sending_date,
                                                              time(hour=int(get_data('hour') or 0),
                                                                   minute=int(get_data('minute') or 0),
                                                                  ),
                                                             )
                                            )

                if sending_date < now():
                    self.add_error('sending_date', _(u'Sending date must be is the future'))
                else:
                    cleaned_data['sending_date'] = sending_date
        else:
            cleaned_data['sending_date'] = now()

        return cleaned_data

    def _get_variables(self, body):  # TODO: move in Emailtemplate ??
        return (varnode.filter_expression.var.var
                    for varnode in Template(body).nodelist.get_nodes_by_type(VariableNode)
               )

    def save(self):
        instance = self.instance
        cleaned_data = self.cleaned_data
        sender_setting = self.sender_setting

        instance.campaign = self.campaign
#        instance.state = SENDING_STATE_PLANNED

        template = cleaned_data['template']
        instance.subject   = template.subject
        instance.body      = template.body
        instance.body_html = template.body_html
        instance.signature = template.signature

        super(SendingCreateForm, self).save()

        sender_address = cleaned_data['sender']
        if self.can_edit_sender_value:
            sender_setting.value = sender_address
            sender_setting.save()

        # M2M need a pk -> after save
        attachments = instance.attachments
        for attachment in template.attachments.all():
            attachments.add(attachment)

        varlist = list(self._get_variables(template.body))
        varlist.extend(self._get_variables(template.body_html))

        for address, recipient_entity in instance.campaign.all_recipients():
            mail = LightWeightEmail(sending=instance,
                                    sender=instance.sender,
                                    recipient=address,
                                    sending_date=instance.sending_date,
                                    recipient_entity=recipient_entity,
                                   )

            if recipient_entity:
                context = {}

                for varname in varlist:
                    val = getattr(recipient_entity, varname, None)
                    if val:
                        # TODO: unicode(val).encode('utf-8') ?
                        #       (if val is an fk it doesn't have attribute encode...(civility))
                        context[varname] = val.encode('utf-8')

                if context:
                    mail.body = dumps(context)

            mail.genid_n_save()

        return instance
