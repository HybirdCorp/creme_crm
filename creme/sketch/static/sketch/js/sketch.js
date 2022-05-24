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
        this._elementListeners = {
            resize: this.resize.bind(this)
        };
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    bind: function(element) {
        Assert.not(this.isBound(), 'D3Sketch is already bound');

        this._element = element.addClass('d3-sketch');
        var svg = this._svg = d3.select(element.get()[0]).append("svg");

        svg.attr("width", element.innerWidth())
           .attr("height", element.innerHeight());

        element.on(this._elementListeners);
        return this;
    },

    unbind: function() {
        Assert.that(this.isBound(), 'D3Sketch is not bound');

        this._element.off(this._elementListeners);
        this._element.removeClass('d3-sketch');
        this._element = undefined;

        this._svg.remove();
        this._svg = undefined;

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

    preferredSize: function() {
        if (this.isBound()) {
            return {
                width: this._element.innerWidth(),
                height: this._element.innerHeight()
            };
        } else {
            return {width: 0, height: 0};
        }
    },

    size: function(size) {
        if (this.isBound()) {
            return {
                width: +(this._svg.attr('width')),
                height: +(this._svg.attr('height'))
            };
        } else {
            return {width: 0, height: 0};
        }
    },

    width: function() {
        return this.isBound() ? +(this._svg.attr('width')) : 0;
    },

    height: function() {
        return this.isBound() ? +(this._svg.attr('height')) : 0;
    },

    resize: function(size) {
        if (this.isBound()) {
            size = $.extend({}, this.preferredSize(), size || {});

            this._svg.attr('width', size.width)
                     .attr('height', size.height);

            this._element.trigger(jQuery.Event("sketch-resize", size));
        }

        return this;
    },

    saveAs: function(done, filename, options) {
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
        Assert.that(this.isBound(), 'D3Sketch is not bound');
        Assert.that(Object.isFunc(done), 'A callback is required to convert the SVG as image.');

        return creme.svgAsImage(done, this.svg().node(), options);
    }
});

}(jQuery));

