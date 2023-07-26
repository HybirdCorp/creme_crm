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

creme.D3BottomAxis = creme.D3Drawable.sub({
    defaultProps: {
        label: function(d, i) { return d; },
        help: function(d, i) { return d; },
        scale: function(d, i) { return d; },
        minHeight: 20,
        tickWrapWidth: 30,
        tickFormat: null,
        ticks: 10
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var axis = d3.select(node);

        var ticks = axis.select('.axis-ticks');

        if (ticks.size() === 0) {
            ticks = axis.append('g')
                            .attr('class', 'axis-ticks');
        }

        ticks.call(d3.axisBottom(props.scale)
                          .tickFormat(props.tickFormat)
                          .tickSizeOuter(0)
                          .ticks(props.ticks))
             .selectAll('.tick text')
                 .call(creme.d3TextWrap().maxWidth(props.tickWrapWidth)
                                         .breakAll(true)
                                         .lineHeight('1.1em'));

        var title = axis.select('.axis-title');

        if (title.size() === 0) {
            title = axis.append('text')
                            .attr('class', 'axis-title')
                            .attr('text-anchor', 'end')
                            .attr('fill', 'currentColor');

            title.append('tspan')
                     .attr('class', 'axis-title-label');
            title.append('tspan')
                     .attr('class', 'axis-title-arrow')
                     .attr('dx', '0.5em')
                     .text('→');
        }

        title.select('.axis-title-label').text(props.label);

        var titleHeight = title.node().getBBox().height;
        var ticksBBox = ticks.node().getBBox();

        title.attr('transform', creme.svgTransform().translate(
             ticksBBox.width,
             Math.max(props.minHeight, ticksBBox.height) + (titleHeight / 2) * 1.1)
        );
    }
});

creme.d3BottomAxis = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3BottomAxis(options),
        props: ['label', 'help', 'scale', 'minHeight', 'tickFormat', 'tickWrapWidth', 'ticks', 'isNumeric']
    });
};

creme.D3LeftAxis = creme.D3Drawable.sub({
    defaultProps: {
        label: function(d, i) { return d; },
        help: function(d, i) { return d; },
        scale: function(d, i) { return d; },
        minWidth: 20,
        fill: 'rgba(0,0,0,0)',
        tickFormat: d3.format('~s'),
        ticks: 10
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var axis = d3.select(node);

        var ticks = axis.select('.axis-ticks');

        if (ticks.size() === 0) {
            axis.append('rect').attr('class', 'axis-bg');
            ticks = axis.append('g').attr('class', 'axis-ticks');
        }

        ticks.call(d3.axisLeft(props.scale)
                        .tickFormat(props.tickFormat)
                        .tickSizeOuter(0)
                        .ticks(props.ticks));

        var title = axis.select('.axis-title');

        if (title.size() === 0) {
            title = axis.append('text')
                            .attr('class', 'axis-title')
                            .attr('text-anchor', 'start')
                            .attr('fill', 'currentColor')
                            .attr('dy', '-1em');

            title.append('tspan')
                     .attr('class', 'axis-title-arrow')
                     .text('↑');

            title.append('tspan')
                     .attr('class', 'axis-title-label')
                     .attr('dy', '0.1em')
                     .attr('dx', '0.5em');
        }

        title.select('.axis-title-label').text(props.label);
        title.attr('transform', creme.svgTransform().translate(-ticks.node().getBBox().width, 0));

        var axisBBox = axis.node().getBBox();

        axis.select('.axis-bg')
                .attr('width', axisBBox.width)
                .attr('height', axisBBox.height)
                .attr('fill', props.fill)
                .attr('transform', creme.svgTransform().translate(-axisBBox.width, 0));
    }
});

creme.d3LeftAxis = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3LeftAxis(options),
        props: ['label', 'help', 'scale', 'tickFormat', 'fill', 'ticks']
    });
};

}(jQuery));
