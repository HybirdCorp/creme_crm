/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2015-2017  Hybird

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

creme.search = {};

creme.search.SearchBox = function (element, searchUrl, advancedSearchUrl) {
    this.$element = $(element);

    this.$input = this.$element.find('input');
    this.$input.bind('focus', this._onShow.bind(this));
    this.$input.bind('input', creme.utils.debounce(this._onInput.bind(this), 200));
    this.$input.bind('keydown', this._onKeyDown.bind(this));

    this.$resultsRoot = this.$element.find('.inline-search-results');

    this.$icon = this.$element.find('.search-box-icon');

    this.$allResultsGroup = this.$element.find('.all-search-results');
    this.$allResultsLink  = this.$allResultsGroup.find('a');

    this.glasspane = new creme.dialogs.GlassPane(/*{debug: true}*/);
    this.glasspane.on('click', this._onHide.bind(this));

    this.state = 'default';
    this.searchUrl = searchUrl;
    this.advancedSearchUrl = advancedSearchUrl;
}

creme.search.SearchBox.prototype= {
    _onShow: function(e) {
        this.glasspane.open($('.header-menu'));
        this.$resultsRoot.addClass('showing');
    },

    _onHide: function(e) {
        this.$input.blur();
        this.$resultsRoot.removeClass('showing');
        this.glasspane.close();
    },

    _onKeyDown: function(e) {
        if (e.keyCode == 27) { // Escape
            this._onHide();
        }

        if (this.state != 'loaded')
            return;

        if (e.keyCode != 38 && e.keyCode != 40 && e.keyCode != 13)
            return;

        e.preventDefault();

        if (e.keyCode == 38) { // Up
            var selected = (this.selected - 1) % this.linksCount;
            if (selected >= 0)
                this._setSelectedResult(selected);
        }
        else if (e.keyCode == 40) { // Down
            var selected = (this.selected + 1) % this.linksCount;
            if (selected >= 0)
                this._setSelectedResult(selected);
        }
        else if (e.keyCode == 13) { // Enter
            this._goToSelection();
        }
    },

    _onInput: function(e) {
        var query = this.$input.val().trim();
        var isEmpty = query == '';

        if (this.state == 'default') {
            if (isEmpty == false) {
                this._switchToLoading(query);
            }
        }
        else if (this.state == 'loading') {
            if (isEmpty) {
                this._switchToDefault();
            } else {
                this._switchToLoading(query);
            }
        }
        else if (this.state == 'loaded') {
            if (isEmpty) {
                this._switchToDefault();
            } else if (this.query != query) {
                this._switchToLoading(query);
            }
        }
    },

    _switchToLoading: function(query) {
        // TODO: possibly move this to onInput ? in any case, check the state transitions are correct even in this error case
        if (query.length < 3) return;

        this.$icon.removeClass('default').addClass('loading');

        this.$allResultsLink.text(gettext('Loading…'));

        this._resetSelection();
        this.$allResultsGroup.siblings().remove(); // TODO: let the old results visible ?

        this._asynchronousRequest(query, new Date().getTime());
        this.state = 'loading';
    },

    // TODO: there are probably ways to do a stronger code (timestamp etc...)
    _asynchronousRequest: function(query, timestamp) {
        this.timestamp = timestamp; // Record last request time to compare with the local timestamp parameter

        var searchUri = this.searchUrl + '?value=' + encodeURIComponent(query);
        $.getJSON(searchUri, function(data) {
            var results = [];

            var resultCount = 0;
            for (var idx in data.results)
                resultCount += data.results[idx].count;

            if (resultCount > 0) {
                if (resultCount > 1) {
                    var best = data.best;
                    var bestResult = ("<div class='search-results-group best-results-group'>" +
                                          "<span class='search-results-group-title'>%s</span>" +
                                          "<ul class='search-results'>" +
                                              "<li class='search-result'><a href='%s'>%s</a></li>" +
                                          "</ul>" +
                                      "</div>").format(gettext('Best result'),
                                                       best.url,
                                                       best.label
                                                      );

                    results.push(bestResult);
                }

                // CTs
                for (var idx in data.results) {
                    var ct = data.results[idx];

                    var ctResultsUrl = this.advancedSearchUrl + "?ct_id=" + ct.id + "&research=" + encodeURIComponent(query);
                    var ctResults = ct.results.map(function(ctResult) {
                       return "<li class='search-result'><a href='%s'>%s</a></li>".format(ctResult.url, ctResult.label);
                    });

                    var ctGroupTitle = ct.label;
                    var ctGroup = ("<div class='search-results-group'>" +
                                       "<span class='search-results-group-title'><a href='%s'>%s</a></span>" +
                                       "<ul class='search-results'>%s</ul>" +
                                   "</div>").format(ctResultsUrl,
                                                    ctGroupTitle,
                                                    ctResults.join('\n')
                                                   );

                    results.push(ctGroup);
                }
            }

            this._onResultsReceived(query, timestamp, results, resultCount);
        }.bind(this));
    },

    _switchToDefault: function() {
        this.$icon.removeClass('loading').addClass('default');

        this.$allResultsLink.text(gettext('Advanced search'));
        this.$allResultsLink.attr('href', this.advancedSearchUrl);

        this._resetSelection();
        this.$allResultsGroup.siblings().remove(); // TODO: let the old results visible ?

        this.state = 'default';
        this.timestamp = null; // Reset timestamp marker so that possible in-flight asynchronous responses are ignored when received
    },

    _switchToLoaded: function() {
        this.$icon.removeClass('loading').addClass('default');
        this.state = 'loaded';
    },

    _onResultsReceived: function(query, timestamp, results, resultCount) {
    //   console.log ('received results from query ' + query + ' sent at ' + timestamp + ' - last known request timestamp: ' + this.timestamp);

        // Filter results from older queries, and results from in-flight queries for unwanted requests
        if (this.timestamp == null || timestamp < this.timestamp)
            return;

        this.resultCount = resultCount;

        if (results) {
            this.$allResultsGroup.after(results);

            this.$results = this.$resultsRoot.find('.search-result');
            this.linksCount = this.$results.size();
        }

        if (this.resultCount > 0) {
            this.$allResultsLink.attr('href', this.advancedSearchUrl + '?research=' + encodeURIComponent(query));
            this.$allResultsLink.text(gettext('All results (%s)').format(this.resultCount));
            this._setSelectedResult(1);
        }
        else {
            this.$allResultsLink.attr('href', '');
            this.$allResultsLink.text(gettext('No result'));
        }

        this._switchToLoaded();
    },

    _resetSelection: function() {
        this.$resultsRoot.find('.search-result-selected').removeClass('search-result-selected');
    },

    _setSelectedResult: function(selected) {
        this._resetSelection();

        this.selected = selected;
        this.$selected = this.$results.eq(selected).addClass('search-result-selected');

        if (this.$selected.length > 0)
            this.$selected[0].scrollIntoView();
    },

    _goToSelection: function() {
        if (this.resultCount > 0) {
            var result = this.$selected.find('a');

            window.location.href = result.attr('href');
        }
    },
};