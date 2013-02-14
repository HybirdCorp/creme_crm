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

from logging import debug
from pickle import loads
from time import sleep

from django.db import transaction, IntegrityError
from django.db.models import (ForeignKey, DateTimeField, PositiveSmallIntegerField,
                              EmailField, CharField, TextField, ManyToManyField)
from django.core.mail import send_mail, get_connection
from django.template import Template, Context
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy, activate

from creme_core.models import CremeModel, CremeEntity

from documents.models import Document

from emails.models.mail import _Email, ID_LENGTH
from emails.models import EmailCampaign, EmailSignature
from emails.utils import generate_id, EMailSender, ImageFromHTMLError
from emails.constants import MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR


#TODO: move to constants ???
SENDING_TYPE_IMMEDIATE = 1
SENDING_TYPE_DEFERRED  = 2

SENDING_TYPES = {
                    SENDING_TYPE_IMMEDIATE: _(u"Immediate"),
                    SENDING_TYPE_DEFERRED:  pgettext_lazy('emails-sending', 'Deferred'),
                }

SENDING_STATE_DONE       = 1
SENDING_STATE_INPROGRESS = 2
SENDING_STATE_PLANNED    = 3
SENDING_STATE_ERROR      = 4

SENDING_STATES = {
                    SENDING_STATE_DONE:       pgettext_lazy('emails-sending', 'Done'),
                    SENDING_STATE_INPROGRESS: _(u"In progress"),
                    SENDING_STATE_PLANNED:    pgettext_lazy('emails-sending', 'Planned'),
                    SENDING_STATE_ERROR:      _(u"Error during sending"),
                 }


class EmailSending(CremeModel):
    sender        = EmailField(_(u"Sender address"), max_length=100)
    campaign      = ForeignKey(EmailCampaign, verbose_name=_(u'Related campaign'), related_name='sendings_set')
    type          = PositiveSmallIntegerField(verbose_name=_(u"Sending type"))
    sending_date  = DateTimeField(_(u"Sending date of emails"))
    state         = PositiveSmallIntegerField(verbose_name=_(u"Sending state"))

    subject     = CharField(_(u'Subject'), max_length=100)
    body        = TextField(_(u"Body"))
    body_html   = TextField(_(u"Body (HTML)"), null=True, blank=True)
    signature   = ForeignKey(EmailSignature, verbose_name=_(u'Signature'), blank=True, null=True)
    attachments = ManyToManyField(Document, verbose_name=_(u'Attachments'))

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Email campaign sending')
        verbose_name_plural = _(u'Email campaign sendings')

    def __unicode__(self):
        return ugettext(u"Sending of <%(campaign)s> on %(date)s") % {'campaign': self.campaign, 'date': self.sending_date}

    #def delete(self):
        #self.mails_set.all().delete() #use CremeModel delete() ??
        #super(EmailSending, self).delete()

    def get_mails(self):
        return self.mails_set.all()

    def get_unsent_mails_count(self):
        return self.mails_set.filter(status__in=[MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR]).count()

    def get_state_str(self):
        return SENDING_STATES[self.state]

    def get_type_str(self):
        return SENDING_TYPES[self.type]

    def get_absolute_url(self):
        return self.campaign.get_absolute_url()

    def get_related_entity(self): #for generic views
        return self.campaign

    def send_mails(self):
        try:
            sender = LightWeightEmailSender(sending=self)
        except ImageFromHTMLError as e:
            activate(settings.LANGUAGE_CODE)
            send_mail(ugettext('[CremeCRM] Campaign email sending error.'),
                      ugettext("Emails in the sending of the campaign <%(campaign)s> on %(date)s weren't sent "
                               "because the image <%(image)s> is no longer available in the template.") % {
                            'campaign': self.campaign,
                            'date':     self.sending_date,
                            'image':    e.filename,
                        },
                      settings.EMAIL_HOST_USER,
                      [self.campaign.user.email or settings.DEFAULT_USER_EMAIL],
                      fail_silently=False,
                     )

            return SENDING_STATE_ERROR

        ##SMTPConnection is deprecated but with mail.get_connection() we can't specify other settings than django settings
        ##todo: Write a custom e-mail backend: http://docs.djangoproject.com/en/1.3/topics/email/#topic-custom-email-backend
        #connection = SMTPConnection(host=settings.CREME_EMAIL_SERVER,
                                    #port=settings.CREME_EMAIL_PORT,
                                    #username=settings.CREME_EMAIL_USERNAME,
                                    #password=settings.CREME_EMAIL_PASSWORD,
                                    #use_tls=True
                                   #)
        connection = get_connection('django.core.mail.backends.smtp.EmailBackend',
                                    host=settings.EMAILCAMPAIGN_HOST,
                                    port=settings.EMAILCAMPAIGN_PORT,
                                    username=settings.EMAILCAMPAIGN_HOST_USER,
                                    password=settings.EMAILCAMPAIGN_PASSWORD,
                                    use_tls=settings.EMAILCAMPAIGN_USE_TLS,
                                   )

        mails_count   = 0
        one_mail_sent = False
        SENDING_SIZE  = getattr(settings, 'EMAILCAMPAIGN_SIZE', 40)
        SLEEP_TIME    = getattr(settings, 'EMAILCAMPAIGN_SLEEP_TIME', 2)

        for mail in LightWeightEmail.objects.filter(sending=self):
            if sender.send(mail, connection=connection):
                mails_count += 1
                one_mail_sent = True
                debug("Mail sent to %s", mail.recipient)

            if mails_count > SENDING_SIZE:
                debug('Sending: waiting timeout')

                mails_count = 0
                sleep(SLEEP_TIME) #avoiding the mail to be classed as spam

        if not one_mail_sent:
            return SENDING_STATE_ERROR


class LightWeightEmail(_Email):
    """Used by campaigns.
    id is a unique generated string in order to avoid stats hacking.
    """
    id               = CharField(_(u'Email ID'), primary_key=True, max_length=ID_LENGTH)
    sending          = ForeignKey(EmailSending, verbose_name=_(u"Related sending"), related_name='mails_set')
    recipient_entity = ForeignKey(CremeEntity, null=True, related_name='received_lw_mails')

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Email of campaign')
        verbose_name_plural = _(u'Emails of campaign')

    def _render_body(self, sending_body):
        body = self.body

        try:
            return Template(sending_body).render(Context(loads(body.encode('utf-8')) if body else {}))
        except Exception as e: #Pickle raise too much differents exceptions...Catch'em all ?
            debug('Error in LightWeightEmail._render_body(): %s', e)
            return ""

    def get_body(self):
        return self._render_body(self.sending.body)

    def get_body_html(self):
        return self._render_body(self.sending.body_html)

    def get_related_entity(self): #for generic views
        return self.sending.campaign

    #TODO: factorise
    @transaction.commit_manually
    def genid_n_save(self):
        #BEWARE: manage manually
        while True:
            sid = transaction.savepoint()

            try:
                self.id = generate_id()
                self.save(force_insert=True)
            except IntegrityError:  #a mail with this id already exists
                debug('Mail id already exists: %s', self.id)
                self.pk = None

                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)
                break

        transaction.commit()


class LightWeightEmailSender(EMailSender):
    def __init__(self, sending):
        super(LightWeightEmailSender, self).__init__(body=sending.body,
                                                     body_html=sending.body_html,
                                                     signature=sending.signature,
                                                     attachments=sending.attachments.all()
                                                    )
        self._sending = sending
        self._body_template = Template(self._body)
        self._body_html_template = Template(self._body_html)

    def get_subject(self, mail):
        return self._sending.subject

    def _process_bodies(self, mail):
        body = mail.body
        context = Context(loads(body.encode('utf-8')) if body else {})

        return self._body_template.render(context), self._body_html_template.render(context)
