const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserJsPlugin = require('terser-webpack-plugin');

module.exports = {
  mode: 'production',
  entry: './src/editor.js',
  resolve: {
    extensions: ['.js']
  },
  plugins: [
    new MiniCssExtractPlugin(),
  ],
  optimization: {
    minimize: true,
    minimizer: [
      new TerserJsPlugin({
        terserOptions: {
          compress: {
            passes: 2
          },
          ie8: false,
        }
      })
    ]
  },
  module: {
    rules: [
      {
        test: /skin\.css$/i,
        use: [ MiniCssExtractPlugin.loader, 'css-loader' ],
      },
      {
        test: /content\.css$/i,
        loader: 'css-loader',
        options: {
          esModule: false,
        },
      },
    ],
  },
  output: {
    filename: 'tinymce-bundle.js',
    path: path.resolve(__dirname, 'dist'),
    clean: true,
    library: 'TinyMCEBundle',
    libraryTarget: 'umd'
  },
};