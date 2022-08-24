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

creme.D3BottomAxis = creme.D3Drawable.sub({
    defaultProps: {
        zIndex: 1,
        bounds: {top: 0, left: 0, width: 0, height: 0},
        label: function(d, i) { return d; },
        help: function(d, i) { return d; },
        scale: function(d, i) { return d; },
        minHeight: 20
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var axis = d3.select(node);

        axis.call(d3.axisBottom(props.scale).tickSizeOuter(0))
            .selectAll('.tick text')
                .call(creme.d3TextWrap().maxWidth(props.scale.bandwidth())
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
        var ticksHeight = Math.max(
            props.minHeight,
            d3.max(creme.d3Map(axis.selectAll('.tick'), function() {
                return this.getBBox().height;
            }))
        );

        title.attr('transform', creme.svgTransform().translate(props.bounds.width, ticksHeight + (titleHeight / 2) * 1.1));

        this.prop('preferredHeight', ticksHeight + titleHeight * 1.1);
    }
});

creme.d3BottomAxis = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3BottomAxis(options),
        props: ['label', 'help', 'zIndex', 'scale', 'minHeight', 'bounds', 'preferredHeight']
    });
};

}(jQuery));
