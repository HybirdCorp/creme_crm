/**
* Array prototype extensions.
* Extends array prototype with the following methods:
* contains, every, exfiltrate, filter, forEach, getRange, inArray, indexOf, insertAt, map, randomize, removeAt, some, unique
*
* This extensions doesn't depend on any other code or overwrite existing methods.
*
*
* Copyright (c) 2007 Harald Hanek (http://js-methods.googlecode.com)
*
* Dual licensed under the MIT (http://www.opensource.org/licenses/mit-license.php)
* and GPL (http://www.gnu.org/licenses/gpl.html) licenses.
*
* @author Harald Hanek
* @version 0.9
* @lastchangeddate 10. October 2007 15:46:06
* @revision 876
*/

(function($) {
    "use strict";

    /**
    * Extend the array prototype with the method under the given name if it doesn't currently exist.
    *
    * @private
    */
   /*
    function append(name, method) {
        if (!Array.prototype[name]) {
            Array.prototype[name] = method;
        }
    };
*/
    function appendStatic(name, method) {
        if (!Array[name]) {
            Array[name] = method;
        }
    };

    appendStatic('copy', function(iterable, start, end) {
        console.warn('Deprecated; Use Array.from(iterable).slice(start, end) instead');

        var res = [];
        start = Math.min(Math.max(0, start || 0), iterable.length);
        end = end !== undefined ? Math.min(Math.max(0, end), iterable.length) : iterable.length;

        for (var i = start; i < end; ++i) {
            res.push(iterable[i]);
        }

        return res;
    });
/*
    if ($ !== undefined) {
        return;
    }
*/
    /**
    * Returns a range of items in this collection
    *
    * @example [1, 2, 1, 4, 5, 4].getRange(2, 4);
    * @result [1, 4, 5]
    *
    * @name getRange
    * @param Number startIndex (optional) defaults to 0
    * @param Number endIndex (optional) default to the last item
    * @return Array
    */
    /* istanbul ignore next */
    /*
    append("getRange", function(start, end) {
        var items = this;
        if (items.length < 1) {
            return [];
        }

        start = start || 0;
        end = Math.min(end === undefined ? this.length - 1 : end, this.length - 1);
        var r = [], i;
        if (start <= end) {
            for (i = start; i <= end; i++) {
                r[r.length] = items[i];
            }
        } else {
            for (i = start; i >= end; i--) {
                r[r.length] = items[i];
            }
        }

        return r;
    });
    */

    /**
    * Checks if a given subject can be found in the array.
    *
    * @example [12, 5, 7, 5].inArray(7);
    * @result true;
    *
    * @example [12, 5, 7, 5].inArray(9);
    * @result false;
    *
    * @name inArray
    * @param Object subject Object to search for
    * @return Boolean
    */
    /* istanbul ignore next */
    /*
    append("inArray", function(subject) {
        for (var i = 0; i < this.length; i++) {
            if (subject === this[i]) {
                return true;
            }
        }
        return false;
    });
    */

    /**
    * Inserts an item at the specified index in the array.
    *
    * @example ['dog', 'cat', 'horse'].insertAt(2, 'mouse');
    * @result ['dog', 'cat', 'mouse', 'horse']
    *
    * @name insertAt
    * @param Number index Position where to insert the element into the array
    * @param Object element The element to insert
    * @return Array
    */
    /* istanbul ignore next */
    /*
    append("insertAt", function(index, element) {
        for (var k = this.length; k > index; k--) {
            this[k] = this[k - 1];
        }

        this[index] = element;
        return this;
    });
    */

    /**
    * Remove an item from a specified index in the array.
    *
    * @example ['dog', 'cat', 'mouse', 'horse'].deleteAt(2);
    * @result ['dog', 'cat', 'horse']
    *
    * @name removeAt
    * @param Number index The index within the array of the item to remove.
    * @return Array
    */
    /* istanbul ignore next */
    /*
    append("removeAt", function(index) {
        for (var k = index; k < this.length - 1; k++) {
            this[k] = this[k + 1];
        }

        this.length--;
        return this;
    });
    */

    /**
    * Tests whether some element in the array passes the test implemented by the provided function.
    *
    * Natively supported in Gecko since version 1.8.
    * http://developer.mozilla.org/en/docs/Core_JavaScript_1.5_Reference:Objects:Array:some
    *
    * @example [101, 199, 250, 200].some(function(element, index, array) {
    *   return element >= 100;
    * });
    * @result true;
    *
    * @example [101, 99, 250, 200].some(function(element, index, array) {
    *   return element >= 100;
    * });
    * @result false;
    *
    * @name some
    * @param Function fn The function to be called for each element.
    * @param Object scope (optional) The scope of the function (defaults to this).
    * @return Boolean
    */
    /* istanbul ignore next */
    /*
    append("some", function(fn, scope) {
        for (var i = 0; i < this.length; i++) {
            if (fn.call(scope || window, this[i], i, this)) {
                return true;
            }
        }

        return false;
    });
    */

    /**
    * Returns a new array that contains all unique elements of this array.
    *
    * @example [1, 2, 1, 4, 5, 4].unique();
    * @result [1, 2, 4, 5]
    *
    * @name unique
    * @return Array
    */
    /* istanbul ignore next */
    /*
    append("unique", function() {
        return this.filter(function(element, index, array) {
            return array.indexOf(element) >= index;
        });
    });
    */
}(jQuery));
