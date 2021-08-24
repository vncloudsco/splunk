define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/datapreview/settings/Timestamp',
        'views/datapreview/settings/EventBreaks',
        'views/datapreview/settings/Fields',
        'views/datapreview/settings/Metrics',
        'views/datapreview/settings/Advanced',
        'views/datapreview/shared/Tab',
        'models/datapreview/ActiveTab',
        'bootstrap.collapse' //NO IMPORT
    ],
    function(
        $,
        _,
        module,
        BaseView,
        TimestampView,
        EventBreaksView,
        FieldsView,
        MetricsView,
        AdvancedView,
        Tab,
        ActiveTabModel
    ){
        return BaseView.extend({
            moduleId: module.id,
            className: 'tab datapreview-settings',
            initialize: function(options) {
                BaseView.prototype.initialize.apply(this, arguments);
                this.options = options;
                this.model.activeTab = new ActiveTabModel();

                this.children.eventBreaksTab = new Tab({
                    tab: 'eventbreaks',
                    label: _("Event Breaks").t(),
                    targetEntity: this.model.activeTab,
                    targetAttribute: "tab",
                    listenOnInitialize: true
                });

                this.children.eventBreaksView = new EventBreaksView({
                    heading: _('Event Breaks').t(),
                    model: this.model,
                    collection: this.collection,
                    enableAccordion: true
                });

                this.children.timestampTab = new Tab({
                    tab: 'timestamp',
                    label: _("Timestamp").t(),
                    targetEntity: this.model.activeTab,
                    targetAttribute: "tab",
                    listenOnInitialize: true
                });

                this.children.timestampView = new TimestampView({
                    heading: _('Timestamp').t(),
                    model: this.model,
                    collection: this.collection
                });

                this.children.metricsTab = new Tab({
                    tab: 'metrics',
                    label: _("Metrics").t(),
                    targetEntity: this.model.activeTab,
                    targetAttribute: "tab",
                    listenOnInitialize: true
                });

                this.children.metricsView = new MetricsView({
                    heading: _('Metrics').t(),
                    model: this.model,
                    collection: this.collection
                });

                this.children.fieldsTab = new Tab({
                    tab: 'fields',
                    label: _("Fields").t(),
                    targetEntity: this.model.activeTab,
                    targetAttribute: "tab",
                    listenOnInitialize: true
                });

                this.children.fieldsView = new FieldsView({
                    heading: _('Delimited settings').t(),
                    model: this.model,
                    collection: this.collection
                });

                this.children.advancedTab = new Tab({
                    tab: 'advanced',
                    label: _("Advanced").t(),
                    targetEntity: this.model.activeTab,
                    targetAttribute: "tab",
                    listenOnInitialize: true
                });

                this.children.advancedView = new AdvancedView({
                    heading: _('Advanced').t(),
                    model: this.model,
                    collection: this.collection,
                    updateSilent: this.options.updateSilent
                });

                this.model.sourcetypeModel.on('sync', function() {
                    this.setPanels();
                }.bind(this));

                this.model.sourcetypeModel.entry.content.on('change:INDEXED_EXTRACTIONS', function() {
                    this.setPanels();
                }.bind(this));

                this.model.sourcetypeModel.entry.content.on('change:category', function() {
                    this.setPanels();
                }.bind(this));

                this.activate();
            },
            startListening: function() {
                this.listenTo(this.model.activeTab, 'change:tab', function() {
                    this.manageStateOfChildren();
                });
            },
            activate: function(options) {
                var clonedOptions = _.extend({}, (options || {}));
                delete clonedOptions.deep;

                this.ensureDeactivated({deep: true});

                BaseView.prototype.activate.call(this, clonedOptions);
                this.manageStateOfChildren();
                return this;
            },
            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }

                BaseView.prototype.deactivate.apply(this, arguments);

                return this;
            },
            manageStateOfChildren: function() {
                var tab = this.model.activeTab.get('tab');
                if (tab === 'eventbreaks') {
                    if (!this.children.eventBreaksView.active) {
                        this.children.eventBreaksView.activate().$el.show();
                    }

                    this.children.timestampView.deactivate({deep: true}).$el.hide();
                    this.children.metricsView.deactivate({deep: true}).$el.hide();
                    this.children.fieldsView.deactivate({deep: true}).$el.hide();
                    this.children.advancedView.deactivate({deep: true}).$el.hide();
                } else if (tab === 'timestamp') {
                    if (!this.children.timestampView.active) {
                        this.children.timestampView.activate().$el.show();
                    }

                    this.children.eventBreaksView.deactivate({deep: true}).$el.hide();
                    this.children.metricsView.deactivate({deep: true}).$el.hide();
                    this.children.fieldsView.deactivate({deep: true}).$el.hide();
                    this.children.advancedView.deactivate({deep: true}).$el.hide();
                } else if (tab === 'metrics') {
                    if (!this.children.metricsView.active) {
                        this.children.metricsView.activate().$el.show();
                    }

                    this.children.eventBreaksView.deactivate({deep: true}).$el.hide();
                    this.children.timestampView.deactivate({deep: true}).$el.hide();
                    this.children.fieldsView.deactivate({deep: true}).$el.hide();
                    this.children.advancedView.deactivate({deep: true}).$el.hide();
                } else if (tab === 'fields') {
                    if (!this.children.fieldsView.active) {
                        this.children.fieldsView.activate().$el.show();
                    }

                    this.children.eventBreaksView.deactivate({deep: true}).$el.hide();
                    this.children.timestampView.deactivate({deep: true}).$el.hide();
                    this.children.metricsView.deactivate({deep: true}).$el.hide();
                    this.children.advancedView.deactivate({deep: true}).$el.hide();
                } else if (tab === 'advanced') {
                    if (!this.children.advancedView.active) {
                        this.children.advancedView.activate().$el.show();
                    }

                    this.children.eventBreaksView.deactivate({deep: true}).$el.hide();
                    this.children.timestampView.deactivate({deep: true}).$el.hide();
                    this.children.metricsView.deactivate({deep: true}).$el.hide();
                    this.children.fieldsView.deactivate({deep: true}).$el.hide();
                }
                return this;
            },
            setPanels: function() {
                var type = this.model.sourcetypeModel.getDataFormat();
                if (type === this.lastType) {
                    return;
                }
                this.lastType = type;
                switch(type) {
                    case this.model.sourcetypeModel.constructor.UNSTRUCTURED:
                       this.prepareUnstructured();
                    break;
                    case this.model.sourcetypeModel.constructor.HIERARCHICAL:
                       this.prepareHierarchical();
                    break;
                    case this.model.sourcetypeModel.constructor.TABULAR:
                       this.prepareTabular();
                    break;
                    case this.model.sourcetypeModel.constructor.METRIC:
                       this.prepareMetric();
                    break;
                    default:
                        this.prepareUnstructured();
                    break;
                }
            },
            render: function() {
                if (!this.el.innerHTML) {
                    this.$el.html(this.template);
                }

                this.children.eventBreaksTab.render().appendTo(this.$('.nav-tabs'));
                this.children.timestampTab.render().appendTo(this.$('.nav-tabs'));
                this.children.metricsTab.render().appendTo(this.$('.nav-tabs'));
                this.children.fieldsTab.render().appendTo(this.$('.nav-tabs'));
                this.children.advancedTab.render().appendTo(this.$('.nav-tabs'));

                this.children.eventBreaksView.render().appendTo(this.$('.tab-content'));
                this.children.timestampView.render().appendTo(this.$('.tab-content'));
                this.children.metricsView.render().appendTo(this.$('.tab-content'));
                this.children.fieldsView.render().appendTo(this.$('.tab-content'));
                this.children.advancedView.render().appendTo(this.$('.tab-content'));

                this.setPanels.call(this);

                return this;
            },
            prepareUnstructured: function() {
                this.children.eventBreaksTab.$el.show();
                this.children.timestampTab.$el.show();
                this.children.metricsTab.$el.hide();
                this.children.fieldsTab.$el.hide();
                this.children.advancedTab.$el.show();

                this.model.activeTab.set('tab', 'eventbreaks');

                this.children.eventBreaksView.$el.show();
                this.children.timestampView.$el.hide();
                this.children.metricsView.$el.hide();
                this.children.fieldsView.$el.hide();
                this.children.advancedView.$el.hide();
            },
            prepareHierarchical: function() {
                this.children.eventBreaksTab.$el.hide();
                this.children.timestampTab.$el.show();
                this.children.metricsTab.$el.hide();
                this.children.fieldsTab.$el.hide();
                this.children.advancedTab.$el.show();

                this.model.activeTab.set('tab', 'timestamp');

                this.children.eventBreaksView.$el.hide();
                this.children.timestampView.$el.show();
                this.children.metricsView.$el.hide();
                this.children.fieldsView.$el.hide();
                this.children.advancedView.$el.hide();
            },
            prepareTabular: function() {
                this.children.eventBreaksTab.$el.hide();
                this.children.timestampTab.$el.show();
                this.children.metricsTab.$el.hide();
                this.children.fieldsTab.$el.show();
                this.children.advancedTab.$el.show();

                this.model.activeTab.set('tab', 'timestamp');

                this.children.eventBreaksView.$el.hide();
                this.children.timestampView.$el.show();
                this.children.metricsView.$el.hide();
                this.children.fieldsView.$el.hide();
                this.children.advancedView.$el.hide();
            },
            prepareMetric: function() {
                this.children.eventBreaksTab.$el.show();
                this.children.timestampTab.$el.show();
                this.children.metricsTab.$el.show();
                this.children.fieldsTab.$el.hide();
                this.children.advancedTab.$el.show();

                this.model.activeTab.set('tab', 'eventbreaks');

                this.children.eventBreaksView.$el.show();
                this.children.timestampView.$el.hide();
                this.children.metricsView.$el.hide();
                this.children.fieldsView.$el.hide();
                this.children.advancedView.$el.hide();
            },
            template: '\
                <ul class="nav nav-tabs main-tabs"></ul>\
                <div class="tab-content tab-group" style="overflow:visible; padding-top:15px;"></div>\
            '
        });
    }
);
