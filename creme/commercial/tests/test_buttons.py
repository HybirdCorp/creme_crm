from unittest.mock import patch

from django.utils.translation import gettext_lazy as _
from parameterized import parameterized

from creme.commercial import buttons
from creme.creme_core.models.relation import RelationType
from creme.creme_core.tests.base import CremeTestCase
from creme.persons import get_organisation_model

Organisation = get_organisation_model()


class ButtonsTestCase(CremeTestCase):
    @parameterized.expand([
        (
            {'has_perm': False},
            RelationType(enabled=True, predicate='Is fake'),
            _('You are not allowed to access to the app «Commercial strategy»')
        ),
        (
            {'has_perm': True, 'can_link': False},
            RelationType(enabled=True, predicate='Is fake'),
            _('You are not allowed to link this entity')
        ),
        (
            {'has_perm': True, 'can_link': True},
            RelationType(enabled=False, predicate='Is fake'),
            _('The relationship type «{predicate}» is disabled').format(predicate='Is fake')
        ),
        (
            {'has_perm': True, 'can_link': True},
            RelationType(enabled=True, predicate='Is fake'),
            buttons.CompleteGoalButton.description
        ),
    ])
    def test_completegoal_description(self, context, rtype, expected):
        user = self.create_user()
        orga = Organisation.objects.create(user=user, name='Acme')

        with patch.object(RelationType.objects, 'get', return_value=rtype):
            button = buttons.CompleteGoalButton()
            button_context = button.get_button_context({
                **context,
                'object': orga,
                'user': user,
            })

            self.assertEqual(button_context['description'], expected)
