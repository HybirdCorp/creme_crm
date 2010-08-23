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

from logging import error, debug
from time import sleep
from email.mime.image import MIMEImage
from os.path import join, basename
from pickle import loads

from django.contrib.contenttypes.generic import GenericForeignKey
from django.db import IntegrityError
from django.db.models import (ForeignKey, DateTimeField, PositiveSmallIntegerField,
                              EmailField, CharField, TextField, ManyToManyField, PositiveIntegerField)
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel

from emails.models.mail import _Email, ID_LENGTH, MAIL_STATUS_SENT
from emails.utils import generate_id

from persons.models import MailSignature

from documents.models import Document

from campaign import EmailCampaign


SENDING_TYPE_IMMEDIATE = 1
SENDING_TYPE_DEFERRED  = 2

SENDING_TYPES = {
                    SENDING_TYPE_IMMEDIATE: _(u"Immédiat"),
                    SENDING_TYPE_DEFERRED:  _(u"Différé"),
                }

SENDING_STATE_DONE       = 1
SENDING_STATE_INPROGRESS = 2
SENDING_STATE_PLANNED    = 3

SENDING_STATES = {
                    SENDING_STATE_DONE:       _(u"Effectué"),
                    SENDING_STATE_INPROGRESS: _(u"En cours"),
                    SENDING_STATE_PLANNED:    _(u"Prévu"),
                 }


class EmailSending(CremeModel):
    sender        = EmailField(_(u"Adresse email de l'expéditeur"), max_length=100)
    campaign      = ForeignKey(EmailCampaign, verbose_name=_(u'Campagne associée'), related_name='sendings_set')
    type          = PositiveSmallIntegerField(verbose_name=_(u"Type d'envoi"))
    #creation_date = DateField(_(u"Date de création")) #, blank=True, null=True
    sending_date  = DateTimeField(_(u"Date d'envoi des mails"))
    state         = PositiveSmallIntegerField(verbose_name=_(u"État de l'envoi"))

    subject     = CharField(_(u'Sujet'), max_length=100)
    body        = TextField(_(u"Corps"))
    signature   = ForeignKey(MailSignature, verbose_name=_(u'Signature'), blank=True, null=True)
    attachments = ManyToManyField(Document, verbose_name=_(u'Fichiers attachés'))

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Envoi de campagne')
        verbose_name_plural = _(u'Envois de campagne')

    def __unicode__(self):
        return u"Envoi de <%s> du %s" % (self.campaign, self.sending_date)

    def delete(self):
        self.mails_set.all().delete() #use CremeModel delete() ??
        super(EmailSending, self).delete()

    def get_mails(self):
        return LightWeightEmail.objects.filter(sending=self)

    def get_state_str(self):
        return SENDING_STATES[self.state]

    def get_type_str(self):
        return SENDING_TYPES[self.type]

    def get_absolute_url(self):
        return self.campaign.get_absolute_url()

    def send_mails(self):
#        mails = Email.objects.filter(sending=self)
        mails = LightWeightEmail.objects.filter(sending=self)

        mails_count  = 0
        SENDING_SIZE = getattr(settings, 'SENDING_SIZE', 40)
        SLEEP_TIME   = getattr(settings, 'SENDING_SLEEP_TIME', 2)

        img_cache = {}
        signature = self.signature
        signature_images = signature.images.all() if signature else ()
        body_template = Template(self.body)

        for mail in mails:
            if mail.status == MAIL_STATUS_SENT:
                error('Mail already sent to the recipient')
                continue

            body = body_template.render(Context(loads(mail.body.encode('utf-8')) if mail.body else {}))
            #body += '<img src="http://minimails.hybird.org/emails/stats/bbm/%s" />' % mail.ident

            if signature:
                body += signature.corpse #'corpse' berkkkkk

                for signature_img in signature_images:
                    body += '<img src="cid:img_%s" /><br/>' % signature_img.id

            msg = EmailMultiAlternatives(self.subject, body, mail.sender, [mail.recipient])
            msg.attach_alternative(body, "text/html")

            for signature_img in signature_images:
                name = signature_img.image.name
                mime_img = img_cache.get(name)

                if mime_img is None:
                    try:
                        f = open(join(settings.MEDIA_ROOT, name), 'rb')
                        mime_img = MIMEImage(f.read())
                        mime_img.add_header('Content-ID','<img_%s>' % signature_img.id)
                        mime_img.add_header('Content-Disposition', 'inline', filename=basename(f.name))
                        f.close()
                    except Exception, e: #better exception ???
                        error('Sending: exception when adding image signature: %s', e)
                        continue
                    else:
                        img_cache[name] = mime_img

                msg.attach(mime_img)

            #TODO: use a cache to not open the sames files for each mail ?????
            for attachment in self.attachments.all():
                msg.attach_file(join(settings.MEDIA_ROOT, attachment.filedata.name))

            try:
                msg.send()
            except Exception, e: #better exception ??
                error("Sending: error during sending mail.")
                mail.status = MAIL_STATUS_SENDINGERROR
            else:
                mail.status = MAIL_STATUS_SENT
                mails_count += 1

            mail.save()
            debug("Mail sent to %s", mail.recipient)

            if mails_count > SENDING_SIZE:
                debug('Sending: waiting timeout')

                mails_count = 0
                sleep(SLEEP_TIME) #avoiding the mail to be classed as spam


class LightWeightEmail(_Email):
    """Used by campaigns"""
    id           = CharField(_(u'Identifiant du mail'), primary_key=True, max_length=ID_LENGTH)
    sending      = ForeignKey(EmailSending, null=True, verbose_name=_(u"Envoi associé"), related_name='mails_set')

    recipient_ct = ForeignKey(ContentType, null=True) #useful ?????
    recipient_id = PositiveIntegerField(null=True)

    recipient_entity = GenericForeignKey(ct_field="recipient_ct", fk_field="recipient_id")

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Courriel de campagne')
        verbose_name_plural = _(u'Courriels  de campagne')

    def get_body(self):
        if self.sending is None:
            return self.body

        try:
            body_template = Template(self.sending.body)
            return body_template.render(Context(loads(self.body.encode('utf-8')) if self.body else {}))
        except:#Pickle raise too much differents exceptions...Catch'em all ?
            return ""

    def genid_n_save(self):
        #BEWARE: manage manually
        while True:
            try:
                self.id = generate_id()
                self.save(force_insert=True)
            except IntegrityError:  #a mail with this id already exists
                debug('Mail id already exists: %s', self.id)
                self.pk = None
            else:
                break