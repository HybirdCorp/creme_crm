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

/* globals BrowserVersion */
(function($) {
"use strict";

creme.layout = creme.layout || {};

/* istanbul ignore next : already supported by any recent browsers */
/* TODO : remove layout tools */
creme.layout.LayoutResizeSensor = creme.component.Component.sub({
    _OVERFLOW_EVENT:  'OverflowEvent' in window ? 'overflowchanged' : 'overflow',
    _UNDERFLOW_EVENT: 'OverflowEvent' in window ? 'overflowchanged' : 'underflow',

    _init_: function() {
        this._threshold = 100;

        if (BrowserVersion.isIE()) {
            this._sensor = $('<div class="ui-layout resize-sensor" onresize="$(\'body\').resize();">');
        } else {
            this._sensor = $('<div class="ui-layout resize-sensor">' +
                             '    <div class="ui-layout resize-overflow"><div></div></div>' +
                             '    <div class="ui-layout resize-underflow"><div></div></div>' +
                             '</div>');
        }
    },

    isBound: function() {
        return this._target !== undefined;
    },

    bind: function(element) {
        if (this._target !== undefined) {
            throw new Error('Resize sensor already bound');
        }

        this._target = element;

        var prev_width = 0, prev_height = 0;
        var sensor = this._sensor;
        var overflow = $('.resize-overflow', sensor);
        var underflow = $('.resize-underflow', sensor);

        var matchFlow = function(event) {
            var width = sensor[0].offsetWidth;
            var height = sensor[0].offsetHeight;

            if (prev_width === width && prev_height === height) {
                return;
            }

            // console.log('resize ', [width, height], ' ', [prev_width, prev_height])

            element.trigger(jQuery.Event("resize", {width: width, height: height}));

            if (!sensor.parent().is(element)) {
                element.append(sensor);
            }

            width = sensor[0].offsetWidth;
            height = sensor[0].offsetHeight;

            $('> :first', overflow).css('width', width - 1)
                                   .css('height', height - 1);

            $('> :first', underflow).css('width', width + 1)
                                    .css('height', height - 1);

            prev_width = width;
            prev_height = height;
        };

        var flow_cb = $.debounce(matchFlow, this._threshold);

        if (!BrowserVersion.isIE()) {
            this._onOverflow(sensor, flow_cb);
            this._onUnderflow(sensor, flow_cb);
            this._onOverflow(overflow, flow_cb);
            this._onUnderflow(underflow, flow_cb);
        }

        $('body').on('resize', flow_cb);

        this._targetPosition = this._target.css('position');
        this._target.css('position', 'relative');
        this._target.append(this._sensor);

        matchFlow({});
    },

    unbind: function() {
        if (this._target === undefined) {
            throw new Error('Resize sensor not bound');
        }

        $('> div.ui-layout.resize-sensor', this._target).remove();

        this._target.css('position', this._targetPosition);
        this._target = undefined;

        return this;
    },

    _isOverflowEvent: function(e) {
        return e.type === 'overflow' ||
               ((e.orient === 0 && e.horizontalOverflow) ||
                (e.orient === 1 && e.verticalOverflow) ||
                (e.orient === 2 && e.horizontalOverflow && e.verticalOverflow));
    },

    _onOverflow: function(element, overflow) {
        var self = this;
        var event = this._OVERFLOW_EVENT;

        element.bind(event, function(e) {
            if (self._isOverflowEvent(e.originalEvent)) {
                e.flow = 'over';
                overflow.apply(self, [e]);
            }
        });
    },

    _onUnderflow: function(element, underflow) {
        var self = this;
        var event = this._UNDERFLOW_EVENT;

        element.bind(event, function(e) {
            if (self._isOverflowEvent(e.originalEvent) === false) {
                e.flow = 'under';
                underflow.apply(self, [e]);
            }
        });
    }
});

/* istanbul ignore next : already supported by any recent browsers */
/* TODO : remove layout tools */
creme.layout.Layout = creme.component.Component.sub({
    _init_: function(options) {
        console.warn('Layout tools are now deprecated; Use modern CSS instead');
        var self = this;

        options = $.extend({
            resizable: false,
            filter: function() { return true; }
        }, options || {});

        this._resize_cb = function(e, ui) {
            self.fireResize(ui ? ui.size.width : e.width || 0,
                            ui ? ui.size.height : e.height || 0);
        };

        this._add_cb = function(e) { self.fireAdded(e.target); };
        this._remove_cb = function(e) { self.fireRemoved(e.target); };
        this._layout_cb = function() { self.layout(); };
        this._locked = false;
        this._uuid = $.uidGen();

        this._events = new creme.component.EventHandler();

        this.filter(options.filter);
        this.resizable(options.resizable);
    },

    preferredSize: function(element) {
        return creme.layout.preferredSize(element);
    },

    filter: function(filter) {
        if (filter === undefined) {
            return this._filter;
        }

        this._filter = Object.isType(filter, 'string') ? function(item) { $(item).is(filter); } : filter;
        return this;
    },

    resizable: function(resizable) {
        if (resizable === undefined) {
            return this._resizable;
        }

        this._resizable = resizable;
        this._initResizeSensor();

        return this;
    },

    _initResizeSensor: function() {
        if (this._target === undefined) {
            return;
        }

        var resizable = this._resizable;
        var sensor = this._resizeSensor;

        if (!resizable) {
            this._unbindResizeSensor();
            return this;
        }

        if (sensor === undefined) {
            this._resizeSensor = sensor = new creme.layout.LayoutResizeSensor();
        }

        this._bindResizeSensor();
    },

    _bindResizeSensor: function() {
        var sensor = this._resizeSensor;

        if (sensor !== undefined && !sensor.isBound()) {
            sensor.bind(this._target);
        }
    },

    _unbindResizeSensor: function() {
        var sensor = this._resizeSensor;

        if (sensor !== undefined && sensor.isBound()) {
            sensor.unbind(this._target);
        }
    },

    container: function() {
        return this._target;
    },

    children: function() {
        return $('> *:not(.ui-layout)', this._target).filter(this._filter);
    },

    onResize: function(resize) {
        this._events.bind('resize', resize);
        return this;
    },

    onAdded: function(added) {
        this._events.bind('added', added);
        return this;
    },

    onRemoved: function(removed) {
        this._events.bind('removed', removed);
        return this;
    },

    onLayout: function(layout) {
        var self = this;

        this._events.bind('start', function() {
            try {
                layout.apply(this, arguments);
            } catch (e) {}

            self.done();
        });

        return this;
    },

    fireResize: function(width, height) {
        this._events.trigger('resize', [this._target, width, height], this);
        return this;
    },

    fireAdded: function(target) {
        this._events.trigger('added', [this._target, target], this);
        return this;
    },

    fireRemoved: function(target) {
        this._events.trigger('removed', [this._target, target], this);
        return this;
    },

    done: function() {
        this._locked = false;
        this._events.trigger('done', [this._target], this);
        return this;
    },

    layout: function() {
        if (this._locked === true) {
            return this;
        }

        this._locked = true;
        this._events.trigger('start', [this._target], this);
        return this;
    },

    _bindEvents: function() {
        if (Object.isSubClassOf(this._target, creme.layout.Layout)) {
            this._target.onDone(this._layout_cb);
            return;
        }

        this._target.on('resize', this._resize_cb);
        this._target.on($.matchIEVersion(8, 9) ? 'DOMNodeRemoved DOMNodeRemovedFromDocument' : 'DOMNodeRemoved', this._remove_cb);
        this._target.on($.matchIEVersion(8, 9) ? 'DOMNodeInserted DOMNodeInsertedIntoDocument' : 'DOMNodeInserted', this._add_cb);
    },

    _unbindEvents: function() {
        if (Object.isSubClassOf(this._target, creme.layout.Layout)) {
            this._target._events.off('done', this._layout_cb);
            return;
        }

        this._target.on('resize', this._resize_cb);
        this._target.on($.matchIEVersion(8, 9) ? 'DOMNodeRemoved DOMNodeRemovedFromDocument' : 'DOMNodeRemoved', this._remove_cb);
        this._target.on($.matchIEVersion(8, 9) ? 'DOMNodeInserted DOMNodeInsertedIntoDocument' : 'DOMNodeInserted', this._add_cb);
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('Layout is already bound.');
        }

        this._target = $(element);
        this._bindEvents();
        this._initResizeSensor();

        return this;
    },

    unbind: function() {
        if (!this.isBound()) {
            throw new Error('Layout is not bound.');
        }

        this._unbindEvents();
        this._target = undefined;

        return this;
    },

    isBound: function() {
        return this._target !== undefined;
    }
});

creme.layout.preferredSize = function(element, depth) {
    depth = depth || 1;

    var height = 0;
    var width = 0;

    $('> *', element).filter(':visible').each(function() {
        var position = $(this).position();

        if (depth > 1) {
            var size = creme.layout.preferredSize($(this), depth - 1);
            width = Math.max(width, size[0]);
            height = Math.max(height, size[1]);
        }

        width = Math.max(width, position.left + $(this).outerWidth(true));
        height = Math.max(height, position.top + $(this).outerHeight(true));
    });

    return [Math.round(width), Math.round(height)];
};
}(jQuery));
