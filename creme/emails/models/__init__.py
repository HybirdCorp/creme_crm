# -*- coding: utf-8 -*-

from .signature import EmailSignature
from .template import AbstractEmailTemplate, EmailTemplate
from .mailing_list import AbstractMailingList, MailingList
from .recipient import EmailRecipient
from .campaign import AbstractEmailCampaign, EmailCampaign
from .sending import EmailSending, LightWeightEmail
from .mail import _Email, AbstractEntityEmail, EntityEmail
