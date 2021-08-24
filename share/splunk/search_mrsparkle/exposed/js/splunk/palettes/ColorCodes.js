define(function(require, exports, module) {

    var Class = require("jg/Class");
    var Color = require("jg/graphics/Color");

    return Class(module.id, function(ColorCodes) {

        // Public Static Constants

        ColorCodes.CATEGORICAL = [
            "#006d9c", "#4fa484", "#ec9960", "#af575a", "#b6c75a", "#62b3b2", "#294e70", "#738795", "#edd051", "#bd9872",
            "#5a4575", "#7ea77b", "#708794", "#d7c6b7", "#339bb2", "#55672d", "#e6e1ae", "#96907f", "#87bc65", "#cf7e60",
            "#7b5547", "#77d6d8", "#4a7f2c", "#f589ad", "#6a2c5d", "#aaabae", "#9a7438", "#a4d563", "#7672a4", "#184b81",
            "#7fb6ce", "#a7d2c2", "#f6ccb0", "#d7abad", "#dbe3ad", "#b1d9d9", "#94a7b8", "#b9c3ca", "#f6e8a8", "#deccb9",
            "#b7acca", "#b2cab0", "#a5b2bf", "#e9ddd4", "#66c3d0", "#aab396", "#f3f0d7", "#c1bcb3", "#b6d7a3", "#e1b2a1",
            "#dec4ba", "#abe6e8", "#91b282", "#f8b7ce", "#cba3c2", "#cccdce", "#c3ab89", "#c7e6a3", "#ada9c8", "#a4bbe0"
        ];

        ColorCodes.CATEGORICAL_DARK = ColorCodes.CATEGORICAL; // @pwied: for now we use the same colors in dark mode

        ColorCodes.SEMANTIC_BY_NAME = {
            success: "#53a051",
            info: "#006d9c",
            warning: "#f8be34",
            alert: "#f1813f",
            error: "#dc4e41"
        };

        ColorCodes.SEMANTIC = [
            ColorCodes.SEMANTIC_BY_NAME.success,
            ColorCodes.SEMANTIC_BY_NAME.info,
            ColorCodes.SEMANTIC_BY_NAME.warning,
            ColorCodes.SEMANTIC_BY_NAME.alert,
            ColorCodes.SEMANTIC_BY_NAME.error
        ];

        ColorCodes.SEMANTIC_DARK = ColorCodes.SEMANTIC;

        ColorCodes.SEQUENTIAL = [
            ColorCodes.SEMANTIC_BY_NAME.success,
            ColorCodes.SEMANTIC_BY_NAME.error,
            ColorCodes.SEMANTIC_BY_NAME.info
        ];

        ColorCodes.DIVERGENT_PAIRS = [
            ["#006D9C", "#EC9960"],
            ["#62B3B2", "#AF575A"],
            ["#AF575A", "#F8BE34"],
            ["#F8BE34", "#4FA484"],
            ["#708794", "#5A4575"],
            ["#294E70", "#B6C75A"]
        ];

        ColorCodes.DARK_GREY = '#3c444d';

        // Public Static Methods

        ColorCodes.toColors = function(codes) {
            var colors = [];
            for (var i = 0, l = codes.length; i < l; i++) {
                colors.push(Color.fromString(codes[i]));
            }
            return colors;
        };

        ColorCodes.toNumbers = function(codes) {
            var numbers = [];
            for (var i = 0, l = codes.length; i < l; i++) {
                numbers.push(Color.fromString(codes[i]).toNumber());
            }
            return numbers;
        };

        ColorCodes.toArrays = function(codes) {
            var arrays = [];
            for (var i = 0, l = codes.length; i < l; i++) {
                arrays.push(Color.fromString(codes[i]).toArray());
            }
            return arrays;
        };

        ColorCodes.toPrefixed = function(codes, prefix) {
            var prefixed = [];
            for (var i = 0, l = codes.length; i < l; i++) {
                prefixed.push(prefix + codes[i].replace(/^(0x|#)/, ""));
            }
            return prefixed;
        };

    });

});
