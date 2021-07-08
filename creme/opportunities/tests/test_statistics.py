# -*- coding: utf-8 -*-

from functools import partial

from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.models import FieldsConfig
from creme.opportunities.models import SalesPhase
from creme.opportunities.statistics import CurrentYearStatistics

from .base import (
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
class StatisticsTestCase(OpportunitiesBaseTestCase):
    def test_current_year01(self):
        "Empty."
        self.create_user()
        self.assertListEqual(
            [],
            CurrentYearStatistics(Opportunity, Organisation)()
        )

    def test_current_year02(self):
        "Several managed organisation + only won."
        user = self.login()
        statf = CurrentYearStatistics(Opportunity, Organisation)

        create_orga = partial(Organisation.objects.create, user=user)
        emitter1 = create_orga(name='Emitter #1', is_managed=True)
        emitter2 = create_orga(name='Emitter #2', is_managed=True)
        target   = create_orga(name='Target')

        filter_phase = SalesPhase.objects.filter
        won_sp     = filter_phase(won=True).first()

        create_opp = partial(
            Opportunity.objects.create,
            user=user, sales_phase=won_sp, closing_date=now(),
        )
        create_opp(name='Opp #1', emitter=emitter1, target=target)
        fmt = _('For {organisation}: {won_stats} / {lost_stats}').format
        self.assertListEqual(
            [
                fmt(
                    organisation=emitter1,
                    won_stats=ngettext(
                        '{count} won opportunity',
                        '{count} won opportunities',
                        1
                    ).format(count=1),
                    lost_stats=ngettext(
                        '{count} lost opportunity',
                        '{count} lost opportunities',
                        0
                    ).format(count=0),
                ),
            ],
            statf(),
        )

        create_opp(name='Opp #2', emitter=emitter1, target=target)
        msg_emitter1 = fmt(
            organisation=emitter1,
            won_stats=ngettext(
                '{count} won opportunity',
                '{count} won opportunities',
                2
            ).format(count=2),
            lost_stats=ngettext(
                '{count} lost opportunity',
                '{count} lost opportunities',
                0
            ).format(count=0),
        )
        self.assertEqual([msg_emitter1], statf())

        create_opp(name='Opp #3', emitter=emitter2, target=target)
        self.assertListEqual(
            [
                msg_emitter1,
                fmt(
                    organisation=emitter2,
                    won_stats=ngettext(
                        '{count} won opportunity',
                        '{count} won opportunities',
                        1
                    ).format(count=1),
                    lost_stats=ngettext(
                        '{count} lost opportunity',
                        '{count} lost opportunities',
                        0
                    ).format(count=0),
                )
            ],
            statf(),
        )

    def test_current_year03(self):
        "Lost opportunities."
        user = self.create_user()

        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='Emitter', is_managed=True)
        target  = create_orga(name='Target')

        filter_phase = SalesPhase.objects.filter
        won_sp     = filter_phase(won=True).first()
        lost_sp    = filter_phase(lost=True).first()
        neutral_sp = filter_phase(won=False, lost=False).first()

        create_opp = partial(
            Opportunity.objects.create,
            user=user, closing_date=now(), emitter=emitter, target=target,
        )
        create_opp(name='Opp #1', sales_phase=lost_sp)
        create_opp(name='Opp #2', sales_phase=lost_sp)
        create_opp(name='Opp #3', sales_phase=lost_sp)
        create_opp(name='Opp #4', sales_phase=won_sp)
        create_opp(name='Opp #5', sales_phase=won_sp)
        create_opp(name='Opp #6', sales_phase=neutral_sp)

        self.assertListEqual(
            [
                _('For {organisation}: {won_stats} / {lost_stats}').format(
                    organisation=emitter,
                    won_stats=ngettext(
                        '{count} won opportunity',
                        '{count} won opportunities',
                        2
                    ).format(count=2),
                    lost_stats=ngettext(
                        '{count} lost opportunity',
                        '{count} lost opportunities',
                        3
                    ).format(count=3),
                ),
            ],
            CurrentYearStatistics(opp_model=Opportunity, orga_model=Organisation)(),
        )

    def test_current_year04(self):
        "Since 1rst january."
        user = self.create_user()

        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='Emitter', is_managed=True)
        target  = create_orga(name='Target')

        filter_phase = SalesPhase.objects.filter
        won_sp     = filter_phase(won=True).first()
        lost_sp    = filter_phase(lost=True).first()

        now_value = now()
        last_year = now_value - relativedelta(years=1)

        create_opp = partial(
            Opportunity.objects.create,
            user=user, closing_date=now_value, emitter=emitter, target=target,
        )
        create_opp(name='Opp #1', sales_phase=lost_sp)
        create_opp(name='Opp #2', sales_phase=lost_sp, closing_date=last_year)
        create_opp(name='Opp #3', sales_phase=lost_sp)
        create_opp(name='Opp #4', sales_phase=won_sp, closing_date=last_year)
        create_opp(name='Opp #5', sales_phase=won_sp)

        self.assertListEqual(
            [
                _('For {organisation}: {won_stats} / {lost_stats}').format(
                    organisation=emitter,
                    won_stats=ngettext(
                        '{count} won opportunity',
                        '{count} won opportunities',
                        1
                    ).format(count=1),
                    lost_stats=ngettext(
                        '{count} lost opportunity',
                        '{count} lost opportunities',
                        2
                    ).format(count=2),
                ),
            ],
            CurrentYearStatistics(Opportunity, Organisation)(),
        )

    def test_current_year05(self):
        "closing_date is hidden."
        user = self.create_user()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('closing_date', {FieldsConfig.HIDDEN: True})],
        )

        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='Emitter', is_managed=True)
        target  = create_orga(name='Target')

        won_sp = SalesPhase.objects.filter(won=True).first()

        Opportunity.objects.create(
            user=user, name='Opp',
            closing_date=now(),
            sales_phase=won_sp,
            emitter=emitter, target=target,
        )

        self.assertListEqual(
            [_('The field «Actual closing date» is hidden ; these statistics are not available.')],
            CurrentYearStatistics(Opportunity, Organisation)(),
        )
