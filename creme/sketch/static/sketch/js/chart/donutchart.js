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

creme.D3DonutChart = creme.D3Chart.sub({
    defaultProps: {
        band: 60,
        margin: 0,
        colors: creme.d3SpectralColors,
        textRadius: 0.8,
        textFormat: null,
        textVisibleMinAngle: Math.PI / 12,
        showLegend: true,
        transition: true,
        visible: true,
        scrollLegend: null,
        legendItemHeight: 25
    },

    _init_: function(options) {
        this._super_(creme.D3Chart, '_init_', options);
    },

    _draw: function(sketch, data, props) {
        var svg = sketch.svg();

        var chart = svg.select(".donut-chart");

        if (chart.size() === 0) {
            chart = svg.append("g").attr('class', 'donut-chart d3-chart');
            this._setupChart(sketch, chart, props);
        }

        chart.classed('not-visible', !props.visible);

        this._updateChart(sketch, chart, data, props);
        return this;
    },

    exportProps: function() {
        return {
            transition: false,
            drawOnResize: false,
            scrollLegend: false
        };
    },

    exportStyle: function(props) {
        return creme.svgRulesAsCSS({
            ".donut-chart": {
                font: "10px sans-serif"
            },
            ".donut-chart .arc path": {
                stroke: "#fff"
            },
            ".donut-chart .slice .hidden-label": {
                visibility: "visible"
            },
            ".donut-chart .slice text.dark-bg": {
                "font-weight": 600
            }
        });
    },

    chartData: function(data) {
        return data.map(function(d, i) {
            return {
                index: i,
                x: d.x,
                y: d.y,
                selected: d.selected,
                color: d.color,
                data: d
            };
        });
    },

    _setupChart: function(sketch, chart, props) {
        chart.append('g').attr('class', 'slices');
        chart.append('g').attr('class', 'legend');

        this.scroll = creme.d3Scroll();
    },

    _updateChart: function(sketch, chart, data, props) {
        var scrollLegend = props.scrollLegend;
        var bounds = creme.svgBounds(sketch.size(), props.margin);
        var colors = creme.d3ColorRange(props.colors, {size: data.length});

        var textFormat = props.textFormat || creme.d3NumericFormat(
            creme.d3NumericDataInfo(data, function(d) { return d.y; })
        );

        data = this.chartData(data);

        var colorScale = d3.scaleOrdinal()
                               .domain([0, data.length])
                               .range(creme.d3ColorRange(colors));

        var colorize = creme.d3Colorize().scale(colorScale);

        var pielayout = d3.pie()
                          .sort(null)
                          .value(function(d) { return d.y; });

        if (props.showLegend) {
            var legends = creme.d3LegendColumn()
                                    .swatchColor(function(d) { return d.color; })
                                    .swatchSize({width: 20, height: props.legendItemHeight})
                                    .spacing(0)
                                    .text(function(d) { return d.x; })
                                    .data(data);

            chart.select('.legend')
                     .attr("transform", creme.svgTransform().translate(bounds.left, bounds.top))
                     .call(legends);

             // Re-calculate bounds with the legend width AFTER text wrap
             bounds = creme.svgBounds(bounds, {
                 left: chart.select('.legend').node().getBBox().width
             });

             if (scrollLegend === null) {
                 scrollLegend = Boolean(props.legendItemHeight * data.length > bounds.height);
             }

             chart.select('.legend').classed('legend-scroll', scrollLegend);
        }

        var radius = creme.svgBoundsRadius(bounds);

        var arcpath = d3.arc()
                        .innerRadius(props.band > 0 ? Math.max(0, radius - props.band) : 0)
                        .outerRadius(radius);

        var textArc = d3.arc()
                        .innerRadius(radius * props.textRadius)
                        .outerRadius(radius * props.textRadius);

        chart.select('.slices')
             .attr("transform", creme.svgTransform().translate(
                 bounds.left + (bounds.width / 2),
                 bounds.top + (bounds.height / 2)
             ));

        // pre-compute colors
        data = colorize(data);
        data = pielayout(data.filter(function(d) { return d.y > 0; }));

        var items = chart.select('.slices')
                             .selectAll('.slice')
                             .data(data);

        var context = {
            arcpath: arcpath,
            textArc: textArc,
            textVisibleMinAngle: props.textVisibleMinAngle,
            formatValue: textFormat,
            transition: props.transition
        };

        this._enterItem(items.enter(), context);
        this._updateItem(props.transition ? items.transition() : items, context);
        items.exit().remove();

        if (props.showLegend && scrollLegend) {
            var legend = chart.select('.legend');
            var legendHeight = legend.node().getBBox().height;

            this.scroll.bounds(bounds)
                       .disabled(false)
                       .innerSize({height: legendHeight})
                       .wheelScrollDelta(function(e, props) {
                           return {x: 0, y: -e.deltaY * props.wheelScale};
                       });

            legend.call(this.scroll);
        } else {
            this.scroll.disabled(true);
        }

        return chart;
    },

    itemClasses: function(d, context) {
        var classes = [];

        if (Math.abs(d.startAngle - d.endAngle) < context.textVisibleMinAngle) {
            classes.push('hidden-label');
        }

        if (d.data.isDarkColor) {
            classes.push('dark-bg');
        }

        return classes.join(' ');
    },

    _enterItem: function(item, context) {
        var self = this;
        var selection = this.selection();

        var arcpath = context.arcpath;
        var formatValue = context.formatValue;
        var textArc = context.textArc;

        var arc = item.append('g')
                         .attr('class', 'slice')
                         .classed('selected', function(d) { return d.data.selected; });

        arc.append("path")
               .attr('d', arcpath)
               .attr("fill", function(d) { return d.data.color; })
               .on('click', function(e, d) { selection.select(d.data.index); });

        arc.append("text")
               .attr("dy", ".35em")
               .style("text-anchor", "middle")
               .text(function(d) { return formatValue(d.data.y); })
               .attr("transform", function(d) {
                    var pos = textArc.centroid(d);
                    return creme.svgTransform().translate(pos[0], pos[1]);
                })
               .attr('class', function(d) {
                    return self.itemClasses(d, context);
                })
               .attr('fill', function(d) { return d.data.textColor; })
               .classed('dark-bg', function(d) { return d.data.isDarkColor; });
    },

    _updateItem: function(item, context) {
        var self = this;
        var arcpath = context.arcpath;
        var formatValue = context.formatValue;
        var textArc = context.textArc;

        function arcTween(d) {
            this._current = this._current || d;
            var interpolate = d3.interpolate(this._current, d);
            this._current = interpolate(0);
            return function(t) {
                return arcpath(interpolate(t));
            };
        };

        item.selection().classed('selected', function(d) { return d.data.selected; });

        if (context.transition) {
            item.select('path').attrTween("d", arcTween);
        } else {
            item.select('path').attr("d", arcpath);
        }

        item.select('path')
                .attr("fill", function(d) { return d.data.color; });

        item.select("text")
                .text(function(d) { return formatValue(d.data.y); })
                .attr("transform", function(d) {
                     var pos = textArc.centroid(d);
                     return creme.svgTransform().translate(pos[0], pos[1]);
                 })
                .attr('fill', function(d) { return d.data.textColor; })
                .attr('class', function(d) {
                    return self.itemClasses(d, context);
                });
    }
});

}(jQuery));
