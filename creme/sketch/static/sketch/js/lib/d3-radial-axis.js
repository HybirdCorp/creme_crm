/*******************************************************************************
    MIT License

    Copyright (c) 2017-2023 Vasco Asturiano

    Fork from release 1.8.0 (https://github.com/vasturiano/d3-radial-axis)
    and maintained by Hybird Copyright (c) 2023.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
*******************************************************************************/

(function(d3) {
"use strict";

var epsilon = 1e-6;

function identity(x) {
    return x;
}

function number(scale) {
    return function(d) { return +scale(d); };
}

function translate(x, y) {
    return "translate(" + x + "," + y + ")";
}

function center(scale, offset) {
    offset = Math.max(0, scale.bandwidth() - offset * 2) / 2;

    if (scale.round()) {
        offset = Math.round(offset);
    }

    return function(d) {
        return scale(d) + offset;
    };
}

function entering() {
    return !this.__axis;
}

function polar2cart(angle, r) {
    return [Math.sin(angle) * r, -Math.cos(angle) * r];
}

function angularTranslate(angle, radius) {
    return translate.apply(translate, polar2cart(angle, radius));
}

function radialAxis(scale, radius, outer) {
    var tickArguments = [],
        tickValues = null,
        tickFormat = null,
        tickSizeInner = 6,
        tickSizeOuter = 6,
        tickPadding = 12,
        offset = typeof window !== "undefined" && window.devicePixelRatio > 1 ? 0 : 0.5;

    outer = outer || false;
    radius = radius || 1;

    function axis(context) {
        var values = tickValues == null ? (scale.ticks ? scale.ticks.apply(scale, tickArguments) : scale.domain()) : tickValues,
            format = tickFormat == null ? (scale.tickFormat ? scale.tickFormat.apply(scale, tickArguments) : identity) : tickFormat,
            spacing = Math.max(tickSizeInner, 0) + tickPadding,
            angleRange = scale.range(),
            anglePos = (scale.bandwidth ? center : number)(scale.copy(), offset),
            selection = context.selection ? context.selection() : context,
            path = selection.selectAll(".domain").data([null]),
            tick = selection.selectAll(".tick").data(values, scale).order(),
            tickExit = tick.exit(),
            tickEnter = tick.enter().append("g").attr("class", "tick"),
            line = tick.select("line"),
            text = tick.select("text");

        var isFullCircle = Math.abs(angleRange[1] - angleRange[0]) >= 2 * Math.PI;

        path = path.merge(path.enter()
                                  .insert("path", ".tick")
                                      .attr("class", "domain")
                                      .attr("stroke", "currentColor"));

        tick = tick.merge(tickEnter);
        line = line.merge(tickEnter.append("line").attr("stroke", "currentColor"));

        text = text.merge(tickEnter.append("text")
                                        .attr("fill", "currentColor")
                                        .attr("dy", ".35em")
                                        .attr("text-anchor", "middle"));

        if (context !== selection) {
            path = path.transition(context);
            tick = tick.transition(context);
            line = line.transition(context);
            text = text.transition(context);

            tickExit = tickExit.transition(context)
                                    .attr("opacity", epsilon)
                                    .attr("transform", function(d) {
                                        var pos = anglePos(d);
                                        return isFinite(pos) ? angularTranslate(pos + offset, radius) : this.getAttribute("transform");
                                     });

            tickEnter.attr("opacity", epsilon)
                     .attr("transform", function(d) {
                         var p = this.parentNode.__axis;
                         var pos = p ? p(d) : NaN;
                         pos = isFinite(pos) ? pos : anglePos(d);
                         return angularTranslate(pos + offset, radius);
                     });
        }

        tickExit.remove();

        function getTickPath(angle, r) {
            return (
                'M' + polar2cart(angle, r + tickSizeOuter * (outer ? 1 : -1)).join(',') +
                'L' + polar2cart(angle, r).join(',')
            );
        }

        function getArcPath(startAngle, endAngle, r) {
            var isLargeArc = Math.abs(endAngle - startAngle) % (2 * Math.PI) > Math.PI;
            var isClockWise = endAngle > startAngle;

            return (
                'M' + polar2cart(startAngle, r).join(',') + // go to 'start'
                (
                    isFullCircle ? (
                        'A' + [r, r, 0, 1, 1].concat(polar2cart(startAngle + Math.PI, r)).join(',')  + // draw arc to 'start' + PI
                        'A' + [r, r, 0, 1, 1].concat(polar2cart(startAngle, r)).join(',')              // draw another half arc back to 'start'
                    ) : (
                        'A' + [r, r, 0, isLargeArc ? 1 : 0, isClockWise ? 1 : 0].concat(polar2cart(endAngle, r)).join(',')
                    )
                )
            );
        }

        path.attr('d', getArcPath(angleRange[0], angleRange[1], radius) + getTickPath(angleRange[0], radius));

        tick.attr("opacity", 1)
            .attr("transform", function(d) {
                return angularTranslate(anglePos(d), radius);
            });

        line.attr('x1', 0)
            .attr('y1', 0)
            .attr('x2', function(d) { return polar2cart(anglePos(d), tickSizeInner)[0] * (outer ? 1 : -1); })
            .attr('y2', function(d) { return polar2cart(anglePos(d), tickSizeInner)[1] * (outer ? 1 : -1); });

        text.attr('x', function(d) { return polar2cart(anglePos(d), spacing)[0] * (outer ? 1 : -1); })
            .attr('y', function(d) { return polar2cart(anglePos(d), spacing)[1] * (outer ? 1 : -1); })
            .text(format);

        selection.filter(entering)
                     .attr("fill", "none")
                     .attr("font-size", 10)
                     .attr("font-family", "sans-serif");

        selection.each(function() { this.__axis = anglePos; });
    }

    axis.scale = function(_) {
        /* eslint-disable-next-line no-return-assign */
        return arguments.length ? (scale = _, axis) : scale;
    };

    axis.radius = function(_) {
        /* eslint-disable-next-line no-return-assign */
        return arguments.length ? (radius = +_, axis) : radius;
    };

    axis.ticks = function(_) {
        /*
         * Sets the arguments that will be passed to scale.ticks and scale.tickFormat
         * when the axis is rendered, and returns the axis generator.
         *
         * Convenience alias of tickArguments:
         * axis.ticks('A', 0) means axis.tickArguments(['A', 0])
         */
        tickArguments = Array.from(arguments);
        return axis;
    };

    axis.tickArguments = function(_) {
        if (arguments.length) {
            tickArguments = _ == null ? [] : Array.from(_);
            return axis;
        } else {
            return tickArguments && tickArguments.slice();
        }
    };

    axis.tickValues = function(_) {
        if (arguments.length) {
            tickValues = _ == null ? [] : Array.from(_);
            return axis;
        } else {
            return tickValues && tickValues.slice();
        }
    };

    axis.tickFormat = function(_) {
        if (arguments.length) {
            tickFormat = _;
            return axis;
        } else {
            return tickFormat;
        }
    };

    axis.tickSize = function(_) {
        if (arguments.length) {
            tickSizeInner = tickSizeOuter = +_;
            return axis;
        } else {
            return outer ? tickSizeOuter : tickSizeInner;
        }
    };

    axis.tickSizeInner = function(_) {
        if (arguments.length) {
            tickSizeInner = +_;
            return axis;
        } else {
            return tickSizeInner;
        }
    };

    axis.tickSizeOuter = function(_) {
        if (arguments.length) {
            tickSizeOuter = +_;
            return axis;
        } else {
            return tickSizeOuter;
        }
    };

    axis.tickPadding = function(_) {
        if (arguments.length) {
            tickPadding = +_;
            return axis;
        } else {
            return tickPadding;
        }
    };

    axis.offset = function(_) {
        if (arguments.length) {
            offset = +_;
            return axis;
        } else {
            return offset;
        }
    };

    axis.outer = function(_) {
        if (arguments.length) {
            outer = _ || false;
            return axis;
        } else {
            return outer;
        }
    };

    return axis;
}

d3.axisRadialInner = function(scale, radius) {
    return radialAxis(scale, radius, false);
};

d3.axisRadialOuter = function(scale, radius) {
    return radialAxis(scale, radius, true);
};

}(d3));
