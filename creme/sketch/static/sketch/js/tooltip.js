/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2023-2025  Hybird

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

/* globals DOMPoint */

(function() {
"use strict";

function bboxAnchorPoint(target, node, direction) {
    /*
    The MIT License (MIT)
    Copyright (c) 2013 Justin Palmer
    (see https://github.com/caged/d3-tip/blob/master/index.js#L273)

    Given a shape on the screen, will return an SVGPoint for the directions
    n(north), s(south), e(east), w(west), ne(northeast), se(southeast),
    nw(northwest), sw(southwest).

          n
     nw +-+-+ ne
        |   |
      w + c + e
        |   |
     sw +-+-+ se
          s
    */
    var point;
    var bbox = target.getBBox();

    switch (direction) {
        case 'n':
            point = new DOMPoint(bbox.x + bbox.height / 2, bbox.y);
            point.x -= node.offsetWidth / 2;
            point.y -= node.offsetHeight;
            break;
        case 's':
            point = new DOMPoint(bbox.x + bbox.height / 2, bbox.y + bbox.height);
            point.x -= node.offsetWidth / 2;
            break;
        case 'e':
            point = new DOMPoint(bbox.x + bbox.width, bbox.y + bbox.height / 2);
            point.y -= node.offsetHeight / 2;
            break;
        case 'w':
            point = new DOMPoint(bbox.x, bbox.y + bbox.height / 2);
            point.x -= node.offsetWidth;
            point.y -= node.offsetHeight / 2;
            break;
        case 'nw':
            point = new DOMPoint(bbox.x, bbox.y);
            point.x -= node.offsetWidth;
            point.y -= node.offsetHeight;
            break;
        case 'ne':
            point = new DOMPoint(bbox.x + bbox.width, bbox.y);
            point.y -= node.offsetHeight;
            break;
        case 'se':
            point = new DOMPoint(bbox.x + bbox.width, bbox.y + bbox.height);
            break;
        case 'sw':
            point = new DOMPoint(bbox.x, bbox.y + bbox.height);
            point.x -= node.offsetWidth;
            break;
        default:
            point = new DOMPoint(bbox.x + bbox.width / 2, bbox.y + bbox.height / 2);
            point.x -= node.offsetWidth / 2;
            point.y -= node.offsetHeight / 2;
    }

    return point;
}


function TooltipEvent(type, options) {
    Object.defineProperties(this, {
        type: {value: type, enumerable: true, configurable: true},
        target: {value: options.target, enumerable: true, configurable: true},
        tooltip: {value: options.tooltip, enumerable: true, configurable: true},
        container: {value: options.container, enumerable: true, configurable: true},
        _: {value: options.dispatch}
    });
}

creme.d3Tooltip = function(root) {
    var container = null;
    var listeners = d3.dispatch("show", "hide");
    var props = {
         root: root || document.body,
         transition: true
    };

    function prop(name, value) {
        if (value === undefined) {
            return props[name];
        } else {
            props[name] = value;
            return tooltip;
        }
    }

    function getContainer(root) {
        if (container === null) {
            container = d3.select(document.createElement('div'))
                              .attr('class', 'd3-sketch-tooltip')
                              .style('top', 0)
                              .style('left', 0);

            root.node().appendChild(container.node());
        }

        return container;
    }

    function emit(node, type, container) {
        var d = d3.select(node).datum();
        var event = new TooltipEvent(type, {
            target: node,
            tooltip: tooltip,
            container: container,
            dispatch: listeners
        });

        listeners.call(type, node, event, d);
    }

    function tooltip(node) {};

    tooltip.show = function() {
        var args = Array.from(arguments);
        var root = d3.select(Object.isFunc(props.root) ? props.root.apply(this, args) : props.root);
        var content = Object.isFunc(props.html) ? props.html.apply(this, args) : props.html;
        var direction = (Object.isFunc(props.direction) ? props.direction.apply(this, args) : props.direction) || 's';
        var offset = (Object.isFunc(props.offset) ? props.offset.apply(this, args) : props.offset) || [0, 0];
        var scroll = {
            top: document.documentElement.scrollTop || props.root.scrollTop,
            left: document.documentElement.scrollLeft || props.root.scrollLeft
        };

        offset = Array.isArray(offset) ? new DOMPoint(offset[0], offset[1]) : offset;

        var container = getContainer(root);

        emit(this, 'show', container);

        // fill the container BEFORE evaluating position
        container.html(content);

        var coords = bboxAnchorPoint(this, container.node(), direction).matrixTransform(creme.svgScreenCTMatrix(this));

        container
            .style('pointer-events', 'all')
            .style('top', coords.y + offset.y + scroll.top + 'px')
            .style('left', coords.x + offset.x + scroll.left + 'px')
            .attr('class', 'd3-sketch-tooltip tip-' + direction);

        container = props.transition ? container.transition() : container;
        container.style('opacity', 1);

        return tooltip;
    };

    tooltip.hide = function() {
        var args = Array.from(arguments);
        var root = d3.select(Object.isFunc(props.root) ? props.root.apply(this, args) : props.root);
        var container = getContainer(root);

        emit(this, 'hide', container);

        container.style('pointer-events', 'none')
                 .attr('class', 'd3-sketch-tooltip');

        container = props.transition ? container.transition() : container;
        container.style('opacity', 0);
    };

    tooltip.offset = function(offset) {
        return prop('offset', offset);
    };

    tooltip.direction = function(direction) {
        return prop('direction', direction);
    };

    tooltip.root = function(root) {
        return prop('root', root);
    };

    tooltip.html = function(html) {
        return prop('html', html);
    };

    tooltip.transition = function(transition) {
        return prop('transition', transition);
    };

    tooltip.on = function() {
        var value = listeners.on.apply(listeners, arguments);
        return value === listeners ? tooltip : value;
    };

    return tooltip;
};

}());
