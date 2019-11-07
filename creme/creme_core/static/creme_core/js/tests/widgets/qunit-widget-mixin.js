(function($) {
    "use strict";

    window.QUnitWidgetMixin = {
        createDynamicInputTag: function(value, noauto) {
            var select = $('<input type="text" widget="ui-creme-dinput" class="ui-creme-dinput ui-creme-widget"/>');

            if (value !== undefined) {
                select.attr('value', value);
            }

            if (!noauto) {
                select.addClass('widget-auto');
            }

            return select;
        },

        createDynamicSelectTag: function(url, noauto) {
            var select = $('<select widget="ui-creme-dselect" class="ui-creme-dselect ui-creme-widget"/>');

            if (url !== undefined) {
                select.attr('url', url);
            }

            if (!noauto) {
                select.addClass('widget-auto');
            }

            return select;
        },

        appendOptionTag: function(element, label, value) {
            var choice = $('<option value="' + (value.replace ? value.replace(/\"/g, '&quot;') : value) + '">' + label + '</option>');
            $(element).append(choice);
            return choice;
        },

        appendOptionGroupTag: function(element, label) {
            var group = $('<optgroup label="' + (label.replace ? label.replace(/\"/g, '&quot;') : label) + '"></optgroup>');
            $(element).append(group);
            return group;
        },

        createEntitySelectorTag: function(options, noauto) {
            options = $.extend({
                label: "select a mock",
                labelURL: "mock/label/${id}"
            }, options || {});

            var select = creme.widget.buildTag($('<span/>'), 'ui-creme-entityselector', options, !noauto)
                             .append($('<button type="button"/>'))
                             .append($('<input type="text" class="ui-creme-entityselector ui-creme-input"/>'));

            return select;
        },

        createChainedSelectTag: function(value, noauto) {
            var element = creme.widget.buildTag($('<span/>'), 'ui-creme-chainedselect', {}, !noauto)
                               .append('<input type="hidden" class="ui-creme-input ui-creme-chainedselect"/>')
                               .append('<ul/>');

            if (value !== undefined) {
                $('input.ui-creme-input', element).val(value);
            }

            return element;
        },

        appendChainedSelectorTag: function(element, name, selector, tag) {
            tag = tag || 'li';

            $('ul', element).append($('<' + tag + '/>').attr('chained-name', name)
                                                       .addClass('ui-creme-chainedselect-item')
                                                       .append(selector));

            return selector;
        },

        appendChainedEntitySelectorTag: function(element, name, options) {
           var selector = this.createEntitySelectorTag(options, true);
           return this.appendChainedSelectorTag(element, name, selector);
        },

        assertDSelectAt: function(widget, name, value, dependencies, url, choices) {
            equal(widget.selector(name).length, 1);
            this.assertDSelect(widget.selector(name), value, dependencies, url, choices);
        },

        assertDSelect: function(select, value, dependencies, url, choices) {
            equal(Object.isEmpty(select), false);

            if (Object.isEmpty(select)) {
                return;
            }

            equal(select.creme().isActive(), true);
            equal(select.creme().widget().cleanedval(), value);
            deepEqual(select.creme().widget().dependencies(), dependencies);
            equal(select.creme().widget().url(), url);
            deepEqual(select.creme().widget().choices(), choices);
        },

        assertEntitySelect: function(select, value, dependencies, url) {
            equal(Object.isEmpty(select), false);

            if (Object.isEmpty(select)) {
                return;
            }

            equal(select.creme().isActive(), true);
            equal(select.creme().widget().cleanedval(), value);
            deepEqual(select.creme().widget().dependencies(), dependencies);
            equal(select.creme().widget().popupURL(), url);
        },

        assertActive: function(element) {
            equal(element.hasClass('widget-active'), true, 'is widget active');
        },

        assertNotActive: function(element) {
            equal(element.hasClass('widget-active'), false, 'is widget not active');
        },

        assertReady: function(element) {
            this.assertActive(element);
            equal(element.hasClass('widget-ready'), true, 'is widget ready');
        },

        assertNotReady: function(element) {
            this.assertActive(element);
            equal(element.hasClass('widget-ready'), false, 'is widget not ready');
        }
    };

}(jQuery));
