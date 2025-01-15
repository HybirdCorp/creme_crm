/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022-2025  Hybird

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

creme.D3Chart = creme.component.Component.sub({
    defaultProps: {},

    _init_: function(options) {
        options = options || {};

        this._props = Object.assign({
            drawOnResize: true
        }, this.defaultProps);

        this._events = new creme.component.EventHandler();
        this._selection = new creme.model.SelectionController();

        this._modelListeners = {
            update: this._onModelUpdate.bind(this),
            add:    this._onModelAdd.bind(this),
            remove: this._onModelRemove.bind(this),
            reset:  this._onModelReset.bind(this)
        };

        this._sketchListeners = {
            resize: _.debounce(this._onSketchResize.bind(this), 200)
        };

        this.props(options);
    },

    props: function(props) {
        if (props === undefined) {
            return Object.assign({}, this._props);
        }

        this._props = Object.assign(this._props || {}, props);
        return this;
    },

    prop: function(name, value) {
        if (value === undefined) {
            return this._props[name];
        } else {
            this._props[name] = value;
            return this;
        }
    },

    selection: function(selection) {
        return this._selection;
    },

    on: function(event, listeners, decorator) {
        this._events.on(event, listeners, decorator);
        return this;
    },

    off: function(event, listeners) {
        this._events.off(event, listeners);
        return this;
    },

    hasCanvas: function() {
        return !Object.isNone(this._sketch);
    },

    sketch: function(sketch) {
        if (sketch === undefined) {
            return this._sketch;
        }

        Assert.is(sketch, creme.D3Sketch, '${sketch} is not a creme.D3Sketch', {sketch: sketch});

        if (this._sketch) {
            this._sketch.off(this._sketchListeners);
        }

        this._sketch = sketch;
        this._sketch.on(this._sketchListeners);

        return this;
    },

    model: function(model) {
        if (model === undefined) {
            return this._model;
        }

        if (Array.isArray(model)) {
            model = new creme.model.Array(model);
        } else {
            Assert.is(model, creme.model.Collection, '${model} is not a valid data model', {model: model});
        }

        var previous = this._model;

        if (previous !== undefined) {
            previous.unbind(this._modelListeners);
        }

        if (!Object.isNone(model)) {
            model.bind(this._modelListeners);
        }

        this._selection.model(model);
        this._model = model;
        return this;
    },

    draw: function() {
        var sketch = this.sketch();

        Assert.not(Object.isNone(sketch), 'D3Chart must have a target sketch to draw on');
        Assert.that(sketch.isBound(), 'D3Chart sketch is not bound');

        var data = this.model() ? this.model().all() : [];

        this._draw(sketch, data, this.props());
        return this;
    },

    saveAs: function(done, filename, options) {
        var data = this.model() ? this.model().all() : [];
        var props = Object.assign(this.props(), this.exportProps());

        options = Object.assign(options || {}, this.exportOptions(data, options, props));

        this._withShadowSketch(options, function(sketch) {
            this._export(sketch, data, props);
            sketch.saveAs(done, filename, options);
        });

        return this;
    },

    asImage: function(done, options) {
        var data = this.model() ? this.model().all() : [];
        var props = Object.assign(this.props(), this.exportProps());

        options = Object.assign(options || {}, this.exportOptions(data, options, props));

        return this._withShadowSketch(options, function(sketch) {
            this._export(sketch, data, props);
            return sketch.asImage(done);
        });
    },

    exportOptions: function(data, options, props) {
        return {};
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            "g": {
                font: "10px sans-serif"
            }
        });
    },

    exportProps: function() {
        return {};
    },

    _withShadowSketch: function(options, callable) {
        Assert.that(this.hasCanvas(), 'D3Chart must have a target sketch to draw on');

        options = Object.assign(this.sketch().size(), options || {});

        var id = _.uniqueId('shadow-d3sketch');
        var element = $('<div>').css({
            width: options.width,
            height: options.height,
            display: 'absolute',
            left: -10000,
            top: -10000
        }).attr('id', id);

        // Prevent potential issues by ignoring resize events
        var canvas = new creme.D3Sketch({ignoreResize: true}).bind(element);

        try {
            element.appendTo('body');
            return callable.bind(this)(canvas);
        } finally {
            try {
                canvas.unbind();
            } finally {
                element.remove();
            }
        }
    },

    _export: function(sketch, data, props) {
        var style = this.exportStyle(props);

        sketch.svg().append('style').text(Object.isString(style) ? style : creme.svgRulesAsCSS(style));

        this._draw(sketch, data, props);
    },

    _draw: function(sketch, data, props) {
        throw new Error('Not implemented');
    },

    _onSketchResize: function() {
        if (this.prop('drawOnResize')) {
            this.draw();
        }
    },

    _onModelUpdate: function(event, data, start, end, previous, action) {
        if (action !== 'reset') {
            this.draw();
        }
    },

    _onModelAdd: function(event, data, start, end, action) {
        if (action !== 'reset') {
            this.draw();
        }
    },

    _onModelRemove: function(event, data, start, end, action) {
        if (action !== 'reset') {
            this.draw();
        }
    },

    _onModelReset: function(event, data) {
        this.draw();
    }
});

}(jQuery));
