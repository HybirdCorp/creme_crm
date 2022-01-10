/* istanbul ignore next : already supported by any recent browsers */

/*
(function($) {
"use strict";

creme.layout = creme.layout || {};

creme.layout.SortLayout = creme.layout.Layout.sub({
    _init_: function(options) {
        options = $.extend({
            comparator: function(a, b) { return 0; },
            reverse: false
        }, options || {});

        this._super_(creme.layout.Layout, '_init_', options);

        this.comparator(options.comparator);
        this.reverse(options.reverse);

        this.onLayout(this._onLayout);
        this.onAdded(this.layout);
        this.onRemoved(this.layout);
    },

    comparator: function(comparator) {
        if (comparator === undefined) {
            return this._comparator;
        }

        this._comparator = $.proxy(comparator, this);
        return this;
    },

    reverse: function(reverse) {
        return Object.property(this, '_reverse', reverse);
    },

    _onLayout: function(event, container) {
        var sortables = Array.copy(this.children().get());

        try {
            sortables = sortables.sort(this._comparator);
            sortables = this.reverse() ? sortables.reverse() : sortables;
        } catch (e) {}

        sortables.forEach(function(item) {
            container.append($(item).remove());
        });
    }
});
}(jQuery));
*/
