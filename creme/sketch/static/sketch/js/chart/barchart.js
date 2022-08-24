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

creme.D3BarChart = creme.D3Chart.sub({
    defaultProps: {
        xAxisSize: 20,
        xAxisTitle: '',
        yAxisSize: 30,
        yAxisTitle: '',
        barColor: "#4682b4",
        barHilighted: "#66a2d4",
        barSelected: "#d6c2f4",
        barTextColor: "#fff",
        limits: [],
        margin: 0,
        transition: true,
        visible: true
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".bar-chart": {
                font: "10px sans-serif"
            },
            ".bar-chart .bar rect": {
                "shape-rendering": "crispEdges"
            },
            ".bar-chart .bar.selected rect": {
                "opacity": "0.8"
            },
            ".bar-chart .bar text": {
                "text-align": "center"
            },
            ".bar-chart .bar text.inner": {
                fill: props.barTextColor
            },
            ".bar-chart .limit": {
                stroke: "#f6c2d4",
                "z-index": 1
            }
        });
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".bar-chart");

        if (chart.size() === 0) {
            chart = svg.append('g')
                           .attr('class', 'bar-chart d3-chart');

            chart.append('g').attr('class', 'x axis');

            chart.append("g")
                    .attr("class", "y axis");

            var ytitle = chart.append('text')
                                  .attr('class', 'y axis-title')
                                  .attr('text-anchor', 'start')
                                  .attr('fill', 'currentColor');

            ytitle.append('tspan')
                      .attr('class', 'axis-title-arror')
                      .text('↑');

            ytitle.append('tspan')
                      .attr('class', 'axis-title-label')
                      .attr('dy', '0.1em')
                      .attr('dx', '0.5em');

            chart.append('g').attr('class', 'bars');
            chart.append('g').attr('class', 'limits');
        }

        chart.classed('not-visible', !props.visible);

        this._updateChart(sketch, chart, data, props);
    },

    _updateChart: function(sketch, chart, data, props) {
        var yAxisTitleSize = (props.yAxisTitle ? 20 : 0);
        var xAxisTitleSize = (props.xAxisTitle ? 20 : 0);

        var bounds = creme.svgBounds(sketch.size(), props.margin);
        var barBounds = creme.svgBounds(bounds, {
            left: props.yAxisSize,
            top: yAxisTitleSize / 2
        });

        var xscale = d3.scaleBand().padding(0.1);
        var yscale = d3.scaleLinear();

        var ymax = d3.max(data, function(d) { return d.y; }) || 1;

        var colorScale = d3.scaleOrdinal()
                               .domain([0, data.length])
                               .range(creme.d3ColorRange(props.barColor));

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        xscale.domain(data.map(function(d) { return d.x; }))
              .range([0, barBounds.width], 0.1);

        var xAxis = creme.d3BottomAxis()
                              .scale(xscale)
                              .minHeight(props.xAxisSize)
                              .bounds(barBounds)
                              .label(props.xAxisTitle);

        chart.selectAll('.x.axis')
                .call(xAxis)
                .attr('transform', creme.svgTransform().translate(
                     props.yAxisSize, bounds.height - xAxis.preferredHeight()
                 ));

        barBounds = creme.svgBounds(barBounds, {
            bottom: xAxis.preferredHeight()
        });

        yscale.domain([0, ymax])
              .range([barBounds.height, 0]);

        chart.selectAll('.y.axis')
                .attr('transform', creme.svgTransform().translate(props.yAxisSize, yAxisTitleSize))
                .call(d3.axisLeft(yscale).tickSizeOuter(0));

        chart.selectAll('.y.axis-title')
                .attr('transform', creme.svgTransform().translate(0, yAxisTitleSize / 2))
                .selectAll('.axis-title-label')
                    .text(props.yAxisTitle);

        var items = chart.select('.bars')
                             .attr('transform', creme.svgTransform().translate(props.yAxisSize, xAxisTitleSize))
                             .selectAll('.bar')
                             .data(data);

        var context = {
            bounds: barBounds,
            colorScale: colorScale,
            xscale: xscale,
            yscale: yscale,
            textformat: d3.format(",.0f")
        };

        this._enterBar(items.enter(), context);
        this._updateBar(props.transition ? items.transition() : items, context);
        items.exit().remove();

        if (props.limits) {
            var limits = creme.d3LimitStack()
                                    .bounds(bounds)
                                    .scale(yscale)
                                    .data(props.limits);

            chart.select('.limits').call(limits);
        }

        return chart;
    },

    _enterBar: function(enter, context) {
        var selection = this.selection();

        var xscale = context.xscale;
        var yscale = context.yscale;
        var textformat = context.textformat;
        var bounds = context.bounds;

        var bar = enter.append('g')
                          .attr('class', function(d) { return d.selected ? 'bar selected' : 'bar'; })
                          .attr('transform', function(d) {
                              return creme.svgTransform().translate(xscale(d.x), yscale(d.y));
                          });

        bar.append('rect')
               .attr('x', 1)
               .attr('width', xscale.bandwidth())
               .attr('height', function(d) { return bounds.height - yscale(d.y); })
               .attr("fill", function(d) { return context.colorScale(d.x); })
               .on('click', function(d, i) { selection.select(i); });

        bar.append('text')
               .attr('dy', '.75em')
               .attr('class', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 'inner' : 'outer'; })
               .attr('y', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 6 : -12; })
               .attr('x', Math.ceil(xscale.bandwidth() / 2))
               .text(function(d) { return textformat(d.y); });
    },

    _updateBar: function(update, context) {
        var xscale = context.xscale;
        var yscale = context.yscale;
        var textformat = context.textformat;
        var bounds = context.bounds;

        update.attr('class', function(d) { return d.selected ? 'bar selected' : 'bar'; })
              .attr('transform', function(d) {
                  return creme.svgTransform().translate(xscale(d.x), yscale(d.y));
              });

        update.select('rect')
                .attr("fill", function(d) { return context.colorScale(d.x); })
                .attr('width', xscale.bandwidth())
                .attr('height', function(d) { return bounds.height - yscale(d.y); });

        update.select('text')
                .attr('class', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 'inner' : 'outer'; })
                .attr('y', function(d) { return (bounds.height - yscale(d.y)) > 15 ? 6 : -12; })
                .attr('x', Math.ceil(xscale.bandwidth() / 2))
                .text(function(d) { return textformat(d.y); });
    }
});

}(jQuery));
