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

(function() {
"use strict";

function Transform() {
    this._ops = [];
}

function toNumber(value) {
    return +value || 0;
}

Transform.prototype = {
    translate: function() {
        this._ops.push({
            op: 'translate',
            args: Array.from(arguments).map(toNumber)
        });
        return this;
    },

    rotate: function() {
        this._ops.push({
            op: 'rotate',
            args: Array.from(arguments).map(toNumber)
        });
        return this;
    },

    scale: function(x, y) {
        this._ops.push({
            op: 'scale',
            args: Array.from(arguments).map(toNumber)
        });
        return this;
    },

    toString: function() {
        return this._ops.map(function(o) {
            return o.op + '(' + o.args.join(',') + ')';
        }).join(' ');
    }
};

creme.svgTransform = function() {
    return new Transform();
};

creme.svgRulesAsCSS = function(rules) {
    return Object.entries(rules).map(function(rule) {
        var selector = rule[0];
        var props = rule[1] || {};

        Assert.not(Object.isEmpty(selector), 'CSS selector must be a non empty string');

        if (Object.isString(props)) {
            return selector + ' { ' + props + '; }';
        } else {
            return selector + ' { ' + Object.entries(props).map(function(prop) {
                return '' + prop[0] + ': ' + prop[1];
            }).join('; ') + '; }';
        }
    }).join('\n');
};

creme.svgBounds = function(bounds) {
    bounds = bounds || {};

    var margin = {
        top: 0,
        left: 0,
        right: 0,
        bottom: 0
    };

    if (arguments.length > 1) {
        for (var i = 1; i < arguments.length; ++i) {
            var m = arguments[i];

            if (Object.isNumber(m) || Object.isString(m)) {
                m = +m;

                margin.top += m;
                margin.left += m;
                margin.right += m;
                margin.bottom += m;
            } else {
                margin.top += +(m.top) || 0;
                margin.left += +(m.left) || 0;
                margin.right += +(m.right) || 0;
                margin.bottom += +(m.bottom) || 0;
            }
        }
    }

    return {
        top: Math.max(0, margin.top) + (bounds.top || 0),
        left: Math.max(0, margin.left) + (bounds.left || 0),
        width: Math.max(0, (bounds.width || 0) - margin.right - margin.left),
        height: Math.max(0, (bounds.height || 0) - margin.top - margin.bottom)
    };
};

creme.svgBoundsRadius = function(bounds) {
    return Math.min(bounds.width || 0, bounds.height || 0) / 2;
};

creme.svgAsXml = function(svg, options) {
    options = options || {};

    Assert.that(
        svg instanceof window.HTMLElement || svg instanceof window.SVGElement,
        'Not an HTML or SVG element : ${e}', {e: svg}
    );

    return [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}" height="${height}">',
            svg.innerHTML,
        '</svg>'
    ].join('\n').template({
        width: options.width || (svg.getAttribute('width') || 'auto'),
        height: options.height || (svg.getAttribute('height') || 'auto')
    });
};

creme.svgAsDataURI = function(svg, options) {
    function _encodeURIEntity(match, val) {
        var char = String.fromCharCode(parseInt(val, 16));
        return char === '%' ? '%25' : char;
    }

    function _reEncodeURI(uri) {
        return decodeURIComponent(
           encodeURIComponent(uri).replace(/%([0-9A-F]{2})/g, _encodeURIEntity)
        );
    }

    return 'data:image/svg+xml;base64,' + window.btoa(_reEncodeURI(creme.svgAsXml(svg, options)));
};

creme.svgAsBlob = function(done, svg, options) {
    options = Object.assign({
        encoderType: 'image/svg+xml',
        encoderQuality: 0.8
    }, options || {});

    Assert.that(Object.isFunc(done), 'A callback is required to get the SVG blob');

    if (options.encoderType === 'image/svg+xml') {
        done(
            new Blob([
                '<?xml version="1.0" standalone="no"?>',
                creme.svgAsXml(svg, options)
            ], { type: "image/svg+xml;charset=utf-8" })
        );
    } else {
        creme.svgAsCanvas(function(canvas) {
            if (Object.isFunc(canvas.msToBlob)) {
                canvas.msToBlob(done, options.encoderType, options.encoderQuality);
            } else {
                canvas.toBlob(done, options.encoderType, options.encoderQuality);
            }
        }, svg, options);
    }
};

creme.svgAsCanvas = function(done, svg, options) {
    options = options || {};

    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    var pixelRatio = window.devicePixelRatio || 1;

    var width = +options.width || (svg.getAttribute('width') || 100);
    var height = +options.height || (svg.getAttribute('height') || 100);

    canvas.width = width * pixelRatio;
    canvas.height = height * pixelRatio;
    canvas.style.width = '' + canvas.width + 'px';
    canvas.style.height = '' + canvas.height + 'px';
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

    Assert.that(Object.isFunc(done), 'A callback is required to get the SVG canvas');

    if (Object.isNone(window.canvg) === false) {
        window.canvg(canvas, creme.svgAsXml(svg, options));
        done(canvas);
    } else {
        creme.svgAsImage(function(image) {
            if (image) {
                try {
                    context.drawImage(image, 0, 0);
                } catch (e) {
                    console.error('There was an error drawing the SVG within the canvas', e);
                    done(null);
                }

                done(canvas);
            } else {
                done(null);
            }
        }, svg, options);
    }

    return canvas;
};

creme.svgAsImage = function(done, svg, options) {
    Assert.that(Object.isFunc(done), 'A callback is required to get the SVG image');

    var image = document.createElement('img');
    var uri = creme.svgAsDataURI(svg, options);

    image.onload = function() {
        done(image);
    };

    image.onerror = function() {
        console.error('There was an error loading the data URI as an image', uri);
        done(null);
    };

    image.src = uri;

    return image;
};

creme.svgScreenCTMatrix = function(node) {
    // Get parent node with screen matrix
    while (node.getScreenCTM == null && node.parentNode != null) {
        node = node.parentNode;
    }

    return node.getScreenCTM();
};

creme.d3FontSize = function(select) {
    if (select.size() > 1) {
        return creme.d3Map(select, function(d) {
            return parseFloat(window.getComputedStyle(this).fontSize) || 0;
        });
    } else if (select.size() > 0) {
        return parseFloat(window.getComputedStyle(select.node()).fontSize) || 0;
    } else {
        return 0;
    }
};

creme.d3NumericDataInfo = function(data, getter) {
    data = data || [];
    getter = getter || function (d) { return d; };

    if (data.length === 0) {
        return {
            integer: true,
            min: 0,
            max: 0,
            gap: 0,
            average: 0
        };
    }

    var min = 0, max = 0, onlyInt = true, sum = 0;

    data.forEach(function(d) {
        var value = parseFloat(getter(d));
        onlyInt = onlyInt && Number.isInteger(value);
        min = isNaN(value) ? min : Math.min(min, value);
        max = isNaN(value) ? max : Math.max(max, value);
        sum += isNaN(value) ? 0 : value;
    });

    return {
        min: min,
        max: max,
        gap: Math.abs(max - min),
        average: sum / data.length,
        integer: onlyInt
    };
};

creme.d3NumericFormat = function(info) {
    if (info.integer) {
        if (info.gap < 10000) {
            return d3.format('~s');
        } else {
            return d3.format('.3s');
        }
    } else {
        if (info.gap < 100) {
            return d3.formatPrefix('.2', 1);
        } else if (info.gap < 5000) {
            return d3.format('~s');
        } else if (info.gap < 10000) {
            return d3.format('.2s');
        } else {
            return d3.format('.3s');
        }
    }
};

creme.d3NumericAxisFormat = function(info) {
    if (info.integer) {
        if (info.gap < 1000) {
            return d3.format('~s');
        } else {
            return d3.format('.2s');
        }
    } else {
        if (info.gap < 100) {
            return d3.formatPrefix('.2', 1);
        } else {
            return d3.format('.2s');
        }
    }
};

creme.d3Map = function(select, func) {
    var res = [];

    select.each(function(datum, i, nodes) {
        res.push(func.apply(this, [datum, i, nodes]));
    });

    return res;
};

creme.d3PreventResizeObserverLoop = function(callback) {
    /*
     * Prevent an issue caused by the infinite loop detection of the
     * ResizeObserver : an observed element should NEVER be resized within the observer callback !
     *
     * It sometimes happens for whatever reason, mostly in unit tests.
     *
     * This "decorator" returns a function to use as ResizeObserver callback and
     * follows those steps:
     *    1. get the "initial" sizes of all elements
     *    2. call the "decorated" callback as usual
     *    3. get the sizes of all elements and filter those that has changed
     *    4. remove the changed elements from the observer to prevent the infinite loop
     *    5. wait for the next "AnimationFrame" before observing these elements again.
     */
    return function(entries, observer) {
        var previousSizes = entries.map(function(entry) {
            return entry.target.getBoundingClientRect();
        });

        try {
            callback(entries, observer);
        } finally {
            var resizedElements = entries.filter(function(entry, i) {
                var size = entry.target.getBoundingClientRect();
                var previousSize = previousSizes[i];

                return (
                    size.width !== previousSize.width ||
                    size.height !== previousSize.height
                );
            }).map(function(event) {
                return event.target;
            });

            resizedElements.forEach(function(element) {
                observer.unobserve(element);
            });

            window.requestAnimationFrame(function() {
                resizedElements.forEach(function(element) {
                    observer.observe(element);
                });
            });
        }
    };
};

}());
