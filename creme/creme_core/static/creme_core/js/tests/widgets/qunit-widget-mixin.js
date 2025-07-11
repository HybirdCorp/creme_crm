(function($) {
    "use strict";

    window.QUnitWidgetMixin = {
        htmlAttrs: function(attrs) {
            return Object.entries(attrs || {}).map(function(opt) {
                var name = opt[0], value = String(opt[1] || '').escapeHTML();
                return '${0}="${1}"'.template([name, value]);
            }).join(' ');
        },

        fillWidgetTag: function(element, options) {
            options = Object.assign({
                widget: '',
                auto: false,
                attrs: {}
            }, options || {});

            element.addClass('ui-creme-widget')
                   .addClass(options.widget)
                   .toggleClass('widget-auto', options.auto)
                   .attr('widget', options.widget);

            Object.entries(options.attrs || {}).forEach(function(e) {
                var key = e[0], value = e[1];
                if (!Object.isNone(value)) {
                    element.attr(key, value);
                }
            });

            return element;
        },

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

        createSelectHtml: function(options) {
            options = Object.assign({
                auto: true,
                choices: [],
                disabled: false,
                readonly: false,
                datatype: 'string',
                multiple: false,
                sortable: false,
                autocomplete: false
            }, options || {});

            var html = (
                '<select widget="ui-creme-dselect"' +
                       ' class="ui-creme-dselect ui-creme-widget${auto}${readonly}"' +
                       '${url}${datatype}${disabled}${multiple}${sortable}${autocomplete}${filter}${cache}${noEmpty}>' +
                    '${options}' +
                '</select>'
            ).template({
                auto: options.auto ? ' widget-auto' : '',
                readonly: options.readonly ? ' is-readonly' : '',
                disabled: options.disabled ? ' disabled' : '',
                multiple: options.multiple ? ' multiple' : '',
                sortable: options.sortable ? ' sortable' : '',
                datatype: options.datatype ? ' datatype="' + options.datatype + '"' : '',
                url: options.url ? ' url="' + options.url + '"' : '',
                autocomplete: options.autocomplete ? ' autocomplete' : '',
                filter: options.filter ? ' filter="' + options.filter + '"' : '',
                cache: options.cache ? ' data-cache="' + options.cache + '"' : '',
                noEmpty: options.noEmpty ? ' data-no-empty="true"' : '',
                options: options.choices.map(function(item) {
                    return '<option value="${value}"${readonly}${disabled}>${label}</option>'.template({
                        value: String(item.id || item.value).replace(/\"/g, '&quot;'),
                        label: String(item.text || item.label).replace(/\"/g, '&quot;'),
                        readonly: item.readonly ? ' readonly' : '',
                        disabled: item.disabled ? ' disabled' : ''
                    });
                }).join('\n')
            });

            return html;
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
            options = Object.assign({
                label: "select a mock",
                labelURL: "mock/label/${id}"
            }, options || {});

            var value = _.pop(options, 'value', '');
            var auto = _.pop(options, 'auto', !noauto);

            var html = (
                '<span class="ui-creme-widget ui-creme-entityselector ${auto}" ${attrs} widget="ui-creme-entityselector">' +
                    '<input type="text" class="ui-creme-entityselector ui-creme-input" value="${value}" />' +
                    '<button type="button"></button>' +
                '</span>'
            ).template({
                auto: auto ? 'widget-auto' : '',
                attrs: this.htmlAttrs(options),
                value: (Object.isNone(_.pop(value)) ? '' : String(value)).escapeHTML()
            });

            return $(html);
        },

        createChainedSelectTag: function(value, noauto) {
            var html = (
                '<span class="ui-creme-widget ui-creme-chainedselect ${auto}" widget="ui-creme-chainedselect">' +
                    '<input type="hidden" class="ui-creme-chainedselect ui-creme-input" value="${value}"/>' +
                    '<ul></ul>' +
                '</span>'
            ).template({
                auto: !noauto ? 'widget-auto' : '',
                value: (Object.isNone(value) ? '' : String(value)).escapeHTML()
            });

            return $(html);
        },

        appendChainedSelectorTag: function(element, name, selector, tag) {
            var item = $((
                '<${tag} chained-name="${name}" class="ui-creme-chainedselect-item"></${tag}>'
            ).template({
                tag: tag || 'li',
                name: name
            }));

            item.append(selector);
            item.appendTo(element.find('ul'));

            return selector;
        },

        appendChainedEntitySelectorTag: function(element, name, options) {
           var selector = this.createEntitySelectorTag(options, true);
           return this.appendChainedSelectorTag(element, name, selector);
        },

        assertDSelectAt: function(widget, name, value, dependencies, url, choices) {
            this.assert.equal(widget.selector(name).length, 1);
            this.assertDSelect(widget.selector(name), value, dependencies, url, choices);
        },

        assertDSelect: function(select, value, dependencies, url, choices) {
            var assert = this.assert;

            assert.equal(Object.isEmpty(select), false);

            if (Object.isEmpty(select)) {
                return;
            }

            assert.equal(select.creme().isActive(), true);
            assert.equal(select.creme().widget().cleanedval(), value);
            assert.deepEqual(select.creme().widget().dependencies(), dependencies);
            assert.equal(select.creme().widget().url(), url);
            assert.deepEqual(select.creme().widget().choices(), choices);
        },

        assertEntitySelect: function(select, value, dependencies, url) {
            var assert = this.assert;

            assert.equal(Object.isEmpty(select), false);

            if (Object.isEmpty(select)) {
                return;
            }

            assert.equal(select.creme().isActive(), true);
            assert.equal(select.creme().widget().cleanedval(), value);
            assert.deepEqual(select.creme().widget().dependencies(), dependencies);
            assert.equal(select.creme().widget().popupURL(), url);
        },

        assertActive: function(element) {
            this.assert.equal(element.hasClass('widget-active'), true, 'is widget active');
        },

        assertNotActive: function(element) {
            this.assert.equal(element.hasClass('widget-active'), false, 'is widget not active');
        },

        assertReady: function(element) {
            this.assertActive(element);
            this.assert.equal(element.hasClass('widget-ready'), true, 'is widget ready');
        },

        assertNotReady: function(element) {
            this.assertActive(element);
            this.assert.equal(element.hasClass('widget-ready'), false, 'is widget not ready');
        }
    };

}(jQuery));
