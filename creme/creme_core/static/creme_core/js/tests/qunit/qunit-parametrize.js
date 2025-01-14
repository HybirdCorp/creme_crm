/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2025  Hybird

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


(function() {
"use strict";

function __scenarioLabel(scenario, index) {
    if (typeof scenario === 'number') {
        return String(scenario);
    } else if (Object.isString(scenario)) {
        return scenario;
    } else {
        return String(index + 1);
    }
};

function __iterScenarios(scenarios, callable) {
    if (Array.isArray(scenarios)) {
        scenarios.forEach(function(scenario, index) {
            callable(scenario, __scenarioLabel(scenario, index));
        });
    } else {
        Object.entries(scenarios).forEach(function(entry) {
            callable(entry[1], entry[0]);
        });
    }
};

window.QUnit.parameterize = function(name, scenarios, callable) {
    if (arguments.length < 3) {
        throw new Error('QUnit.parametrize requires at least 3 arguments');
    }

    if (arguments.length > 3) {
        var args = Array.from(arguments);
        callable = args[arguments.length - 1];
        scenarios = args[1];
        var subScenarios = args.slice(2, arguments.length - 1);

        return __iterScenarios(scenarios, function(scenario, label) {
            QUnit.parameterize.apply(null, [
                    '${name}-${label}'.template({name: name, label: label})
                ].concat(
                    subScenarios
                ).concat([
                    function() {
                        callable.apply(this, (Array.isArray(scenario) ? scenario : [scenario]).concat(Array.from(arguments)));
                    }
                ])
            );
        });
    }

    __iterScenarios(scenarios || {}, function(scenario, label) {
        if (callable.skipped) {
            QUnit.skip('${name}-${label}'.template({name: name, label: label}));
        } else {
            QUnit.test('${name}-${label}'.template({name: name, label: label}), function() {
                callable.apply(this, (Array.isArray(scenario) ? scenario : [scenario]).concat(Array.from(arguments)));
            });
        }
    });
};

window.QUnit.parameterizeIf = function(condition, name, scenarios, callable) {
    callable.skipped = Object.isFunc(condition) ? condition() : Boolean(condition);
    return QUnit.parameterize(name, scenarios, callable);
};

/* An alias for me */
window.QUnit.parametrize = window.QUnit.parameterize;
window.QUnit.parametrizeIf = window.QUnit.parameterizeIf;

}());
