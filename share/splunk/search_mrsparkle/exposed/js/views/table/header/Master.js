define(
    [
        'underscore',
        'module',
        'models/datasets/Table',
        'models/datasets/commands/InitialData',
        'mixins/dataset',
        'views/Base',
        'views/table/header/TableName',
        'views/table/header/Save',
        'views/shared/controls/SyntheticRadioControl',
        './Master.pcss'
    ],
    function(
        _,
        module,
        TableModel,
        InitialDataModel,
        datasetMixin,
        BaseView,
        TableNameView,
        SaveView,
        SyntheticRadioControl,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.tableName = new TableNameView({
                    model: {
                        table: this.model.table
                    }
                });

                this.children.saveDataset = new SaveView({
                    model: {
                        application: this.model.application,
                        searchPointJob: this.model.searchPointJob,
                        currentPointJob: this.model.currentPointJob,
                        table: this.model.table,
                        tablePristine: this.model.tablePristine,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo
                    },
                    collection: {
                        roles: this.collection.roles
                    }
                });
            },

            events: {
                'click .preview a': function (e) {
                    e.preventDefault();
                    this.model.table.entry.content.set('dataset.display.mode', datasetMixin.MODES.TABLE);
                },

                'click .summarize a': function(e) {
                    e.preventDefault();
                    this.model.table.entry.content.set('dataset.display.mode', datasetMixin.MODES.DATA_SUMMARY);
                }
            },


            activate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                if (this.active) {
                    return BaseView.prototype.activate.call(this, clonedOptions);
                }

                this.children.tableName.activate({ deep: true });
                this.manageStateOfChildren();
                return BaseView.prototype.activate.call(this, clonedOptions);
            },

            startListening: function() {
                this.listenTo(this.model.state, 'change:initialDataState', this.manageStateOfChildren);
                this.listenTo(this.model.table.entry.content, 'change:dataset.display.mode', this.manageStateOfChildren);
            },

            manageStateOfChildren: function() {
                if (this.model.state.get('initialDataState') === InitialDataModel.STATES.EDITING) {
                    this.$('.nav-tabs').hide();
                    this.children.saveDataset.deactivate({ deep: true }).$el.hide();
                    return;
                }

                this.$('.nav-tabs').css('display', '');
                this.children.saveDataset.activate({ deep: true }).$el.css('display', '');

                var currentTab = this.model.table.entry.content.get('dataset.display.mode');
                if (currentTab !== datasetMixin.MODES.DATA_SUMMARY) {
                    this.$('.preview').addClass('active');
                    this.$('.summarize').removeClass('active');
                } else {
                    this.$('.preview').removeClass('active');
                    this.$('.summarize').addClass('active');
                }
            },

            render: function() {
                if (!this.el.innerHTML) {
                    this.$el.html(this.compiledTemplate());

                    this.children.tableName.activate({ deep: true }).render().prependTo(this.$el);
                    this.children.saveDataset.render().appendTo(this.$('.btn-container'));
                }
                this.manageStateOfChildren();

                return this;
            },

            template: '\
                <ul class="nav nav-tabs">\
                    <li class="preview"><a href="#"><%- _(\'Preview Rows\').t() %></a></li>\
                    <li class="summarize"><a href="#"><%- _(\'Summarize Fields\').t() %></a></li>\
                </ul>\
                <div class="btn-container"></div>\
            '
        });
    }
);
