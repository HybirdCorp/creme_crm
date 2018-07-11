# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2018  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from creme.creme_core import get_concrete_model
from creme.creme_core.management.commands import entity_factory

from creme.crudity.models import WaitingAction


def _entity_2_dict(entity):
    data = {}

    for field in entity._meta.fields:
        if not field.editable:
            continue

        if not field.get_tag('viewable'):
            continue

        fname = field.name

        try:
            fvalue = getattr(entity, fname)
        except AttributeError:
            pass
        else:
            if fvalue is None:
                continue

            # if field.rel:
            if field.remote_field:
                # TODO: manage M2M
                fname = field.attname
                fvalue = fvalue.pk

            data[fname] = fvalue

    return data


# Command ----------------------------------------------------------------------


class Command(BaseCommand):
    help = 'Create some "fake" WaitingActions (app "crudity") for testing purposes.'
    leave_locale_alone = True

    TYPES = [
        ('PERSONS_CONTACT_MODEL',      entity_factory._get_contact_n_factory),
        ('PERSONS_ORGANISATION_MODEL', entity_factory._get_organisation_n_factory),
    ]

    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument('-n', '--number',
                     action='store', dest='number', type=int, default=10,
                     help='How many actions are created per configured backend. [default: %(default)s]',
                    )
        add_argument('-l', '--list',
                     action='store_true', dest='list_types', default=False,
                     help='List the available type of entities',
                    )
        add_argument('-c', '--language',
                     action='store', dest='language_code', default='',
                     help='Locale used for random data. [default: see settings.LANGUAGE_CODE]',
                    )

    def handle(self, **options):
        types_map = {
            get_concrete_model(type_str): factory_builder
                for type_str, factory_builder in self.TYPES
        }

        get_opt = options.get

        if get_opt('list_types'):
            self.stdout.write('\n'.join(' - {}'.format(m) for m in types_map.iterkeys()))
            return

        number = get_opt('number')
        verbosity = get_opt('verbosity')

        locale = entity_factory.get_best_locale(get_opt('language_code'))
        backend_count = 0
        action_count = 0

        from creme.crudity.registry import crudity_registry  # lazy loading

        for fetcher_name, fetcher in crudity_registry._fetchers.iteritems():
            for crud_inputs in fetcher.get_inputs():
                for method, input in crud_inputs.iteritems():
                    for backend in input.get_backends():
                        _get_model_n_factory = types_map.get(backend.model)

                        if _get_model_n_factory is None:
                            self.stderr.write('"{}" is not managed ; use the -l option to get the managed types.'.format(backend.model))
                            continue

                        backend_count += 1
                        factory = _get_model_n_factory(locale)[1]

                        for i in xrange(number):
                            # action = WaitingAction(
                            #     action=method,
                            #     source='{} - {}'.format(fetcher_name, input.name),
                            #     ct=ContentType.objects.get_for_model(backend.model),
                            #     subject=backend.subject,
                            #     # user=owner,  TODO ?
                            # )
                            # action.set_data(_entity_2_dict(factory.build()))

                            try:
                                # action.save()
                                WaitingAction.objects.create(
                                        action=method,
                                        source='{} - {}'.format(fetcher_name, input.name),
                                        ct=ContentType.objects.get_for_model(backend.model),
                                        subject=backend.subject,
                                        # user=owner,  TODO ?
                                        data=_entity_2_dict(factory.build()),
                                )
                            except Exception as e:
                                # self.stderr.write('A error occurred when saving "{}" ({}).'.format(action, e))
                                self.stderr.write('A error occurred when saving action: {}.'.format(e))
                            else:
                                action_count += 1

        if verbosity:
            self.stdout.write('Number of backend used: {backends}\n'
                              'Number of actions created: {actions}'.format(
                                    backends=backend_count,
                                    actions=action_count,
                                )
                             )
