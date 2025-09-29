const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const webpack = require('webpack');

const cesiumSource = 'node_modules/cesium/Build/Cesium';

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // Add Cesium to the webpack configuration
      webpackConfig.resolve.fallback = {
        ...webpackConfig.resolve.fallback,
        fs: false,
        path: false,
        url: false,
        zlib: false,
        http: false,
        https: false,
        stream: false,
        crypto: false,
        assert: false,
        os: false,
        constants: false,
        buffer: false,
        process: false,
      };

      // Add Cesium to the webpack configuration
      webpackConfig.module.rules.push({
        test: /\.js$/,
        enforce: 'pre',
        include: path.resolve(__dirname, 'node_modules/cesium/Source'),
        use: 'strip-pragma-loader'
      });

      // Copy Cesium assets
      webpackConfig.plugins.push(
        new CopyWebpackPlugin({
          patterns: [
            {
              from: path.join(cesiumSource, 'Workers'),
              to: 'cesium/Workers',
            },
            {
              from: path.join(cesiumSource, 'ThirdParty'),
              to: 'cesium/ThirdParty',
            },
            {
              from: path.join(cesiumSource, 'Assets'),
              to: 'cesium/Assets',
            },
            {
              from: path.join(cesiumSource, 'Widgets'),
              to: 'cesium/Widgets',
            },
          ],
        }),
        new webpack.DefinePlugin({
          CESIUM_BASE_URL: JSON.stringify('/cesium'),
        })
      );

      return webpackConfig;
    },
  },
}; 