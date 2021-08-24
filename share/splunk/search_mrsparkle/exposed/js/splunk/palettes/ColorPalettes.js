define(function(require, exports, module) {

    var Class = require("jg/Class");
    var ColorCodes = require("splunk/palettes/ColorCodes");
    var ListColorPalette = require("splunk/palettes/ListColorPalette");

    return Class(module.id, function(ColorPalettes) {

        // Public Static Constants

        ColorPalettes.CATEGORICAL = new ListColorPalette(ColorCodes.toColors(ColorCodes.CATEGORICAL));

        ColorPalettes.SEMANTIC = new ListColorPalette(ColorCodes.toColors(ColorCodes.SEMANTIC));

    });

});
