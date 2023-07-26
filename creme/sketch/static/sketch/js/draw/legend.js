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

creme.D3LegendRow = creme.D3Drawable.sub({
    defaultProps: {
        swatchSize: {width: 20, height: 20},
        swatchColor: d3.scaleOrdinal().range([
            "#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"
        ]),
        spacing: 0,
        data: [],
        text: function(d, i) { return d; },
        help: null,
        textWrap: {
            breakAll: true,
            lineHeight: '1.1em'
        }
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var interval = Math.max((props.swatchSize.width || 0) + props.spacing, props.interval || 0);
        var position = function(d, i) {
            return creme.svgTransform().translate((interval / 2) + i * interval, 0);
        };

        var textWrapper = Object.isFunc(props.textWrapper) ? props.textWrapper : creme.d3TextWrap().maxWidth(interval).props(props.textWrap);
        var legend = d3.select(node);
        var items = legend.selectAll('.legend-item').data(props.data || []);

        var newItem = items.enter()
                           .append('g')
                               .attr('class', 'legend-item')
                               .attr("transform", position);

        newItem.append("rect")
                   .attr("width", props.swatchSize.width)
                   .attr("height", props.swatchSize.height)
                   .attr('title', props.help || props.text)
                   .attr("fill", props.swatchColor);

        newItem.append("text")
                   .attr("y", props.swatchSize.height * 1.5)
                   .attr("dx", props.swatchSize.width / 2)
                   .attr("dy", "0.35em")
                   .attr('text-anchor', 'middle')
                   .text(props.text)
                   .call(textWrapper);

        items.attr("transform", position);
        items.select('text')
                .text(props.text)
                .call(textWrapper);
        items.select("rect")
                .attr('title', props.help || props.text)
                .attr("fill", props.swatchColor);

        items.exit().remove();
    }
});

creme.d3LegendRow = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3LegendRow(options),
        props: ['swatchSize', 'swatchColor', 'spacing', 'data', 'text', 'interval', 'helpText', 'textWrap']
    });
};

creme.D3LegendColumn = creme.D3Drawable.sub({
    defaultProps: {
        swatchSize: {width: 20, height: 20},
        swatchColor: d3.scaleOrdinal().range([
            "#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"
        ]),
        spacing: 0,
        data: [],
        text: function(d, i) { return d; }
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var position = function(d, i) {
            return creme.svgTransform().translate(0, i * (props.swatchSize.height + props.spacing));
        };

        var items = d3.select(node).selectAll('.legend-item').data(props.data || []);

        var newItem = items.enter()
                           .append('g')
                               .attr('class', 'legend-item')
                               .attr("transform", position);

        newItem.append("rect")
                   .attr("width", props.swatchSize.width)
                   .attr("height", props.swatchSize.height)
                   .attr('title', props.help || props.text)
                   .attr("fill", props.swatchColor);

        newItem.append("text")
                   .attr("x", props.swatchSize.width)
                   .attr('text-anchor', 'start')
                   .attr('alignment-baseline', 'middle')
                   .attr("y", props.swatchSize.height * 0.5)
                   .attr("dx", "0.31em")
                   .text(props.text);

        items.attr("transform", position);

        items.select("rect")
                .attr('title', props.help || props.text)
                .attr("fill", props.swatchColor);

        items.select("text").text(props.text);

        items.exit().remove();
    }
});

creme.d3LegendColumn = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3LegendColumn(options),
        props: ['swatchSize', 'swatchColor', 'spacing', 'data', 'text']
    });
};

}(jQuery));
