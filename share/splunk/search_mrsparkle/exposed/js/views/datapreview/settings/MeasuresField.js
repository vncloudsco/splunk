define(
[
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/datapreview/settings/MetricsField'
],
function(
    $,
    _,
    Backbone,
    module,
    MetricsField
){
    return MetricsField.extend({
        moduleId: module.id
    });
});
