define(function(require, exports, module) {
    var SharedModels = require('./sharedmodels');

    return {
        load: function(name, req, onLoad) {
            SharedModels.load('visualizations').done(onLoad);
        }
    };

});
