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

from django.utils.translation import ugettext as _

from documents.models import Folder

def get_csv_folder_or_create(user):
    title=_(u'CSV Documents')

    try:
        folder = Folder.objects.get(title=title)
    except Folder.DoesNotExist:
        folder = Folder.objects.create(title=title,
                                       description=_(u'Folder containing all the CSV documents used when importing data'),
                                       parent_folder=None,
                                       category=None,
                                       user=user,
                                      )

    return folder