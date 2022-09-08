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

creme.D3TubeChart = creme.D3Chart.sub({
    defaultProps: {
        xAxisSize: 20,
        xAxisTitle: '',
        xAxisTickFormat: d3.format("~s"),
        barTextFormat: d3.format("~s"),
        colors: ["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"],
        margin: 5,
        showLegend: true,
        transition: true,
        visible: true
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".tube-chart": {
                font: "10px sans-serif"
            },
            ".tube-chart .bar rect": {
                fill: props.barColor,
                "shape-rendering": "crispEdges"
            },
            ".tube-chart .bar.selected rect": {
                fill: props.barSelected
            },
            ".tube-chart .bar text": {
                "text-anchor": "middle"
            },
            ".tube-chart .bar text.inner": {
                fill: props.barTextColor
            },
            ".tube-chart .limit": {
                stroke: "#f6c2d4",
                "z-index": 1
            }
        });
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".tube-chart");

        if (chart.size() === 0) {
            chart = svg.append('g').attr('class', 'tube-chart d3-chart');

            chart.append('g').attr('class', 'x axis');

            chart.append('g').attr('class', 'bars');
            chart.append('g').attr('class', 'legend');
        }

        chart.classed('not-visible', !props.visible);

        if (props.visible) {
            this._updateChart(sketch, chart, data, props);
        }
    },

    _updateChart: function(sketch, chart, data, props) {
        var bounds = creme.svgBounds(sketch.size(), props.margin);
        var color = d3.scaleOrdinal().range(creme.d3ColorRange(props.colors));

        var xscale = d3.scaleLinear();
        var xkeys = data.map(function(d) { return d.x; });

        data = this.hierarchy(data.filter(function(d) {
            return d.y > 0;
        }));

        var ymax = d3.max(data, function(d) { return d.endX; }) || 1;
        var legendHeight = 0;

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        if (props.showLegend) {
            var legends = creme.d3LegendRow()
                                    .swatchColor(color)
                                    .swatchSize({width: 16, height: 16})
                                    .interval(Math.ceil(bounds.width / xkeys.length))
                                    .data(xkeys.sort());

            chart.select('.legend').call(legends);

            // Re-calculate bounds with the legend width AFTER text wrap
            legendHeight = Math.ceil(chart.select('.legend').node().getBBox().height);
        }

        xscale.domain([0, ymax])
              .range([0, bounds.width], 0.1);

        chart.select('.x.axis')
                  .call(creme.d3BottomAxis()
                                  .scale(xscale)
                                  .tickFormat(props.xAxisTickFormat)
                                  .minHeight(props.xAxisSize)
                                  .tickWrapWidth(bounds.width / 10)
                                  .label(props.xAxisTitle))
                  .attr('transform', function() {
                      return creme.svgTransform().translate(
                          0,
                          bounds.height - Math.floor(this.getBBox().height)
                      );
                  });

        // Re-calculate bounds with the X-axis height AFTER text wrap
        var xAxisHeight = Math.floor(chart.select('.x.axis').node().getBBox().height);

        bounds = creme.svgBounds(bounds, {
            top: legendHeight,
            bottom: xAxisHeight
        });

        var items = chart.select('.bars')
                             .attr('transform', creme.svgTransform().translate(0, legendHeight))
                             .selectAll('.bar')
                             .data(data);

        var context = {
            bounds: bounds,
            xscale: xscale,
            color: color,
            textformat: props.barTextFormat,
            transition: props.transition
        };

        this._enterStack(items.enter(), context);
        this._updateStack(props.transition ? items.transition() : items, context);
        items.exit().remove();

        return chart;
    },

    hierarchy: function(data) {
        var acc = 0;

        return data.map(function(d, i) {
            data = {
                y: d.y,
                x: d.x,
                index: i,
                startX: acc,
                endX: acc + d.y,
                data: d
            };

            acc += d.y;
            return data;
        });
    },

    _enterStack: function(enter, context) {
        var selection = this.selection();

        var xscale = context.xscale;
        var color = context.color;
        var textformat = context.textformat;
        var bounds = context.bounds;

        var bar = enter.append('g')
                          .attr('class', 'bar')
                          .classed('selected', function(d) { return d.data.selected ; })
                          .attr('transform', function(d) {
                              return creme.svgTransform().translate(xscale(d.startX) || 0, 0);
                          });

        bar.append('rect')
               .attr('x', 1)
               .attr('width', function(d) { return xscale(d.y); })
               .attr('height', bounds.height)
               .attr("fill", function(d) { return color(d.x); })
               .on('click', function(e, d) { selection.select(d.index); });

        bar.append('text')
               .attr('dy', '.75em')
               .attr('y', Math.ceil(bounds.height / 2))
               .attr('x', function(d) { return (bounds.width - xscale(d.y)) > 15 ? 6 : -12; })
               .text(function(d) { return textformat(d.y); });
    },

    _updateStack: function(update, context) {
        var xscale = context.xscale;
        var color = context.color;
        var textformat = context.textformat;
        var bounds = context.bounds;

        update.selection()
                  .classed('selected', function(d) { return d.data.selected ; });

        update.attr('transform', function(d) {
                  return creme.svgTransform().translate(xscale(d.startX) || 0, 0);
              });

        update.select('rect')
               .attr('width', function(d) { return xscale(d.y); })
               .attr('height', bounds.height)
               .attr("fill", function(d) { return color(d.x); });

        update.select('text')
                .attr('y', Math.ceil(bounds.height / 2))
                .attr('x', function(d) { return (bounds.width - xscale(d.y)) > 15 ? 6 : -12; })
                .text(function(d) { return textformat(d.y); });
    }
});

}(jQuery));
