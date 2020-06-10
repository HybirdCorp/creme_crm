(function() {
    var fs = require('fs');

    buildKarmaGlobalJs = function(filename, globals, target) {
        globals = globals || {};
        target = target || 'window';

        var content = '(function() { ' + Object.keys(globals).map(function(key) {
            var value = globals[key];

            if (typeof value === 'string') {
                value = '"' + value + '"';
            } else if (typeof value === 'object') {
                value = JSON.stringify(value);
            }

            return target + '["' + key + '"] = ' + value;
        }).join('\n') + '}());';

        fs.writeFileSync('.karma.globals.js', content, 'utf8');
    }

    isDirectory = function(path) {
        try {
            return fs.lstatSync(path).isDirectory();
        } catch(e) {
            return false;
        }
    }

    buildKarmaTestFilesFromPath = function(paths) {
        return paths.map(function(path) {
            if (isDirectory(path)) {
                if (path[path.length - 1] !== '/') {
                    path = path + '/'; 
                }

                if (path.indexOf('/js/tests/') !== -1) {
                    return path + '/**/!(qunit)*.js';
                } else {
                    return path + '/**/js/tests/**/!(qunit)*.js';
                }
            } else {
                return path;
            }
        });
    }
}());

module.exports = function(config) {
    var language = config.djangoLang || 'en';
    var debug_port = config.browserDebugPort || '9333';

    var commonfiles = [
        'creme/media/static/l10n--' + language + '-*.js',
        'creme/media/static/lib*.js',
        'creme/media/static/main*.js'
    ];

    var qunitmixins = ['creme/**/js/tests/**/qunit*mixin.js']
    var allfiles = ['creme/**/js/tests/**/!(qunit)*.js'];
    var default_browsers = ['FirefoxHeadless']
    var globals = {
        THEME_NAME: 'icecream'
    };

    var isEmpty = function(s) {
        return s && s.length > 0;
    };

    var filterEmptyStrings = function(data) {
        data = Array.isArray(data) ? data : [data];
        return data.filter(isEmpty);
    };

    var browsers = filterEmptyStrings(config.browsers);
    browsers = isEmpty(browsers) ? browsers : default_browsers;

    var targets = filterEmptyStrings(Array.isArray(config.targets) ? config.targets : (config.targets || '').split(','));
    targets = isEmpty(targets) ? buildKarmaTestFilesFromPath(targets) : allfiles;

    if (globals) {
        buildKarmaGlobalJs('.karma.globals.js', globals);
        commonfiles = ['.karma.globals.js'].concat(commonfiles);
    }

    config.set({
        plugins: [
            'karma-chrome-launcher',
            'karma-firefox-launcher',
            // 'karma-phantomjs-launcher',
            'karma-jsdom-launcher',
            'karma-qunit',
            'karma-jquery-new',
            'karma-coverage'
        ],
        basePath: '',
        autoWatch: true,
        concurrency: 1,
        frameworks: ['qunit'],
        files: commonfiles.concat(qunitmixins)
                          .concat(targets),
        browsers: browsers,

        customLaunchers: {
            ChromeHeadless: {
                base: 'Chrome',
                flags: [
                    '--no-gpu',
                    '--disable-software-rasterizer',
                    '--headless',
                    '--disable-web-security',
                    '--mute-audio',
                    '--hide-scrollbars',
                    '--remote-debugging-port=' + debug_port
                ]
            },
            // Works on debian stable (strech) with chromium 69
            ChromiumHeadless: {
                base: 'Chromium',
                flags: [
                    '--no-gpu',
                    '--disable-software-rasterizer',
                    '--headless',
                    '--disable-web-security',
                    '--mute-audio',
                    '--hide-scrollbars',
                    '--remote-debugging-port=' + debug_port
                ]
            },
            ChromiumDebug: {
                base: 'Chromium',
                flags: ['--remote-debugging-port=' + debug_port]
            },
            // Works with firefox >= 55
            FirefoxHeadless: {
                base: 'Firefox',
                flags: ['-headless', '-start-debugger-server=' + debug_port]
            },
            FirefoxDebug: {
                base: 'Firefox',
                flags: ['-start-debugger-server=' + debug_port]
            }
        },

        preprocessors: {
            'creme/media/static/main*.js': ['coverage']
        },

        reporters: ['progress', 'coverage'],
        coverageReporter: {
            dir: process.env.DJANGO_KARMA_OUTPUT || '.coverage-karma',
            reporters: [{
                type: 'html',
                subdir: 'html'
            }, {
                type: 'text-summary'
            }]
        },
        failOnEmptyTestSuite: true,
        singleRun: true,
        client: {
            qunit: {
                testTimeout: 6000
            }
        }
    });
};