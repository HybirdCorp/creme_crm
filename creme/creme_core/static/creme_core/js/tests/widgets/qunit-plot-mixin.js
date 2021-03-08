(function($) {
    "use strict";

    window.QUnitPlotMixin = {
        assertNoPlot: function(context, element, error) {
            equal(element.creme().widget().plot(), undefined, 'plot element');
            equal($('.jqplot-target', element).length, 0, 'jqplot-target count');

            equal(context.plotSuccess, null, 'no success');

            if (error) {
                equal('' + context.plotError, error);
            } else {
                equal(context.plotError !== null, true, 'has error');
            }
        },

        assertPlot: function(context, element) {
            equal(typeof element.creme().widget().plot(), 'object', 'plot element');
            equal($('.jqplot-target', element).length, 1, 'jqplot-target count');

            deepEqual(context.plotSuccess, element.creme().widget().plot(), 'success');
            equal(context.plotError, null, 'no error');
        },

        assertRasterPlot: function(context, element) {
            equal(element.creme().widget().plot(), undefined, 'plot element');

            var img = $('.jqplot-target img', element);
            equal(img.length, 1, 'jqplot-target count');
            equal(true, img.attr('src').startsWith('data:image/png;base64'));

            deepEqual(context.plotSuccess, element.creme().widget().plot(), 'success');
            equal(context.plotError, null, 'no error');
        },

        assertEmptyPlot: function(context, element) {
            equal(typeof element.creme().widget().plot(), 'object', 'plot element');
            equal($('.jqplot-target', element).length, 0, 'jqplot-target count');

            deepEqual(context.plotSuccess, element.creme().widget().plot(), 'success');
            equal(context.plotError, null, 'no error');
        },

        assertInvalidPlot: function(context, element, error) {
            equal(typeof element.creme().widget().plot(), 'object');
            equal($('.jqplot-target', element).length, 0);

            equal(context.plotSuccess, null, 'no success');

            if (error) {
                equal(context.plotError, error);
            } else {
                equal(context.plotError !== null, true, 'has error');
            }
        },

        resetMockPlotEvents: function() {
            this.plotError = null;
            this.plotSuccess = null;
        },

        bindMockPlotEvents: function(plot) {
            var self = this;

            plot.on('plotSuccess', function(e, plot) {
                self.plotSuccess = plot; self.plotError = null;
            });
            plot.on('plotError', function(e, err) {
                self.plotError = err; self.plotSuccess = null;
            });
        }
    };

}(jQuery));
