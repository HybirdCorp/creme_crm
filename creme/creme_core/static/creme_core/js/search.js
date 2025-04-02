/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2015-2025  Hybird

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

/*
 * Requires : jQuery
 *            creme.utils.js
 */

(function($) {
"use strict";

creme.search = creme.search || {};

var KeyCodes = {
    UP: 38,
    DOWN: 40,
    ENTER: 13,
    ESCAPE: 27
};

creme.search.SearchBox = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            minSearchLength: 3,
            debounceDelay: 200,
            focusDebounceDelay: 100
        }, options || {});

        this._glasspane = new creme.dialog.GlassPane(/* {debug: true} */);
        this._glasspane.pane().on('click', this._onHide.bind(this));

        if (Object.isEmpty(options.searchUrl)) {
            throw new Error('searchUrl is required');
        }

        if (Object.isEmpty(options.advancedSearchUrl)) {
            throw new Error('advancedSearchUrl is required');
        }

        this._state = 'default';
        this._timestamp = null;

        this.debounceDelay = options.debounceDelay;
        this.focusDebounceDelay = options.focusDebounceDelay;
        this.minSearchLength = options.minSearchLength;
        this.searchUrl = options.searchUrl;
        this.advancedSearchUrl = options.advancedSearchUrl;
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    isLoading: function() {
        return this._state === 'loading';
    },

    bind: function(element) {
        if (this.isBound()) {
            throw Error('SearchBox is already bound');
        }

        this._element = element;

        var _onInput = this._onInput.bind(this);
        var _onShow = this._onShow.bind(this);

        this._input = element.find('input');
        this._input.on('focus', this.focusDebounceDelay ? _.debounce(_onShow, this.focusDebounceDelay, false) : _onShow)
                   .on('input paste', this.debounceDelay ? _.debounce(_onInput, this.debounceDelay, false) : _onInput)
                   .on('keydown', this._onKeyDown.bind(this));

        this._resultsRoot = element.find('.inline-search-results');

        this._icon = element.find('.search-box-icon');

        this._allResultsGroup = element.find('.all-search-results');
        this._allResultsLink  = this._allResultsGroup.find('a');

        return this;
    },

    isOpened: function() {
        return this._glasspane.isOpened();
    },

    _onShow: function(e) {
        if (this.isOpened()) {
            return;
        }

        this._glasspane.open($('.header-menu'));
        this._resultsRoot.addClass('showing');
    },

    _onHide: function(e) {
        this._cancelSearch();

        this._input.trigger('blur');
        this._resultsRoot.removeClass('showing');
        this._glasspane.close();
    },

    _onKeyDown: function(e) {
        if (this.isLoading()) {
            return;
        }

        switch (e.keyCode) {
            case KeyCodes.ESCAPE:
                this._onHide();
                break;
            case KeyCodes.ENTER:
                this._goToSelection();
                break;
            case KeyCodes.UP:
                this._setSelectedResult((this.selected - 1) % this.linksCount);
                break;
            case KeyCodes.DOWN:
                this._setSelectedResult((this.selected + 1) % this.linksCount);
                break;
            default:
                return;
        }

        e.preventDefault();
    },

    _onInput: function(e) {
        var query = (this._input.val() || '').trim();
        var isValidQuery = query.length >= this.minSearchLength;

        // console.log('_onInput', query, isValidQuery, new Date().getTime() - this._debugTimestamp);

        if (isValidQuery === false) {
            this._cancelSearch();
        } else {
            this._startSearch(query);
        }
    },

    _updateResultState: function(results) {
        results = results || {};

        this._allResultsGroup.siblings().remove();

        if (results.count > 0) {
            this._allResultsGroup.after(results.items);

            var url = _.toRelativeURL(this.advancedSearchUrl).searchData({search: results.query});

            this._allResultsLink.attr('href', url);
            this._allResultsLink.text(gettext('All results (%s)').format(results.count));

            this._setSelectedResult(1);
        } else {
            this._allResultsLink.attr('href', '');
            this._allResultsLink.text(gettext('No result'));
        }

        this.linksCount = this._resultsRoot.find('.search-result').length;
        this.resultCount = results.count;
    },

    _updateState: function(isLoading, results) {
        this._icon.toggleClass('default', !isLoading)
                  .toggleClass('loading', isLoading);

        this._state = isLoading ? 'loading' : 'default';

        if (isLoading) {
            this._allResultsLink.text(gettext('Loading…'));

            this._resetSelection();
        } else if (Object.isNone(results)) {
            this._allResultsLink.text(gettext('Advanced search'));
            this._allResultsLink.attr('href', this.advancedSearchUrl);

            this._resetSelection();
        } else {
            this._updateResultState(results);
        }
    },

    _cancelSearch: function() {
        this._timestamp = null;
        this._updateState(false);
    },

    _startSearch: function(query) {
        var self = this;
        var timestamp = new Date().getTime();
        var queryOptions = {
            backend: {
                sync: false
            }
        };

        // console.log('_startSearch', timestamp - this._debugTimestamp);

        creme.ajax.query(this.searchUrl, queryOptions, {value: query})
                  .onStart(function() {
                       self._updateState(true);
                       self._timestamp = timestamp;
                   })
                  .onFail(function() {
                      self._updateState(false);
                   })
                  .onDone(function(event, responseData) {
                      try {
                          var data = self._renderResults(JSON.parse(responseData), query);

                          if (self._timestamp !== null && timestamp >= self._timestamp) {
                              self._updateState(false, data);
                          }
                      } catch (e) {
                          console.error(e);
                          self._updateState(false);
                      }
                   })
                  .get();
    },

    _renderResults: function(data, query) {
        var results = [];
        var idx = -1;

        var resultCount = 0;

        for (idx in data.results) {
            resultCount += data.results[idx].count;
        }

        if (resultCount > 0) {
            if (resultCount > 1) {
                var best = data.best;
                var bestResult = (
                    "<div class='search-results-group best-results-group'>" +
                        "<span class='search-results-group-title'>${title}</span>" +
                        "<ul class='search-results'>" +
                            "<li class='search-result'><a href='${url}'${attrs}>${label}</a></li>" +
                        "</ul>" +
                    "</div>"
                ).template({
                    title: gettext('Best result'),
                    url: best.url,
                    attrs: best.deleted ? " class='is_deleted'" : '',
                    label: $('<div>').text(best.label).html()  // NB: HTML escaping
                });

                results.push(bestResult);
            }

            var searchUrl = _.toRelativeURL(this.advancedSearchUrl);

            // CTs
            for (idx in data.results) {
                var ct = data.results[idx];

                var ctResultsUrl = searchUrl.searchData({ct_id: ct.id, search: query}).toString();
                var ctResults = ct.results.map(function(ctResult) {
                    return "<li class='search-result'><a href='${url}'${attrs}>${label}</a></li>".template({
                        url: ctResult.url,
                        attrs: ctResult.deleted ? " class='is_deleted'" : '',
                        label: $('<div>').text(ctResult.label).html()
                    });
                });

                var ctGroupTitle = ct.label;
                var ctGroup = (
                    "<div class='search-results-group'>" +
                        "<span class='search-results-group-title'><a href='${url}'>${title}</a></span>" +
                        "<ul class='search-results'>${results}</ul>" +
                    "</div>"
                ).template({
                    url: ctResultsUrl,
                    title: ctGroupTitle,
                    results: ctResults.join('\n')
                });

                results.push(ctGroup);
            }
        }

        return {
            query: query,
            count: resultCount,
            items: results
        };
    },

    _resetSelection: function() {
        this._resultsRoot.find('.search-result-selected').removeClass('search-result-selected');
    },

    _setSelectedResult: function(selected) {
        this._resetSelection();

        this.selected = selected;
        this._selected = this._resultsRoot.find('.search-result')
                                          .eq(selected)
                                          .addClass('search-result-selected');

        if (this._selected.length > 0) { this._selected[0].scrollIntoView(); }
    },

    _goToSelection: function() {
        if (this.resultCount > 0) {
            var result = this._selected.find('a');

            creme.utils.goTo(result.attr('href'));
        }
    }
});
}(jQuery));
