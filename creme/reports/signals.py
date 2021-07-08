# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.dispatch import receiver

from creme.creme_core.signals import pre_uninstall_flush


@receiver(pre_uninstall_flush)
def _uninstall_reports(sender, content_types, verbosity, stdout_write, style, **kwargs):
    from .models import Field

    if Field in sender.get_models():
        # We are uninstalling 'reports' itself.
        return

    if verbosity:
        stdout_write('Deleting reports...')

    for rfield in Field.objects.filter(
        sub_report__ct__in=content_types,
    ).exclude(
        report__ct__in=content_types,
    ):
        report = rfield.report
        sub_report = rfield.sub_report
        stdout_write(
            f' Beware: the report "{sub_report}" (id={sub_report.id}) was '
            f'used as sub-report by : "{report}" (id={report.id})',
            style.NOTICE
        )
        rfield.delete()

    # TODO: warning for fields on RelationTypes which are deleted ?

    if verbosity:
        stdout_write(' [OK]', style.SUCCESS)
