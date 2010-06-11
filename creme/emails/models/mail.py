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

from email.mime.image import MIMEImage
from logging import error, debug
from os.path import join, basename

from django.db.models import (PositiveIntegerField, PositiveSmallIntegerField, CharField,
                              TextField, DateTimeField, ForeignKey, ManyToManyField)
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core.mail import EmailMultiAlternatives

from creme_core.models import CremeModel

from persons.models import MailSignature

from documents.models import Document

from sending import EmailSending


MAIL_STATUS_SENT         = 1
MAIL_STATUS_NOTSENT      = 2
MAIL_STATUS_SENDINGERROR = 3
MAIL_STATUS_SYNCHRONISED = 4 #??

MAIL_STATUS = {
                MAIL_STATUS_SENT:         _(u"Envoyé"),
                MAIL_STATUS_NOTSENT:      _(u"Non envoyé"),
                MAIL_STATUS_SENDINGERROR: _(u"Erreur d'envoi"),
                MAIL_STATUS_SYNCHRONISED: _(u"Synchronisé"), 
              }

ID_LENGTH = 32

class Email(CremeModel):
    """
    id is a unique generated string in order to avoid stats hacking.
    """
    id           = CharField(_(u'Identifiant du mail'), primary_key=True, max_length=ID_LENGTH)
    sending      = ForeignKey(EmailSending, null=True, verbose_name=_(u"Envoi associé"), related_name='mails_set')

    reads        = PositiveIntegerField(_(u'Nombre de lecture(s)'), blank=True, null=True)
    status       = PositiveSmallIntegerField(_(u'Statut'))

    sender       = CharField(_(u'Émetteur'), max_length=100)
    recipient    = CharField(_(u'Destinataire'), max_length=100)
    #cc           = CharField(_(u'cc'), max_length=100)
    subject      = CharField(_(u'Sujet'), max_length=100, blank=True, null=True)
    #body_html    = TextField()
    body         = TextField()
    #validated    = BooleanField()
    #spam         = BooleanField()
    #assign       = ManyToManyField(CremeEntity, blank=True, null=True , symmetrical=False, related_name='MailCremeAssign_set' )
    sending_date = DateTimeField(_(u"Date d'envoi"), blank=True, null=True)
    signature    = ForeignKey(MailSignature, verbose_name=_(u'Signature'), blank=True, null=True) ##merge with body ????
    attachments  = ManyToManyField(Document, verbose_name=_(u'Fichiers attachés'))

    recipient_ct = ForeignKey(ContentType, null=True) #useful ?????
    recipient_id = PositiveIntegerField(null=True)

    recipient_entity = GenericForeignKey(ct_field="recipient_ct", fk_field="recipient_id")

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Courriel')
        verbose_name_plural = _(u'Courriels')

    def __unicode__(self):
        return u"Mail<from: %s> <to: %s> <sent: %s> <id: %s>" % (self.sender, self.recipient, self.sending_date, self.id)

    def get_status_str(self):
        return MAIL_STATUS[self.status]

    #TODO: factorise with EmailSending.send_mails()
    def send(self):
        mail = self

        img_cache = {}

        if mail.status == MAIL_STATUS_SENT:
            error('Mail already sent to the recipient')
            return

        body = mail.body
        #body += '<img src="http://minimails.hybird.org/emails/stats/bbm/%s" />' % mail.ident

        signature = mail.signature
        signature_images = signature.images.all() if signature else ()

        if signature:
            body += signature.corpse #'corpse' berkkkkk

            for signature_img in signature_images:
                body += '<img src="cid:img_%s" /><br/>' % signature_img.id

        msg = EmailMultiAlternatives(mail.subject, body, mail.sender, [mail.recipient])
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
        for attachment in mail.attachments.all():
            msg.attach_file(join(settings.MEDIA_ROOT, attachment.filedata.name))

        try:
            msg.send()
        except Exception, e: #better exception ??
            error("Sending: error during sending mail.")
            mail.status = MAIL_STATUS_SENDINGERROR
        else:
            mail.status = MAIL_STATUS_SENT

        mail.save()
        debug("Mail sent to %s", mail.recipient)
