define([
    'jquery',
    'module',
    'views/Base',
    'contrib/text!views/clustering/push/ActionProgress.html',
    'views/clustering/push/ActionProgress.pcss',
    'util/console'
],
    function(
        $,
        module,
        BaseView,
        Template,
        css,
        console
        ) {
        return BaseView.extend({
            moduleId: module.id,
            template: Template,
            initialize: function(options) {
                options = options || {};
                BaseView.prototype.initialize.call(this, options);
                this.model.pushModel.on('tick', this.render, this);

                this.peerActionTypeKey = options.peerActionTypeKey; // 'peersRestarted'
                this.label = options.label;

            },
            reset: function() {
                this.model.pushModel.set(this.peerActionTypeKey, 0);
                this.render();
            },
            render: function() {
                var html = this.compiledTemplate({
                    count: this.model.pushModel.get(this.peerActionTypeKey),
                    total: this.model.pushModel.get('peersTotal'),
                    label: this.label
                });
                this.$el.html(html);
            }
        });

    });