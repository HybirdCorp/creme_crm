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

    buildKarmaCoverageFromPaths = function(paths) {
        output = {};

        paths.forEach(function(path) {
            output[path] = ['coverage'];
        });

        return output;
    }

    parseKarmaArg = function(config, name, options) {
        options = options || {};
        var value = process.env['KARMA_' + name.toUpperCase()] || options.defaultValue;
        return config[name] || value;
    }
}());

module.exports = function(config) {
    var browserDebugPort = parseKarmaArg(config, 'browserDebugPort', {defaultValue: '9333'});
    var language = parseKarmaArg(config, 'djangoLang', {defaultValue: 'en'});
    var staticsPath = parseKarmaArg(config, 'djangoStatics', {defaultValue: 'creme/media/static'});
    var sourcePath = parseKarmaArg(config, 'djangoSources', {defaultValue: 'creme/**/js'});
    var coverageOutput = parseKarmaArg(config, 'coverageOutput', {defaultValue: 'artifacts/karma_coverage'});

    // TODO: use path from the config
    var commonfiles = [
        staticsPath + '/l10n--' + language + '-*.js',
        staticsPath + '/lib*.js',
        staticsPath + '/main*.js'
    ];

    var qunitfiles = [
        sourcePath + '/tests/**/qunit-parametrize.js',
        sourcePath + '/tests/**/qunit*mixin.js'
    ];

    var allfiles = [sourcePath + '/tests/**/!(qunit)*.js'];
    var defaultBrowsers = ['FirefoxHeadless']
    var globals = {
        THEME_NAME: 'icecream'
    };
    var coverageFiles = [
        staticsPath + '/main*.js'
    ]

    var isEmpty = function(s) {
        return s && s.length > 0;
    };

    var filterEmptyStrings = function(data) {
        data = Array.isArray(data) ? data : [data];
        return data.filter(isEmpty);
    };

    var browsers = filterEmptyStrings(config.browsers);
    browsers = isEmpty(browsers) ? browsers : defaultBrowsers;

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
            'karma-coverage'
        ],
        autoWatch: true,
        concurrency: 1,
        frameworks: ['qunit'],
        files: commonfiles.concat(qunitfiles)
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
                    '--remote-debugging-port=' + browserDebugPort
                ]
            },
            // Works on debian stable (stretch) with chromium 69
            ChromiumHeadless: {
                base: 'Chromium',
                flags: [
                    '--no-gpu',
                    '--disable-software-rasterizer',
                    '--headless',
                    '--disable-web-security',
                    '--mute-audio',
                    '--hide-scrollbars',
                    '--remote-debugging-port=' + browserDebugPort
                ]
            },
            ChromiumDebug: {
                base: 'Chromium',
                flags: ['--remote-debugging-port=' + browserDebugPort]
            },
            // Works with firefox >= 55
            FirefoxHeadless: {
                base: 'Firefox',
                flags: ['-headless', '-start-debugger-server=' + browserDebugPort]
            },
            FirefoxDebug: {
                base: 'Firefox',
                flags: ['-start-debugger-server=' + browserDebugPort]
            }
        },

        preprocessors: buildKarmaCoverageFromPaths(coverageFiles),

        reporters: ['progress', 'coverage'],
        coverageReporter: {
            dir: coverageOutput,
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
