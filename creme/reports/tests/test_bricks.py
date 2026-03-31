from functools import partial
from unittest import mock
from uuid import uuid4

from django.db.models.query_utils import Q
from django.template.loader import get_template
from django.urls.base import reverse
from django.utils.timezone import datetime, make_aware
from django.utils.translation import gettext as _

from creme.creme_core.models import FakeOrganisation, InstanceBrickConfigItem
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer
from creme.reports.bricks import (
    ReportChartBrick,
    ReportChartInstanceBrick,
    ReportChartsBrick,
)
from creme.reports.core.chart.hand import _generate_date_format
from creme.reports.core.chart.plot import plot_registry
from creme.reports.models import ReportChart
from creme.reports.tests.base import BaseReportsTestCase
from creme.reports.tests.fake_models import (
    FakeReportsColorCategory,
    FakeReportsDocument,
    FakeReportsFolder,
)


def create_fake_docs(user):
    create_folder = partial(FakeReportsFolder.objects.create, user=user)
    folder1 = create_folder(title='Internal', created=make_aware(datetime(2022, 5, 1)))
    folder2 = create_folder(title='External', created=make_aware(datetime(2022, 5, 1)))

    create_cat = FakeReportsColorCategory.objects.create
    cat_A = create_cat(title='Cat A')
    cat_B = create_cat(title='Cat B')

    create_doc = partial(FakeReportsDocument.objects.create, user=user)
    return (
        create_doc(
            title='Doc#1.1',
            linked_folder=folder1,
            category=cat_A,
            created=make_aware(datetime(2022, 5, 10)),
        ),
        create_doc(
            title='Doc#1.2',
            linked_folder=folder1,
            category=cat_A,
            created=make_aware(datetime(2022, 5, 30)),
        ),
        create_doc(
            title='Doc#2',
            linked_folder=folder2,
            category=cat_B,
            created=make_aware(datetime(2022, 8, 2)),
        ),
    )


def reverse_listview(name, q_filters):
    return get_listview_url(reverse(name), q_filters)


def get_listview_url(url, q_filters):
    if isinstance(q_filters, Q):
        q_filters = [q_filters]

    q = Q()

    for q_object in q_filters:
        q &= q_object if isinstance(q_object, Q) else Q(**q_object)

    return f'{url}?q_filter={QSerializer().dumps(q)}'


@mock.patch('creme.reports.bricks.ReportChartBrick._render')
class D3ReportChartBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    maxDiff = None

    # def test_detailview_display__no_data(self, mock_brick_render):
    def test_render__no_data(self, mock_brick_render):
        user = self.get_root_user()
        chart = self._create_documents_chart(user=user)

        context = self.build_context(user=user, instance=chart)

        brick = ReportChartBrick()
        # brick.detailview_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'chart': chart,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,)
            ),
        })

    # def test_detailview_display(self, mock_brick_render):
    def test_render(self, mock_brick_render):
        user = self.get_root_user()
        chart = self._create_documents_chart(user=user)

        create_fake_docs(user)

        context = self.build_context(user=user, instance=chart)
        data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportChartBrick()
        # brick.detailview_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'chart': chart,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,),
            ),
        })

    # def test_detailview_display__colors(self, mock_brick_render):
    def test_render__colors(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart = self._create_documents_colors_chart(report)

        create_fake_docs(user)

        cat_A, cat_B = FakeReportsColorCategory.objects.all()

        context = self.build_context(user=user, instance=chart)
        data = [
            {
                'x': f'{cat_A}',
                'y': 2,
                'color': f'#{cat_A.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_A.pk}],
                ),
            }, {
                'x': f'{cat_B}',
                'y': 1,
                'color': f'#{cat_B.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_B.pk}],
                ),
            },
        ]

        brick = ReportChartBrick()
        # brick.detailview_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'chart': chart,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,),
            ),
        })


@mock.patch('creme.reports.bricks.ReportChartsBrick._render')
class D3ReportChartsBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def _create_report_charts(self, report):
        return (
            ReportChart.objects.create(
                linked_report=report,
                name='Number of created documents / year',
                abscissa_cell_value='created',
                abscissa_type=ReportChart.Group.YEAR,
                ordinate_type=ReportChart.Aggregator.COUNT,
            ),
            ReportChart.objects.create(
                linked_report=report,
                name='Number of created documents / month',
                abscissa_cell_value='created',
                abscissa_type=ReportChart.Group.MONTH,
                ordinate_type=ReportChart.Aggregator.COUNT,
            ),
        )

    # def test_detailview_display__no_chart(self, mock_brick_render):
    def test_render__no_chart(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)

        context = self.build_context(user=user, instance=report)

        brick = ReportChartsBrick()
        # brick.detailview_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]
        self.assertEqual(render_context['plots'], [*plot_registry])
        self.assertEqual(render_context['rows'], [])

    # def test_detailview_display__no_data(self, mock_brick_render):
    def test_render__no_data(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart_by_year, chart_by_month = self._create_report_charts(report)

        context = self.build_context(user=user, instance=report)

        brick = ReportChartsBrick()
        # brick.detailview_display(context)
        brick.render(context)

        data = []

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.assertEqual(render_context['plots'], [*plot_registry])

        self.assertEqual(render_context['rows'], [
            {
                'chart': chart_by_year,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart_by_year.id,)
                ),
                'props': {
                    plot.name: plot.props(chart=chart_by_year, data=data)
                    for plot in plot_registry
                },
            }, {
                'chart': chart_by_month,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart_by_month.id,)
                ),
                'props': {
                    plot.name: plot.props(chart=chart_by_month, data=data)
                    for plot in plot_registry
                },
            },
        ])

    # def test_detailview_display(self, mock_brick_render):
    def test_render(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart_by_year, chart_by_month = self._create_report_charts(report)

        create_fake_docs(user)

        brick = ReportChartsBrick()
        # brick.detailview_display(self.build_context(user=user, instance=report))
        brick.render(self.build_context(user=user, instance=report))

        chart_by_year_data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        by_month_format = _generate_date_format(year=True, month=True)
        chart_by_month_data = [
            {
                'x': datetime(2022, 5, 1).strftime(by_month_format),  # 05-2022
                'y': 2,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 5},
                    ]
                ),
            }, {
                'x': datetime(2022, 8, 1).strftime(by_month_format),  # 08-2022
                'y': 1,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 8},
                    ],
                ),
            },
        ]

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.maxDiff = None
        self.assertListEqual(
            [
                {
                    'chart': chart_by_year,
                    'data': chart_by_year_data,
                    'instance_brick_count': 0,
                    'settings_update_url': reverse(
                        'reports__update_chart_fetch_settings', args=(chart_by_year.id,),
                    ),
                    'props': {
                        plot.name: plot.props(chart_by_year, chart_by_year_data)
                        for plot in plot_registry
                    },
                }, {
                    'chart': chart_by_month,
                    'data': chart_by_month_data,
                    'instance_brick_count': 0,
                    'settings_update_url': reverse(
                        'reports__update_chart_fetch_settings', args=(chart_by_month.id,),
                    ),
                    'props': {
                        plot.name: plot.props(chart_by_month, chart_by_month_data)
                        for plot in plot_registry
                    },
                },
            ],
            render_context['rows'],
        )

    # def test_detailview_display__colors(self, mock_brick_render):
    def test_render__colors(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart = self._create_documents_colors_chart(report)

        create_fake_docs(user)

        cat_A, cat_B = FakeReportsColorCategory.objects.all()
        data = [
            {
                'x': f'{cat_A}',
                'y': 2,
                'color': f'#{cat_A.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_A.pk}],
                ),
            }, {
                'x': f'{cat_B}',
                'y': 1,
                'color': f'#{cat_B.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_B.pk}],
                ),
            },
        ]

        brick = ReportChartsBrick()
        # brick.detailview_display(self.build_context(user=user, instance=report))
        brick.render(self.build_context(user=user, instance=report))

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.maxDiff = None
        self.assertListEqual(
            [{
                'chart': chart,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'props': {
                    plot.name: plot.props(chart=chart, data=data)
                    for plot in plot_registry
                },
            }],
            render_context['rows'],
        )


@mock.patch('creme.reports.bricks.ReportChartInstanceBrick._render')
class D3ReportChartInstanceBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    # def test_detailview_display__no_data(self, mock_brick_render):
    def test_render__detail__no_data(self, mock_brick_render):
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'reports'], admin_4_apps=['reports'],
        )
        self.add_credentials(role=user.role, all=['VIEW'])
        chart = self._create_documents_chart(user=user)
        ibci = self._create_chart_instance_brick(chart)
        entity = FakeOrganisation.objects.create(user=user, name='Acme')

        context = self.build_context(user=user, instance=entity)

        brick = ReportChartInstanceBrick(ibci)
        # brick.detailview_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                'chart': chart,
                'data': [],
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'plots': [*plot_registry],
                'props': {plot.name: plot.props(chart, []) for plot in plot_registry},
            },
            mock_brick_render.call_args[0][0],
        )

    # def test_detailview_display__invalid_uuid(self, mock_brick_render):
    def test_render__detail__invalid_uuid(self, mock_brick_render):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user)
        uuid_str = str(uuid4())
        ibci = InstanceBrickConfigItem.objects.create(
            entity=report,
            brick_class_id=ReportChartInstanceBrick.id,
            json_extra_data={'chart': uuid_str},
        )

        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        context = self.build_context(user=user, instance=entity)

        brick = ReportChartInstanceBrick(ibci)
        self.assertEqual('creme_core/bricks/generic/error.html', brick.template_name)
        with self.assertNoException():
            get_template(brick.template_name)

        errors = [
            _(
                'It seems the chart has been removed; '
                'please contact your administrator to fix the blocks configuration '
                '(chart UUID is "{}")'
            ).format(uuid_str),
        ]
        self.assertListEqual(errors, brick.errors)
        self.assertTupleEqual((), brick.target_ctypes)

        # brick.detailview_display(context)
        brick.render(context)
        mock_brick_render.assert_called_once()
        self.assertDictEqual(
            {**context, 'errors': errors},
            mock_brick_render.call_args[0][0]
        )

    # def test_detailview_display(self, mock_brick_render):
    def test_render__detail(self, mock_brick_render):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)
        ibci = self._create_chart_instance_brick(chart)
        entity = FakeOrganisation.objects.create(user=user, name='Acme')

        create_fake_docs(user)

        context = self.build_context(user=user, instance=entity)
        data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportChartInstanceBrick(ibci)
        # brick.detailview_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                'chart': chart,
                'data': data,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'plots': [*plot_registry],
                'props': {plot.name: plot.props(chart, data) for plot in plot_registry},
            },
            mock_brick_render.call_args[0][0],
        )

    # def test_home_display__no_data(self, mock_brick_render):
    def test_render__home__no_data(self, mock_brick_render):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)
        ibci = self._create_chart_instance_brick(chart)

        context = self.build_context(user=user)

        brick = ReportChartInstanceBrick(ibci)
        # brick.home_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                'chart': chart,
                'data': [],
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'plots': [*plot_registry],
                'props': {plot.name: plot.props(chart, []) for plot in plot_registry},
            },
            mock_brick_render.call_args[0][0],
        )

    # def test_home_display(self, mock_brick_render):
    def test_render__home(self, mock_brick_render):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)
        ibci = self._create_chart_instance_brick(chart)

        create_fake_docs(user)

        context = self.build_context(user=user)
        data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportChartInstanceBrick(ibci)
        # brick.home_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                'chart': chart,
                'data': data,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'plots': [*plot_registry],
                'props': {plot.name: plot.props(chart, data) for plot in plot_registry},
            },
            mock_brick_render.call_args[0][0],
        )

    # def test_home_display__colors(self, mock_brick_render):
    def test_render__home__colors(self, mock_brick_render):
        user = self.login_as_root_and_get()
        report = self._create_simple_documents_report(user=user)
        chart = self._create_documents_colors_chart(report)
        ibci = self._create_chart_instance_brick(chart)

        create_fake_docs(user)

        cat_A, cat_B = FakeReportsColorCategory.objects.all()

        context = self.build_context(user=user)
        data = [
            {
                'x': f'{cat_A}',
                'y': 2,
                'color': f'#{cat_A.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_A.pk}],
                ),
            }, {
                'x': f'{cat_B}',
                'y': 1,
                'color': f'#{cat_B.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_B.pk}],
                ),
            },
        ]

        brick = ReportChartInstanceBrick(ibci)
        # brick.home_display(context)
        brick.render(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                'chart': chart,
                'data': data,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'plots': [*plot_registry],
                'props': {plot.name: plot.props(chart, data) for plot in plot_registry},
            },
            mock_brick_render.call_args[0][0],
        )

    # def test_home_display__invalid_uuid(self, mock_brick_render):
    def test_render__home__invalid_uuid(self, mock_brick_render):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user)
        uuid_str = str(uuid4())
        ibci = InstanceBrickConfigItem.objects.create(
            entity=report,
            brick_class_id=ReportChartInstanceBrick.id,
            json_extra_data={'chart': uuid_str},
        )

        context = self.build_context(user=user)
        brick = ReportChartInstanceBrick(ibci)
        errors = [
            _(
                'It seems the chart has been removed; '
                'please contact your administrator to fix the blocks configuration '
                '(chart UUID is "{}")'
            ).format(uuid_str),
        ]
        self.assertListEqual(errors, brick.errors)

        # brick.home_display(context)
        brick.render(context)
        mock_brick_render.assert_called_once()
        self.assertDictEqual(
            {**context, 'errors': errors}, mock_brick_render.call_args[0][0],
        )
