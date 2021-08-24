define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/datasetcontrols/clone/Master',
        './Master.pcss',
        'uri/route'
    ],
    function(
        $,
        _,
        module,
        BaseView,
        CloneDialog,
        css,
        route
    ) {
        return BaseView.extend({
            moduleId: module.id,
            className: 'dataset-extend-menu',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            events: {
                'click a.clone': function(e) {
                    this.children.cloneDialog = new CloneDialog({
                        model: {
                            dataset: this.model.dataset,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            application: this.model.application
                        },
                        onHiddenRemove: true,
                        nameLabel: this.model.dataset.getDatasetDisplayType()
                    });

                    this.children.cloneDialog.render().appendTo($("body"));
                    this.children.cloneDialog.show();
                    e.preventDefault();
                }
            },

            render: function() {
                this.$el.html(this.compiledTemplate({
                    canClone: this.model.dataset.canClone()
                }));

                if (this.options.displayAsButtons) {
                    this.$el.addClass('btn-group');
                    this.$('div').addClass('btn-combo');
                    this.$('a').addClass('btn');
                }

                return this;
            },

            template: '\
                <% if (canClone) { %>\
                    <div>\
                        <a href="#" class="clone"><%- _("Clone").t() %></a>\
                    </div>\
                <% } %>\
            '
        });
    }
);

