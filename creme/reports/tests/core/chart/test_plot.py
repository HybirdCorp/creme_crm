from creme.creme_core.tests.base import CremeTestCase
from creme.reports.core.chart import plot


class PlotTestCase(CremeTestCase):
    def test_plot(self):
        name1 = 'barchart'
        label1 = 'Histogram'
        plot1 = plot.Bar(name=name1, label=label1)
        self.assertEqual(name1, plot1.name)
        self.assertEqual(label1, plot1.label)

        # ---
        name2 = 'piechart'
        label2 = 'Pie'
        plot2 = plot.Pie(name=name2, label=label2)
        self.assertEqual(name2, plot2.name)
        self.assertEqual(label2, plot2.label)

    def test_registry(self):
        name1 = 'barchart'
        name2 = 'piechart'

        plot1 = plot.Bar(name=name1, label='Histogram')
        plot2 = plot.Pie(name=name2, label='Pie')
        registry = plot.PlotRegistry().register(plot1, plot2)

        self.assertIs(plot1, registry.get(name1))
        self.assertIs(plot2, registry.get(name2))
        self.assertIsNone(registry.get('invalid'))

        self.assertListEqual([plot1, plot2], [*registry])

        # ---
        registry.unregister(name1)
        self.assertListEqual([plot2], [*registry])

    def test_registry__error__empty(self):
        registry = plot.PlotRegistry()

        with self.assertRaises(plot.PlotRegistry.RegistrationError) as cm:
            registry.register(plot.Bar(name='', label='Histogram'))
        self.assertEqual('The plot name is empty.', str(cm.exception))

    def test_registry__error__duplicate(self):
        registry = plot.PlotRegistry()
        name = 'my_plot'
        registry.register(plot.Bar(name=name, label='Histogram'))

        with self.assertRaises(plot.PlotRegistry.RegistrationError) as cm:
            registry.register(plot.Pie(name=name, label='Pie'))
        self.assertEqual(f'The plot name "{name}" is already used.', str(cm.exception))

    def test_registry__error__unregister(self):
        registry = plot.PlotRegistry()
        name = 'invalid'

        with self.assertRaises(plot.PlotRegistry.UnRegistrationError) as cm:
            registry.unregister(name=name)
        self.assertEqual(f'The plot name "{name}" cannot be found.', str(cm.exception))
