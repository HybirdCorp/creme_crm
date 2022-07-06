################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from json import loads

# from django.urls import reverse
from django.conf import settings

from .backend import WSBackEnd

SAMOUSSA_STATUS_WAITING = 'wait'
SAMOUSSA_STATUS_ACCEPT = 'accept'
SAMOUSSA_STATUS_SENT = 'sent'
SAMOUSSA_STATUS_ERROR = 'error'


class SamoussaBackEnd(WSBackEnd):
    def connect(self):
        return self.open(
            settings.CREME_SAMOUSSA_URL,
            settings.CREME_SAMOUSSA_USERNAME,
            settings.CREME_SAMOUSSA_PASSWORD,
        )

    def delete_messages(self, **kwargs):
        self.delete('/sms/api/message/', **kwargs)
        # TODO: self.delete(reverse('...'), **kwargs)

    def delete_message(self, message):
        self.delete_messages(phone=message.phone, user_data=message.sending_id)

    def sync_message(self, message):
        info = self.message(message, fields=['status', 'message'])
        message.status = info.get('status', message.status)
        message.status_message = info.get('message', message.status_message)
        return message

    # curl -u compte21:compte21 --basic --url "http://127.0.0.1:8001/sms/api/piston/message/json?state=accept"  # NOQA
    def list_messages(self, **kwargs):
        # TODO: reverse('...')
        return loads(self.get('/sms/api/message/json', **kwargs).read())

    # curl -u compte21:compte21 --basic --url "http://127.0.0.1:8001/sms/api/piston/message" -F "content=test" -F "phone=0899653355;4577896652;4785556664" -F "user_data=41" -F "accept=True" -X POST  # NOQA
    def send_messages(self, content, numbers, user_data=None):
        if isinstance(numbers, list):
            numbers = ';'.join(numbers)

        # TODO: reverse('...')
        return loads(
            self.post(
                '/sms/api/message', content=content, phone=numbers, user_data=user_data,
            ).read()
        )

    def get_account(self):
        # TODO: reverse('...')
        return loads(self.get('/sms/api/account').read())
