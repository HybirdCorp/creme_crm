/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

creme.widget.PluginLauncher = creme.widget.declare('ui-creme-jqueryplugin', {
    options: {
        plugin: '',
        plugin_options: {}
    },

    _create: function(element, options, cb, sync, attributes) {
        var plugin_name = options.plugin || '';
        var plugin_options = this._pluginOptions = (
            _.isString(options.plugin_options) ? _.cleanJSON(options.plugin_options) || {} : options.plugin_options
        );
        var plugin = this._plugin = plugin_name !== '' ? element[plugin_name] : undefined;

        // console.log('plugin-name:', plugin_name, 'options:', options, 'plugin-options:', plugin_options, 'is_valid:', (typeof plugin === 'function'));

        if (Object.isFunc(plugin)) {
            plugin.apply(element, [plugin_options]);
        }

        element.addClass('widget-ready');
    },

    _destroy: function(element) {
        this._plugin.apply(element, 'destroy');
    },

    plugin: function(element) {
        return this._plugin;
    }
});

}(jQuery));
