/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2022  Hybird

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

        var flow_cb = _.debounce(matchFlow, this._threshold);

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
