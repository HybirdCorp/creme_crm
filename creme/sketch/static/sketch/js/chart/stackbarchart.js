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

creme.D3StackBarChart = creme.D3Chart.sub({
    defaultProps: {
        xaxisSize: 30,
        yaxisSize: 20,
        showLegend: true,
        legendSize: 40,
        limits: [],
        limitColor: '#000',
        barTextColor: '#fff',
        barTextFormat: function(d) { return d3.format(",.0f")(d.y); },
        margin: 0,
        colors: ["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"],
        transition: true,
        groupId: function(d) { return d.group; },
        visible: true
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".legend": {
                font: "10px sans-serif",
                "text-anchor": "end"
            },
            ".legend-item text": {
                "text-anchor": "middle"
            },
            ".stack-bar-chart": {
                font: "10px sans-serif"
            },
            ".stack-bar-chart .bar text": {
                "text-anchor": "middle"
            },
            ".stack-bar-chart .bar text.inner": {
                fill: props.barTextColor
            },
            ".stack-bar-chart .bar text.outer": {
                display: "none"
            }
        });
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".stack-bar-chart");

        if (chart.size() === 0) {
            chart = svg.append("g")
                           .attr('class', 'stack-bar-chart d3-chart');

            chart.append('g').attr('class', 'x axis');
            chart.append("g").attr("class", "y axis");
            chart.append('g').attr('class', 'stacks');
            chart.append('g').attr('class', 'limits');

            svg.append('g').attr('class', 'legend');
        }

        chart.classed('not-visible', !props.visible);

        this._updateChart(sketch, chart, data, props);
    },

    _updateChart: function(sketch, chart, data, props) {
        var bounds = creme.svgBounds(sketch.size(), {
            left: props.xaxisSize,
            bottom: props.yaxisSize,
            top: props.showLegend ? props.legendSize : 0
        }, props.margin);

        var xkeys = Array.from(new Set(data.map(function(d) { return d.x; })));
        var stackdata = this.hierarchy(data, props);
        var ymax = d3.max(stackdata, function(d) {
                return d.items.reduce(function(a, d) {
                    return a + d.y;
                }, 0);
            }) || 1;

        var stackscale = d3.scaleBand()
                           .domain(stackdata.map(function(d) { return d.group; }))
                           .rangeRound([0, bounds.width])
                           .paddingInner(0.1);

        var yscale = d3.scaleLinear()
                       .domain([0, ymax])
                       .range([bounds.height, 0])
                       .nice();

        var color = d3.scaleOrdinal().range(props.colors);

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        chart.selectAll('.x.axis')
                .attr('transform', creme.svgTransform().translate(0, bounds.height))
                .call(d3.axisBottom(stackscale).tickSizeOuter(0));

        chart.selectAll('.y.axis')
                .call(d3.axisLeft(yscale).tickSizeOuter(0));

        var context = {
            yscale: yscale,
            stackscale: stackscale,
            xkeys: xkeys,
            color: color,
            text: props.barTextFormat,
            transition: props.transition
        };

        var stacks = chart.select('.stacks')
                              .selectAll('.stack')
                              .data(stackdata);

        this._enterStack(stacks.enter(), context);
        this._updateStack(stacks, context);
        stacks.exit().remove();

        if (props.showLegend) {
            var legends = creme.d3LegendRow()
                                    .swatchColor(context.color)
                                    .swatchSize({width: 36, height: 19})
                                    .data(xkeys.sort());

            sketch.svg().select('.legend').call(legends);
        }

        if (props.limits) {
            var limits = creme.d3LimitStack()
                                    .bounds(bounds)
                                    .color(props.limitColor)
                                    .scale(yscale)
                                    .data(props.limits);

            chart.select('.limits').call(limits);
        }

        return chart;
    },

    hierarchy: function(data, props) {
        var groupId = props.groupId;
        var stack = {};

        data.forEach(function(d, i) {
            var group = groupId(d);
            stack[group] = (stack[group] || []);
            stack[group].push({
                x: d.x,
                y: d.y,
                index: i,
                data: d
            });
        });

        for (var group in stack) {
            var acc = 0;
            stack[group].forEach(function(d, i, items) {
                var prevY = i > 0 ? items[i - 1].y : 0;
                acc += prevY;

                d.startY = acc;
                d.endY = acc + d.y;
            });
        }

        return Object.entries(stack).map(function(entry) {
            return {
                group: entry[0],
                items: entry[1]
            };
        });
    },

    _enterStack: function(stacks, context) {
        var bars = stacks.append('g')
                         .attr('class', 'stack')
                         .attr('transform', function(d) {
                              return creme.svgTransform().translate(context.stackscale(d.group) || 0, 0);
                          })
                         .selectAll('.bar')
                             .data(function(d) { return d.items; });

        this._enterBar(bars.enter(), context);
    },

    _updateStack: function(stacks, context) {
        stacks.attr('transform', function(d) {
            return creme.svgTransform().translate(context.stackscale(d.group) || 0, 0);
        });

        var bars = stacks.selectAll('.bar')
                             .data(function(d) { return d.items; });

        this._enterBar(bars.enter(), context);
        this._updateBar(context.transition ? bars.transition() : bars, context);
        bars.exit().remove();
    },

    _enterBar: function(bars, context) {
        var selection = this.selection();

        var yscale = context.yscale;
        var color = context.color;

        var bar = bars.append('g')
                          .attr('class', 'bar')
                          .classed('selected', function(d) { return d.data.selected; })
                          .attr('transform', function(d) {
                              return creme.svgTransform().translate(0, yscale(d.endY));
                           });

        bar.append('rect')
               .attr('x', 1)
               .attr('title', context.text)
               .attr('width', context.stackscale.bandwidth())
               .attr('height', function(d) { return yscale(d.startY) - yscale(d.endY); })
               .attr("fill", function(d) { return color(d.x); })
               .on('click', function(e, d) { selection.select(d.index); });

        bar.append('text')
               .attr('dy', '0.75em')
               .attr('class', function(d) { return (yscale(d.startY) - yscale(d.endY)) > 16 ? 'inner' : 'outer'; })
               .attr('y', 6)
               .attr('x', Math.ceil(context.stackscale.bandwidth() / 2))
               .text(context.text);

        return bar;
    },

    _updateBar: function(bar, context) {
        var yscale = context.yscale;
        var color = context.color;

        bar.selection()
                .classed('selected', function(d) { return d.data.selected; });

        bar.attr('transform', function(d) {
               return creme.svgTransform().translate(0, yscale(d.endY));
           });

        bar.select('rect')
               .attr('title', context.text)
               .attr('width', context.stackscale.bandwidth())
               .attr('height', function(d) { return yscale(d.startY) - yscale(d.endY); })
               .attr("fill", function(d) { return color(d.x); });

        bar.select('text')
               .attr('class', function(d) { return (yscale(d.startY) - yscale(d.endY)) > 16 ? 'inner' : 'outer'; })
               .attr('y', 6)
               .attr('x', Math.ceil(context.stackscale.bandwidth() / 2))
               .text(context.text);
    }
});

}(jQuery));
