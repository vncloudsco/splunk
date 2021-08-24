define(
    [
        'module',
        'views/Base'
    ],
    function(
        module,
        BaseView
    ) {
        return BaseView.extend({
            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            startListening: function() {
                this.listenTo(this.model.dataset.entry, 'change:name', this.debouncedRender);
                this.listenTo(this.model.dataset.entry.content, 'change:accelerated', this.debouncedRender);
                this.listenTo(this.model.dataset.entry.content, 'change:dataset.description', this.debouncedRender);
            },

            render: function() {
                this.$el.html(this.compiledTemplate({
                    name: this.model.dataset.getFormattedName(),
                    description: this.model.dataset.getDescription(),
                    datasetTypeCanBeAccelerated: this.model.dataset.typeCanBeAccelerated(),
                    isAcceleratedDataset: this.model.dataset.isAcceleratedDataset()
                }));

                return this;
            },

            template: '\
                <h2 class="section-title">\
                    <%- name %>\
                    <% if (datasetTypeCanBeAccelerated) { %>\
                        <i class="icon-lightning <% if (isAcceleratedDataset) { %>icon-lightning-selected<% } %>" title="<%= isAcceleratedDataset ? _("Accelerated").t() : _("Not Accelerated").t() %>"></i>\
                    <% } %>\
                </td>\
                </h2>\
                <% if (description) { %>\
                    <p class="section-description">\
                        <%- description %>\
                    </p>\
                <% } %>\
            '
        });
    }
);
