/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2017-2026  Hybird

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

/* globals BrowserVersion FunctionFaker DateFaker */

(function($) {
    "use strict";

    window.QUnitMixin = function() {
        var self = this;
        var reserved = ['setup', 'teardown', 'before', 'after', 'beforeEach', 'afterEach'];
        var mixins = this.__mixins = [QUnitBaseMixin].concat(Array.from(arguments));

        mixins.forEach(function(mixin) {
            for (var key in mixin) {
                if (reserved.indexOf(key) === -1) {
                    self[key] = mixin[key];
                }
            }
        });

        /* HACK : Since QUnit 1.20+ the module expects a DICT of hooks, not any object with right methods. */
        /* eslint-disable no-self-assign */
        this['before'] = this.before;
        this['beforeEach'] = this.beforeEach;

        this['after'] = this.before;
        this['afterEach'] = this.afterEach;
    };

    QUnitMixin.prototype = {
        beforeEach: function(env) {
            var self = this;

            this.__mixins.forEach(function(mixin) {
                if (Object.isFunc(mixin.beforeEach)) {
                    mixin.beforeEach.call(self, env);
                }
            });
        },

        afterEach: function(env) {
            var self = this;

            Array.from(this.__mixins).reverse().forEach(function(mixin) {
                if (Object.isFunc(mixin.afterEach)) {
                    mixin.afterEach.call(self, env);
                }
            });
        }
    };

    window.QUnit.skipIf = function(condition, name, callable) {
        var skipIt = Object.isFunc(condition) ? condition() : Boolean(condition);

        if (skipIt) {
            QUnit.skip(name);
        } else {
            QUnit.test(name, callable);
        }
    };

    window.QUnit.browsers = BrowserVersion;

    $.migrateTrace = true;

    var listChildrenTags = function() {
        return $('body').children().map(function() {
            var attributes = [];

            for (var i = 0; i < this.attributes.length; ++i) {
                attributes.push('${name}="${value}"'.template({
                    name: this.attributes[i].name,
                    value: this.attributes[i].value.replace('"', '\\"')
                }));
            }

            return '<${tagName} ${attrs}>'.template({
                tagName: this.tagName.toLowerCase(),
                attrs: attributes.join(' ')
            });
        }).get();
    };

    window.QUnitBaseMixin = {
        beforeEach: function(env) {
            // console.log(env.test.testName);
            Object.defineProperty(this, 'assert', {
                value: env.test.assert,
                configurable: false,
                writable: false
            });

            this.__qunitDOMCleanupCheckError = 'ignore';
            this.__qunitBodyElementTags = listChildrenTags($('body'));
            this.qunitFixture().attr('style', 'position: absolute;top: -10000px;left: -10000px;width: 1000px;height: 1000px;');
        },

        afterEach: function(env) {
            var tags =  listChildrenTags($('body'));
            var checkStatus = this.qunitDOMCleanupCheck();

            if (checkStatus === 'ignore') {
                return;
            }

            if (this.__qunitBodyElementTags.length !== tags.length) {
                var message = 'QUnit incomplete DOM cleanup (expected ${expected}, got ${count})'.template({
                    expected: this.__qunitBodyElementTags.length,
                    count: tags.length
                });

                if (this.qunitDOMCleanupCheck() === 'error') {
                    this.assert.deepEqual(tags.sort(), this.__qunitBodyElementTags.sort(), message);
                } else {
                    console.warn(message);
                }
            }

            this.qunitDOMCleanup();
        },

        qunitUserAgent: function() {
            return $('#qunit-userAgent').text() || '';
        },

        qunitDOMCleanup: function() {
            $('[id^=qunit-fixture-]').empty();
            $('#qunit-fixture').empty();
        },

        qunitDOMCleanupCheck: function(status) {
            if (status === undefined) {
                return this.__qunitSkipDOMCleanupCheck;
            }

            this.__qunitSkipDOMCleanupCheck = status;
            return this;
        },

        qunitFixture: function(name) {
            var fixture = $('#qunit-fixture');

            if (fixture.length === 0) {
                throw Error('Missing qunit-fixture element !');
            };

            if (name === undefined || name === null) {
                return fixture;
            }

            name = String(name);
            var subfixture = fixture.find('#qunit-fixture-' + name);

            if (subfixture.length === 0) {
                subfixture = $('<div id="qunit-fixture-' + name + '"></div>').appendTo(fixture);
            }

            return subfixture;
        },

        assertRaises: function(block, expected, message) {
            expected = expected || Error;
            var assert = this.assert;

            assert.raises(
                block,
                function(error) {
                    assert.ok(error instanceof expected, 'error is ' + expected);

                    if (message !== undefined) {
                        assert.equal(message, '' + error, 'expected message');
                    }

                    block.__raised = error;
                    return true;
                }
            );

            return block.__raised;
        },

        assertNoXSS: function(block) {
            // Theses scripts are inspired by those found here:
            // https://owasp.org/www-community/xss-filter-evasion-cheatsheet
            var scripts = [
                '<script>QUnit.pushFailure("XSS < script>...< /script>");</script>',
                '<img src="javascript:QUnit.pushFailure(\'XSS < img src=...>\')" />',
                '<img src=/ onerror="QUnit.pushFailure(\'XSS < img onerror=...>\')"></img>',
                '\\<a data-test="qunitXSS" onmouseover="QUnit.pushFailure(\'XSS < a mouseover=...>\')"\\>xxs link\\</a\\>'
            ];

            scripts.forEach(function(script) {
                var success = false;

                try {
                    block.bind(this)(script);
                    success = true;
                } finally {
                    this.assert.ok(success, 'XSS test as failed. See logs for stacktrace.');
                }

                // Trigger events for some XSS issues
                $('[data-test="qunitXSS"]').trigger('mouseover').trigger('click');
            }.bind(this));
        },

        equalHtml: function(expected, element, message) {
            this.assert.equal($('<div>').append(expected).html(), $(element).html(), message);
        },

        equalOuterHtml: function(expected, element, message) {
            this.assert.equal($('<div>').append(expected).html(), $('<div>').append($(element).clone()).html(), message);
        },

        fakeMethod: function(options) {
            var faker = new FunctionFaker(options);
            faker.wrap();
            return faker;
        },

        withFakeMethod: function(options, block) {
            return new FunctionFaker(options).with(block.bind(this));
        },

        withFrozenTime: function(date, block) {
            return new DateFaker(date).with(block.bind(this));
        },

        awaits: function(target, func) {
            if (isNaN(target)) {
                return this.awaitsPromise(target, func);
            } else {
                var done = this.assert.async();

                setTimeout(function() {
                    try {
                        func.apply(this, arguments);
                    } finally {
                        done();
                    }
                }, target);
            }
        },

        awaitsPromise: function(promise, func) {
            var done = this.assert.async();

            promise.then(function() {
                try {
                    func.apply(this, arguments);
                } catch (e) {
                    console.error(e);
                    ok(false, 'Unexpected promise callback error');
                }
            }.bind(this)).catch(function(e) {
                console.error(e);
            }).finally(function() {
                done();
            });
        }
    };

    window.QUnitConsoleMixin = {
        beforeEach: function() {
            this.resetMockConsoleWarnCalls();

            var self = this;
            var __consoleWarn = this.__consoleWarn = console.warn;
            var __consoleError = this.__consoleError = console.error;

            console.warn = function() {
                var args = Array.from(arguments);
                self.__consoleWarnCalls.push(args);
                return __consoleWarn.apply(this, args);
            };

            console.error = function() {
                var args = Array.from(arguments);
                self.__consoleErrorCalls.push(args);
                return __consoleError.apply(this, args);
            };
        },

        afterEach: function() {
            console.warn = this.__consoleWarn;
            console.error = this.__consoleError;
        },

        mockConsoleWarnCalls: function() {
            return this.__consoleWarnCalls;
        },

        resetMockConsoleWarnCalls: function() {
            this.__consoleWarnCalls = [];
        },

        mockConsoleErrorCalls: function() {
            return this.__consoleWarnCalls;
        },

        resetMockConsoleErrorCalls: function() {
            this.__consoleWarnCalls = [];
        }
    };

    window.QUnitMouseMixin = {
        fakeMouseEvent: function(name, options) {
            var position = _.pop(options, 'position') || {};
            var offset = _.pop(options, 'offset') || {};
            var button = _.pop(options, 'button') || 1;     // Mouse button 1 (left), 2 (middle), 3 (right)
            var target = _.pop(options, 'target');

            options = Object.assign({
                bubbles: true,
                cancelable: (name !== "mousemove"),
                view: window,
                detail: 0,
                screenX: 0,
                screenY: 0,
                clientX: position.x,
                clientY: position.y,
                ctrlKey: false,
                altKey: false,
                shiftKey: false,
                metaKey: false,
                button: button,
                which: button,
                // relatedTarget: document.body.parentNode,
                pageX: position.x || 0,     // The mouse position relative to the left edge of the document.
                pageY: position.y || 0,      // The mouse position relative to the top edge of the document.
                offsetX: offset.x || 0,
                offsetY: offset.y || 0,
                // originalEvent: {},
                preventDefault: _.noop,
                target: Object.isNone(target) ? $(target).get(0) : undefined
            }, options || {});

            return $.Event(name, options);
        },

        simulateDragNDrop: function(options) {
            options = Object.assign({
                dragStartDelay: 0,
                revertDelay: 0
            }, options || {});

            var source = options.source || [];
            var target = options.target || [];

            if (source.length !== 1 || target.length !== 1) {
                this.assert.ok(false, 'Must have only ONE drag source (got ${source}) and ONE target (got ${target})'.template({
                    source: source.length,
                    target: target.length
                }));

                return;
            }

            function center(elem, ratio) {
                var offset = elem.offset();
                var document = $(elem.get(0).ownerDocument);

                return {
                    x: Math.floor(offset.left + elem.outerWidth() / 2 - document.scrollLeft()),
                    y: Math.floor(offset.top + elem.outerHeight() / 2 - document.scrollTop())
                };
            }

            // Get center position from source and target element as initial mouse position.
            var dragPosition = center(source);
            var dropPosition = center(target);

            // The drop position must be in the bottom-half or right-half part of the target.
            // And upper-half or left-half if we move backward.
            var down = dropPosition.x > dragPosition.x;
            var right = dropPosition.y > dragPosition.y;

            dropPosition.x += target.outerWidth() * 0.25 * (down ? 1 : -1);
            dropPosition.y += target.outerHeight() * 0.25 * (right ? 1 : -1);

            return new Promise(function(resolve, reject) {
                // First : LEFT mouse button down !
                source.trigger(
                    this.fakeMouseEvent('mousedown', {
                        position: dragPosition,
                        which: 1
                    })
                );

                // Second : Move to target drop zone
                setTimeout(function() {
                    source.trigger(
                        this.fakeMouseEvent('mousemove', {
                            position: dropPosition,
                            which: 1
                        })
                    );

                    // Third : Release mouse button on the drop zone
                    source.trigger(
                        this.fakeMouseEvent('mouseup', {
                            position: dropPosition,
                            which: 1
                        })
                    );

                    setTimeout(function() {
                        resolve.apply(this);
                    }.bind(this), options.revertDelay);
                }.bind(this), options.dragStartDelay);
            }.bind(this));
        }
    };
}(jQuery));
