/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022-2023  Hybird

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
        xAxisTickFormat: null,
        barTextFormat: null,
        barTextAlignmentRatio: 0.5,
        barTextVisibleMinSize: 30,
        colors: ["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"],
        margin: 5,
        showLegend: true,
        transition: true,
        visible: true,
        scrollLegend: null,
        legendItemMinWidth: 60
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".tube-chart": {
                font: "10px sans-serif"
            },
            ".tube-chart .bar rect": {
                "shape-rendering": "crispedges"
            },
            ".tube-chart .bar text": {
                "text-anchor": "middle"
            },
            ".tube-chart .bar .dark-bg": {
                "font-weight": "bold"
            }
        });
    },

    exportProps: function() {
        return {
            transition: false,
            drawOnResize: false,
            scrollLegend: false
        };
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".tube-chart");

        if (chart.size() === 0) {
            chart = svg.append('g').attr('class', 'tube-chart d3-chart');
            this._setupChart(sketch, chart, props);
        }

        chart.classed('not-visible', !props.visible);
        this._updateChart(sketch, chart, data, props);
    },

    _setupChart: function(sketch, chart, props) {
        chart.append('g').attr('class', 'x axis');

        chart.append('g').attr('class', 'bars');

        var legend = chart.append('g').attr('class', 'legend');

        this.scroll = creme.d3Scroll().target(legend);
    },

    _updateChart: function(sketch, chart, data, props) {
        var scrollLegend = props.scrollLegend;
        var bounds = creme.svgBounds(sketch.size(), props.margin, {
            left: 5,
            right: 5
        });
        var colors = creme.d3ColorRange(props.colors, {size: data.length});
        var colorScale = d3.scaleOrdinal().domain([0, data.length]).range(colors);

        var xscale = d3.scaleLinear();
        var colorize = creme.d3Colorize().scale(colorScale);

        data = this.hierarchy(data);

        // pre-compute colors
        data = colorize(data);

        var yDataInfo = creme.d3NumericDataInfo(data, function(d) { return d.endX; });
        var barTextFormat = props.barTextFormat || creme.d3NumericFormat(yDataInfo);
        var xAxisTickFormat = props.xAxisTickFormat || creme.d3NumericAxisFormat(yDataInfo);

        var ymax = yDataInfo.max || 1;
        var legendHeight = 0;

        chart.attr('transform', creme.svgTransform().translate(bounds.left, bounds.top));

        if (scrollLegend === null) {
            scrollLegend = Boolean(props.legendItemMinWidth * data.length > bounds.width);
        }

        var legendWidth = scrollLegend ? Math.max(props.legendItemMinWidth * data.length, bounds.width) : bounds.width;

        if (props.showLegend) {
            var legend = chart.select('.legend');
            var itemMaxWidth = Math.ceil(legendWidth / data.length);
            var legendRow = creme.d3LegendRow()
                                    .swatchColor(function(d) { return d.color; })
                                    .swatchSize({width: 16, height: 16})
                                    .text(function(d) { return d.x; })
                                    .interval(itemMaxWidth)
                                    .data(data);

            legend.call(legendRow);

            // Re-calculate bounds with the legend width AFTER text wrap
            legendHeight = Math.ceil(legend.node().getBBox().height);
            legend.classed('legend-scroll', scrollLegend);
        }

        xscale.domain([0, ymax])
              .range([0, bounds.width]);

        var xAxisTicks = yDataInfo.integer ? Math.min(yDataInfo.gap, 8) : 8;

        chart.select('.x.axis')
                  .call(creme.d3BottomAxis()
                                  .scale(xscale)
                                  .tickFormat(xAxisTickFormat)
                                  .minHeight(props.xAxisSize)
                                  .tickWrapWidth(bounds.width / xAxisTicks)
                                  .ticks(xAxisTicks)
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

        var nonzero_data = data.filter(function(d) { return d.y > 0; });

        var items = chart.select('.bars')
                             .attr('transform', creme.svgTransform().translate(0, legendHeight))
                             .selectAll('.bar')
                             .data(nonzero_data);

        var context = {
            bounds: bounds,
            xscale: xscale,
            textformat: barTextFormat,
            textAlignRatio: props.barTextAlignmentRatio,
            textMinVisibleSize: props.barTextVisibleMinSize,
            transition: props.transition
        };

        this._enterStack(items.enter(), context);
        this._updateStack(props.transition ? items.transition() : items, context);
        items.exit().remove();

        if (props.showLegend && scrollLegend) {
            this.scroll.bounds(bounds)
                       .disabled(false)
                       .innerSize({width: legendWidth});

            legend.call(this.scroll);
        } else {
            this.scroll.disabled(true);
        }

        return chart;
    },

    hierarchy: function(data) {
        var acc = 0;

        return data.map(function(d, i) {
            var entry = {
                y: d.y,
                x: d.x,
                index: i,
                startX: acc,
                endX: acc + d.y,
                color: d.color,
                data: d
            };

            acc += d.y;
            return entry;
        });
    },

    itemClasses: function(d, context) {
        var classes = [];

        if (Math.abs(context.xscale(d.y)) < context.textMinVisibleSize) {
            classes.push('hidden-label');
        }

        if (d.isDarkColor) {
            classes.push('dark-bg');
        }

        return classes.join(' ');
    },

    _enterStack: function(enter, context) {
        var self = this;
        var selection = this.selection();

        var xscale = context.xscale;
        var textformat = context.textformat;
        var textAlignRatio = context.textAlignRatio;
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
               .attr("fill", function(d) { return d.color; })
               .on('click', function(e, d) { selection.select(d.index); });

        bar.append('text')
               .attr('dy', '.75em')
               .attr('y', Math.ceil(bounds.height / 2))
               .attr('x', function(d) { return xscale(d.y) * textAlignRatio; })
               .attr('class', function(d) { return self.itemClasses(d, context); })
               .attr('fill', function(d) { return d.textColor; })
               .text(function(d) { return textformat(d.y); });
    },

    _updateStack: function(update, context) {
        var self = this;
        var xscale = context.xscale;
        var textformat = context.textformat;
        var textAlignRatio = context.textAlignRatio;
        var bounds = context.bounds;

        update.selection()
                  .classed('selected', function(d) { return d.data.selected ; });

        update.attr('transform', function(d) {
                  return creme.svgTransform().translate(xscale(d.startX) || 0, 0);
              });

        update.select('rect')
               .attr('width', function(d) { return xscale(d.y); })
               .attr('height', bounds.height)
               .attr("fill", function(d) { return d.color; });

        update.select('text')
                .attr('y', Math.ceil(bounds.height / 2))
                .attr('x', function(d) { return xscale(d.y) * textAlignRatio; })
                .attr('class', function(d) { return self.itemClasses(d, context); })
                .attr('fill', function(d) { return d.textColor; })
                .text(function(d) { return textformat(d.y); });
    }
});

}(jQuery));
