/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

(function($) {
"use strict";

creme.widget.Toggle = creme.widget.declare('ui-creme-toggle', {
    options: {
        'ontoggle': undefined
    },

    _create: function(element, options, cb, sync, attributes) {
        var self = this;

        this.trigger(element).each(function() {
            var trigger_options = creme.widget.parseopt($(this), {
                'open-event': null,
                'close-event': null,
                'toggle-event': 'click',
                'recursive': false
            }, {});

            self._bind_trigger(element, $(this), trigger_options);
        });

        this._on_toggle = creme.object.build_callback(options.ontoggle, ['collapsed', 'options']);
        this.toggle(element, this.is_opened(element));

        element.addClass('widget-ready');
    },

    _bind_trigger: function(element, trigger, options) {
        var self = this;
        var toggle_event = options['toggle-event'];
        var open_event   = options['open-event'];
        var close_event  = options['close-event'];

        if (toggle_event != null) { trigger.bind(toggle_event, function() { self.toggle(element, undefined, options); }); }

        if (open_event != null) { trigger.bind(open_event, function() { self.expand(element, options); }); }

        if (close_event != null) { trigger.bind(close_event, function() { self.collapse(element, options); }); }
    },

    trigger: function(element) {
        var triggers =  $('.toggle-trigger', element).filter(function() {
//            return $(this).parents('.ui-creme-toggle:first').is(element);
            return $(this).parents('.ui-creme-toggle').first().is(element);
        });

        return element.is('.toggle-trigger') ? triggers.add(element) : triggers;
    },

    targets: function(element) {
        var targets = $('.toggle-target', element).filter(function() {
//            return $(this).parents('.ui-creme-toggle:first').is(element);
            return $(this).parents('.ui-creme-toggle').first().is(element);
        });

        return element.is('.toggle-target') ? targets.add(element) : targets;
    },

    toggles: function(element) {
        return $('.ui-creme-toggle.widget-ready', element);
    },

    toggle: function(element, open, options) {
        options = options || {};

        var self = this;
        var collapsed = (open === undefined) ? !this.is_closed(element) : !open;

        element.toggleClass('toggle-collapsed', collapsed);

        this.trigger(element).each(function() {
            self._toggle_trigger($(this), collapsed, options);
        });

        this.targets(element).each(function() {
            self._toggle_target($(this), collapsed, options);
        });

        if (options.recursive) {
            this.toggles(element).each(function() {
                $(this).creme().widget().toggle(!collapsed, options);
            });
        }

        if (Object.isFunc(this._on_toggle)) {
            try {
                if (element.is('.widget-ready')) {
                    this._on_toggle.apply(this, [collapsed, options]);
                }
            } catch (e) {
                console.error(e);
            }
        }

        return this;
    },

    expand: function(element, options) {
        return this.toggle(element, true, options);
    },

    collapse: function(element, options) {
        return this.toggle(element, false, options);
    },

    is_opened: function(element) {
        return !element.hasClass('toggle-collapsed');
    },

    is_closed: function(element) {
        return element.hasClass('toggle-collapsed');
    },

    _toggle_trigger: function(trigger, collapsed, options) {
        trigger.toggleClass('toggle-collapsed', collapsed);
        this._toggle_attributes(trigger, collapsed);
    },

    _toggle_target: function(target, collapsed, options) {
        target.toggleClass('toggle-collapsed', collapsed);
        this._toggle_attributes(target, collapsed);

        $('.ui-creme-resizable', target).trigger('resize')
                                        .trigger('resizestop');
    },

    _toggle_attributes: function(target, collapsed) {
        for (var index = 0; index < target[0].attributes.length; ++index) {
            var attr = target[0].attributes[index];

            if (/^toggle\-(close|open)\-[\w\d]+$/.test(attr.name)) {
                var attr_split_name = attr.name.split('-');
                var mode = attr_split_name[1];
                var name = attr_split_name[2];

                if (!collapsed && mode === 'open') {
                    target.attr(name, attr.value);
                } else if (collapsed && mode === 'close') {
                    target.attr(name, attr.value);
                }
            }
        }
    }
});

}(jQuery));
