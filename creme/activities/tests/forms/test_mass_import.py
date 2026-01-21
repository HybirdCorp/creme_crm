from functools import partial

from django.utils.translation import gettext as _

from creme.activities import constants
from creme.activities.forms.mass_import import (
    _PATTERNS,
    MultiColumnsParticipantsExtractor,
    SplitColumnParticipantsExtractor,
    SubjectsExtractor,
    _pattern_CFL,
    _pattern_FL,
)
from creme.creme_core.models import RelationType
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.documents import get_document_model
from creme.persons.models import Civility
from creme.persons.populate import UUID_CIVILITY_MR
from creme.persons.tests.base import skipIfCustomContact

from ..base import Activity, Contact, _ActivitiesTestCase


class ActivityMassImportFormTestCase(_ActivitiesTestCase):
    def test_pattern1(self):
        "Pattern #1: 'Civility FirstName LastName'"
        with self.assertNoException():
            pattern_func = _PATTERNS['1']
            result = pattern_func('Ms. Aoi Kunieda')

        expected = ('Ms.', 'Aoi', 'Kunieda')
        self.assertTupleEqual(expected, result)
        self.assertTupleEqual((None, 'Aoi', 'Kunieda'), pattern_func('Aoi Kunieda'))
        self.assertTupleEqual((None, None, 'Kunieda'), pattern_func('Kunieda'))
        self.assertTupleEqual(
            ('Mr.', 'Kaiser', 'de Emperana Beelzebub'),
            pattern_func('Mr. Kaiser de Emperana Beelzebub'),
        )
        self.assertTupleEqual(expected, pattern_func(' Ms. Aoi Kunieda '))

    def test_pattern2(self):
        "Pattern #2: 'Civility LastName FirstName'."
        with self.assertNoException():
            pattern_func = _PATTERNS['2']
            result = pattern_func('Ms. Kunieda Aoi')

        expected = ('Ms.', 'Aoi', 'Kunieda')
        self.assertTupleEqual(expected, result)
        self.assertTupleEqual(expected, pattern_func(' Ms.  Kunieda  Aoi '))
        self.assertTupleEqual((None, 'Aoi', 'Kunieda'), pattern_func(' Kunieda  Aoi '))
        self.assertTupleEqual(
            ('Mr.', 'Kaiser', 'de Emperana Beelzebub'),
            pattern_func('Mr. de Emperana Beelzebub Kaiser'),
        )
        self.assertTupleEqual((None, None, 'Kunieda'), pattern_func('Kunieda'))

    def test_pattern3(self):
        "Pattern #3: 'FirstName LastName'"
        with self.assertNoException():
            pattern_func = _PATTERNS['3']
            result = pattern_func('Aoi Kunieda')

        expected = (None, 'Aoi', 'Kunieda')
        self.assertTupleEqual(expected, result)
        self.assertTupleEqual(expected, pattern_func('  Aoi  Kunieda '))
        self.assertTupleEqual((None, None, 'Kunieda'), pattern_func('Kunieda'))
        self.assertTupleEqual(
            (None, 'Kaiser', 'de Emperana Beelzebub'),
            pattern_func('Kaiser de Emperana Beelzebub '),
        )

    def test_pattern4(self):
        "Pattern #4: 'LastName FirstName'."
        with self.assertNoException():
            pattern_func = _PATTERNS['4']
            result = pattern_func('Kunieda Aoi')

        self.assertTupleEqual((None, 'Aoi', 'Kunieda'), result)
        self.assertTupleEqual(
            (None, 'Kaiser', 'de Emperana Beelzebub'),
            pattern_func('de Emperana Beelzebub Kaiser ')
        )

    @skipIfCustomContact
    def test_participants_multicol_extractor(self):
        user = self.login_as_root_and_get()

        # -----
        ext = MultiColumnsParticipantsExtractor(1, 2)

        first_name = 'Aoi'
        last_name = 'Kunieda'
        contacts, err_msg = ext.extract_value([first_name, last_name], user)
        self.assertTupleEqual((), contacts)
        self.assertTupleEqual(
            tuple([
                _('The participant «{}» cannot be found').format(
                    _('{first_name} {last_name}').format(
                        first_name=first_name,
                        last_name=last_name,
                    ),
                ),
            ]),
            err_msg,
        )

        create_contact = partial(Contact.objects.create, user=user, last_name=last_name)
        aoi = create_contact(first_name=first_name)
        contacts, err_msg = ext.extract_value([first_name, last_name], user)
        self.assertListEqual([aoi], [*contacts])
        self.assertFalse(err_msg)

        # -----
        ext = MultiColumnsParticipantsExtractor(0, 1)
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertListEqual([aoi], [*contacts])
        self.assertEqual((), err_msg)

        ittosai = create_contact(first_name='Ittôsai')
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertCountEqual([aoi, ittosai], contacts)
        self.assertEqual(
            (_('Several contacts were found for the search «{}»').format(last_name),),
            err_msg,
        )

        create_contact(first_name='Shinobu')
        create_contact(first_name='Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertFalse(contacts)
        self.assertTupleEqual(
            (_('Too many contacts were found for the search «{}»').format(last_name), ),
            err_msg,
        )

    @skipIfCustomContact
    def test_participants_multicol_extractor__view_perms(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        last_name = 'Kunieda'
        create_contact = partial(Contact.objects.create, last_name=last_name)
        aoi = create_contact(user=user, first_name='Aoi')
        create_contact(user=self.get_root_user(), first_name='Ittôsai')

        ext = MultiColumnsParticipantsExtractor(0, 1)
        contacts, err_msg = ext.extract_value([last_name], user)
        self.assertListEqual([aoi], [*contacts])
        self.assertFalse(err_msg)

    @skipIfCustomContact
    def test_participants_multicol_extractor__link_perms(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['VIEW', 'LINK'], all=['VIEW'])

        ext = MultiColumnsParticipantsExtractor(0, 1)
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([last_name], user)

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertTupleEqual(
            (_('The participant «{}» cannot be found').format(last_name),),
            err_msg,
        )

        create_contact = partial(Contact.objects.create, last_name=last_name)
        create_contact(user=self.get_root_user(), first_name='Ittôsai')

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertTupleEqual(
            (_('No linkable contact found for the search «{}»').format(last_name),),
            err_msg
        )

        aoi = create_contact(user=user, first_name='Aoi')
        contacts, err_msg = extract()
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    def test_participants_multicol_extractor__creation(self):
        "Creation if not found."
        user = self.login_as_root_and_get()

        ext = MultiColumnsParticipantsExtractor(1, 2, create_if_unfound=True)
        first_name = 'Aoi'
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([first_name, last_name], user)

        contacts, err_msg = extract()
        self.assertFalse(err_msg)

        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertListEqual([aoi], [*contacts])

        extract()
        self.assertEqual(
            1, Contact.objects.filter(first_name=first_name, last_name=last_name).count(),
        )

    @skipIfCustomContact
    def test_participants_singlecol_extractor(self):
        "SplitColumnParticipantsExtractor."
        user = self.login_as_root_and_get()
        ext = SplitColumnParticipantsExtractor(1, '#', _pattern_FL)

        create_contact = partial(Contact.objects.create, user=user, last_name='Kunieda')
        searched = 'Aoi Kunieda'
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertFalse(contacts)
        self.assertListEqual(
            [_('The participant «{}» cannot be found').format(searched)],
            err_msg,
        )

        aoi = create_contact(first_name='Aoi')
        oga = create_contact(first_name='Tatsumi', last_name='Oga')
        contacts, err_msg = ext.extract_value(['Aoi Kunieda#Tatsumi Oga'], user)
        self.assertCountEqual([aoi, oga], contacts)
        self.assertFalse(err_msg)

        contacts, err_msg = ext.extract_value(['Aoi Kunieda#Tatsumi Oga#'], user)
        self.assertCountEqual([aoi, oga], contacts)

        # -------
        searched = 'Kunieda'
        ittosai = create_contact(first_name='Ittôsai')
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertCountEqual([aoi, ittosai], contacts)
        self.assertListEqual(
            [_('Several contacts were found for the search «{}»').format(searched)],
            err_msg,
        )

        create_contact(first_name='Shinobu')
        create_contact(first_name='Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')
        contacts, err_msg = ext.extract_value([searched], user)
        self.assertFalse(contacts)
        self.assertListEqual(
            [_('Too many contacts were found for the search «{}»').format(searched)],
            err_msg,
        )

    @skipIfCustomContact
    def test_participants_singlecol_extractor__perms(self):
        "SplitColumnParticipantsExtractor + credentials"
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        create_contact = partial(Contact.objects.create, last_name='Kunieda')
        aoi = create_contact(user=user, first_name='Aoi')
        create_contact(user=self.get_root_user(), first_name='Ittôsai')

        ext = SplitColumnParticipantsExtractor(1, '#', _pattern_FL)
        contacts, err_msg = ext.extract_value(['Kunieda'], user)
        self.assertListEqual([aoi], contacts)
        self.assertFalse(err_msg)

    @skipIfCustomContact
    def test_participants_singlecol_extractor__creation(self):
        "Creation if not found + civility."
        user = self.login_as_root_and_get()
        ext = SplitColumnParticipantsExtractor(1, '#', _pattern_CFL, create_if_unfound=True)

        first_name = 'Aoi'
        last_name = 'Kunieda'
        contacts, err_msg = ext.extract_value([f'{first_name} {last_name}'], user)
        self.assertFalse(err_msg)
        aoi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertIsNone(aoi.civility)

        first_name = 'Ittôsai'
        contacts, err_msg = ext.extract_value([f'Sensei {first_name} {last_name}'], user)
        self.assertFalse(err_msg)
        ittosai = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertIsNone(ittosai.civility)

        # Civility retrieved by title
        mister = self.get_object_or_fail(Civility, uuid=UUID_CIVILITY_MR)
        first_name = 'Tatsumi'
        last_name = 'Oga'
        contacts, err_msg = ext.extract_value([f'{mister.title} {first_name} {last_name}'], user)
        self.assertFalse(err_msg)
        oga = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(mister, oga.civility)

        # Civility is not used to search
        contacts, err_msg = ext.extract_value([f'Sensei {first_name} {last_name}'], user)
        self.assertEqual([oga], contacts)
        self.assertEqual(mister, self.refresh(oga).civility)

        # Civility retrieved by short name
        first_name = 'Takayuki'
        last_name = 'Furuichi'
        ext.extract_value([f'{mister.shortcut} {first_name} {last_name}'], user)
        furuichi = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(mister, furuichi.civility)

    @skipIfCustomContact
    def test_subjects_extractor__link_perms(self):
        user = self.login_as_activities_user(
            allowed_apps=('documents',),
            creatable_models=[Activity, get_document_model()],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'], all=['VIEW'])

        ext = SubjectsExtractor(1, '/')
        last_name = 'Kunieda'

        def extract():
            return ext.extract_value([last_name], user)

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertListEqual(
            [_('The subject «{}» cannot be found').format(last_name)],
            err_msg,
        )

        create_contact = partial(Contact.objects.create, last_name=last_name)
        create_contact(user=self.get_root_user(), first_name='Ittôsai')

        contacts, err_msg = extract()
        self.assertFalse(contacts)
        self.assertListEqual(
            [_('No linkable entity found for the search «{}»').format(last_name)],
            err_msg,
        )

        aoi = create_contact(user=user, first_name='Aoi')
        contacts, err_msg = extract()
        self.assertEqual([aoi], contacts)
        self.assertFalse(err_msg)

    @skipIfCustomContact
    def test_subjects_extractor__limit(self):
        user = self.login_as_root_and_get()
        ext = SubjectsExtractor(1, '#')

        last_name = 'Kunieda'

        create_contact = partial(Contact.objects.create, user=user, last_name=last_name)
        create_contact(first_name='Aoi')
        create_contact(first_name='Ittôsai')
        create_contact(first_name='Shinobu')
        create_contact(first_name='Kôta')
        create_contact(first_name='')
        create_contact(first_name='Tatsumi')

        contacts, err_msg = ext.extract_value([f' {last_name} #'], user)
        self.assertFalse(contacts)
        self.assertListEqual(
            [
                _('Too many «{models}» were found for the search «{search}»').format(
                    models=_('Contacts'),
                    search=last_name,
                ),
            ],
            err_msg,
        )

    @skipIfNotInstalled('creme.tickets')
    def test_subjects_extractor__other_ctype(self):
        from creme.tickets.models import Criticity, Priority, Ticket

        rtype = self.get_object_or_fail(RelationType, pk=constants.REL_OBJ_ACTIVITY_SUBJECT)
        self.assertIn(Ticket, (ct.model_class() for ct in rtype.object_ctypes.all()))

        user = self.login_as_root_and_get()
        last_name = 'Kunieda'
        ticket = Ticket.objects.create(
            user=user, title=f"{last_name}'s ticket",
            priority=Priority.objects.all()[0],
            criticity=Criticity.objects.all()[0],
        )

        ext = SubjectsExtractor(1, '/')
        extracted, err_msg = ext.extract_value([last_name], user)
        self.assertEqual([ticket], extracted)
        self.assertFalse(err_msg)
