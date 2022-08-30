/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022  Hybird

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

creme.D3Sketch = creme.component.Component.sub({
    _init_: function(options) {
        this._events = new creme.component.EventHandler();
        this._elementListeners = {
            resize: this._onContainerResize.bind(this)
        };
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    bind: function(element) {
        Assert.not(this.isBound(), 'D3Sketch is already bound');
        Assert.that(element.length === 1, 'Unable to bind D3Sketch to multiple nor empty selection');

        this._element = element.addClass('d3-sketch');

        var domElement = element.get(0);
        var svg = this._svg = d3.select(domElement).append("svg");

        // Initialize SVG element size
        svg.attr('width', '100%')
           .attr('height', this.containerSize().height)
           .style('display', 'block');

        // IMPORTANT : If the svg is display mode is 'inline-block' (default), the height
        // will be constantly evaluated and the node will grow indefinitely.
        this._resizeObserver = new ResizeObserver(this._onContainerResize.bind(this));
        this._resizeObserver.observe(domElement);

        element.on(this._elementListeners);
        return this;
    },

    unbind: function() {
        Assert.that(this.isBound(), 'D3Sketch is not bound');

        this._resizeObserver.disconnect();
        this._resizeObserver = undefined;

        this._element.off(this._elementListeners);
        this._element.removeClass('d3-sketch');
        this._element = undefined;

        this._svg.remove();
        this._svg = undefined;

        return this;
    },

    on: function(event, listeners, decorator) {
        this._events.on(event, listeners, decorator);
        return this;
    },

    off: function(event, listeners) {
        this._events.off(event, listeners);
        return this;
    },

    clear: function() {
        Assert.that(this.isBound(), 'D3Sketch is not bound');
        this._svg.selectAll('*').remove();
    },

    element: function() {
        return this._element;
    },

    svg: function() {
        return this._svg;
    },

    containerSize: function() {
        if (this.isBound()) {
            return {
                width: this._element.innerWidth(),
                height: this._element.innerHeight()
            };
        } else {
            return {width: 0, height: 0};
        }
    },

    size: function() {
        if (this.isBound()) {
            var style = window.getComputedStyle(this._svg.node());
            var preferred = this.containerSize();

            return {
                width: parseInt(style.width) || preferred.width,
                height: parseInt(style.height) || preferred.height
            };
        } else {
            return {width: 0, height: 0};
        }
    },

    _onContainerResize: function() {
        var preferred = this.containerSize();

        // Force container height (CSS issue with height=auto)
        this._svg.attr('height', preferred.height);

        var svgSize = this.size();

        this._element.trigger(jQuery.Event("sketch-resize"), svgSize);
        this._events.trigger('resize', [svgSize]);
    },

    width: function() {
        return this.isBound() ? this.size().width : 0;
    },

    height: function() {
        return this.isBound() ? this.size().height : 0;
    },

    saveAs: function(done, filename, options) {
        // Computed SVG size is set as default for the blob generation because
        // the attribute value may be '100%' or 'auto' and cause issues
        options = $.extend(this.size(), options);

        Assert.that(this.isBound(), 'D3Sketch is not bound');
        Assert.that(Object.isFunc(done), 'A callback is required to convert and save the SVG.');

        /*
         * HACK FOR UNIT TESTS
         * svgAsBlob callback is call by a img.onload and the current window/global instance may change,
         * so the faked function will be lost.
         */
        var saveAs = FileSaver.saveAs;

        creme.svgAsBlob(function(blob) {
            filename = filename || 'output.svg';

            if (blob) {
                saveAs(blob, filename);
            }

            done(blob, filename);
        }, this._svg.node(), options);
    },

    asImage: function(done, options) {
        // Computed SVG size is set as default for the blob generation because
        // the attribute value may be '100%' or 'auto' and cause issues
        options = $.extend(this.size(), options);

        Assert.that(this.isBound(), 'D3Sketch is not bound');
        Assert.that(Object.isFunc(done), 'A callback is required to convert the SVG as image.');

        return creme.svgAsImage(done, this.svg().node(), options);
    }
});

}(jQuery));

