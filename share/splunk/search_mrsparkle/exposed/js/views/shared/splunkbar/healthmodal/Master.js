define([
    'jquery',
    'underscore',
    'module',
    'views/shared/ModalLocalClassNames',
    './HealthTitle',
    './HealthContents',
    './Master.pcssm'
],
function(
    $,
    _,
    module,
    ModalView,
    HealthTitleView,
    HealthContentsView,
    css
) {
    return ModalView.extend({
        moduleId: module.id,
        css: _.extend({}, ModalView.prototype.css, css),
        initialize: function() {
            this.options.titleView = new HealthTitleView();
            this.options.bodyView = new HealthContentsView({
                model: {
                    application: this.model.application,
                    serverInfo: this.model.serverInfo
                }
            });
            ModalView.prototype.initialize.apply(this, arguments);
        }
    });
});