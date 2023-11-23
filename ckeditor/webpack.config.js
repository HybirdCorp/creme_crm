// webpack.config.js

'use strict';

const path = require( 'path' );
const webpack = require( 'webpack' );

const { styles } = require( '@ckeditor/ckeditor5-dev-utils' );
const TerserPlugin = require("terser-webpack-plugin");

const ckeditorPackage = require('@ckeditor/ckeditor5-core/package.json');

module.exports = {
    entry: './bundle.js',

    output: {
        path: path.resolve( __dirname, 'dist' ),
        filename: `ckeditor5-${ckeditorPackage.version}.js`,
        libraryTarget: 'window'
    },

    module: {
        rules: [
            {
                test: /^bundle.js$/,
                use: [ 'export-loader' ]
            },
            {
                test: /ckeditor5-[^/\\]+[/\\]theme[/\\]icons[/\\][^/\\]+\.svg$/,
                use: [ 'raw-loader' ]
            },
            {
                test: /ckeditor5-[^/\\]+[/\\]theme[/\\].+\.css$/,
                use: [
                    {
                        loader: 'style-loader',
                        options: {
                            injectType: 'singletonStyleTag',
                            attributes: {
                                'data-cke': true
                            }
                        }
                    },
                    'css-loader',
                    {
                        loader: 'postcss-loader',
                        options: {
                            postcssOptions: styles.getPostCssConfig( {
                                themeImporter: {
                                    themePath: require.resolve( '@ckeditor/ckeditor5-theme-lark' )
                                },
                                minify: true
                            } )
                        }
                    }
                ]
            }
        ]
    },

    optimization: {
        minimize: true,
        minimizer: [new TerserPlugin({
            minify: TerserPlugin.swcMinify,
            terserOptions: {
                compress: true
            }
        })],
    },

    // Useful for debugging.
    devtool: 'source-map',

    // By default webpack logs warnings if the bundle is bigger than 200kb.
    performance: { hints: false }
};
