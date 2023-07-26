/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2023  Hybird

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

creme.D3Scroll = creme.D3Drawable.sub({
    defaultProps: {
        target: null,
        bounds: {top: 0, left: 0, width: 0, height: 0},
        innerSize: {width: 0, height: 0},
        wheelScale: 0.1,
        disabled: false,
        wheelScrollDelta: function(e, props) {
            return {x: -e.deltaY * props.wheelScale, y: 0};
        }
    },

    setup: function(node, datum, i) {
        var self = this;
        var zoom = this.zoom = d3.zoom();
        var props = this.props();
        var container = d3.select(node);
        var target = (Object.isString(props.target) ? container.select(props.target) : props.target) || container;

        zoom.on("zoom.wheel", null)
            .on("zoom", function(e) {
                if (!self.prop('disabled')) {
                    target.attr("transform", creme.svgTransform().translate(e.transform.x, e.transform.y));
                }
            });

        target.on('wheel', function(e) {
            var wheelScrollDelta = self.prop('wheelScrollDelta');

            if (!self.prop('disabled') && wheelScrollDelta) {
                e.preventDefault();
                e.stopPropagation();
                var delta = wheelScrollDelta(e, props);
                container.call(zoom.translateBy, delta.x, delta.y);
            }
        });

        container.call(zoom);
    },

    draw: function(node, datum, i) {
        var props = this.props();
        var container = d3.select(node);
        var bounds = props.bounds;
        var zoom = this.zoom;
        var target = (Object.isString(props.target) ? container.select(props.target) : props.target) || container;

        if (!this.zoom) {
            this.setup(node, datum, i);
            zoom = this.zoom;
        }

        // HACK : Fix SVGLength.value property issue in tests
        // (see https://github.com/Webiks/force-horse/issues/19#issuecomment-826728521)
        zoom.extent([[0, 0], [bounds.width + bounds.left, bounds.height + bounds.top]])
            .scaleExtent([1, 1])  // no scale
            .translateExtent([[0, 0], [props.innerSize.width + bounds.left, props.innerSize.height + bounds.top]]);

        container.call(zoom.transform, d3.zoomIdentity);
        target.attr("transform", creme.svgTransform().translate(0, 0));
    }
});

creme.d3Scroll = function(options) {
    return creme.d3Drawable({
        instance: new creme.D3Scroll(options),
        props: ['target', 'bounds', 'innerSize', 'wheelScale', 'wheelScrollDelta', 'disabled'],
        methods: ['setup']
    });
};

}(jQuery));
