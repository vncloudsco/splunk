define(
    [
        'jquery',
        'underscore',
        'module',
        'models/services/data/transforms/MetricSchema',
        'views/Base',
        'views/datapreview/settings/Timestamp',
        'views/datapreview/settings/EventBreaks',
        'views/datapreview/settings/Fields',
        'views/datapreview/settings/Metrics',
        'views/datapreview/settings/Advanced',
        'contrib/text!views/datapreview/settings/AccordionGroup.html',
        'bootstrap.collapse' //NO IMPORT
    ],
    function(
        $,
        _,
        module,
        MetricTransformsModel,
        BaseView,
        TimestampView,
        EventBreaksView,
        FieldsView,
        MetricsView,
        AdvancedView,
        AccordionGroupTemplate
    ){
        return BaseView.extend({
            moduleId: module.id,
            className: 'accordion datapreview-settings',
            initialize: function(options) {
                BaseView.prototype.initialize.apply(this, arguments);
                this.options = options;
                this.model.metricTransformsModel = new MetricTransformsModel({
                    isCloud: this.model.serverInfo.isCloud()
                });

                if(typeof this.options.enableAccordion === 'undefined'){
                    this.options.enableAccordion = true;
                }

                this.children.eventBreaksView = new EventBreaksView({
                    heading: _('Event Breaks').t(),
                    model: this.model,
                    collection: this.collection,
                    enableAccordion: true
                });

                this.children.timestamp = new TimestampView({
                    heading: _('Timestamp').t(),
                    model: this.model,
                    collection: this.collection
                });

                this.children.fields = new FieldsView({
                    heading: _('Delimited settings').t(),
                    model: this.model,
                    collection: this.collection
                });

                this.children.metricsView = new MetricsView({
                    heading: _('Metrics').t(),
                    model: this.model,
                    collection: this.collection
                });

                this.children.advanced = new AdvancedView({
                    heading: _('Advanced').t(),
                    model: this.model,
                    collection: this.collection,
                    updateSilent: this.options.updateSilent
                });

                this.model.sourcetypeModel.on('sync', function(){
                    this.setPanels();
                }.bind(this));

                this.model.sourcetypeModel.entry.content.on('change:INDEXED_EXTRACTIONS', function(){
                    this.setPanels();
                }.bind(this));

            },
            setPanels: function(){
                var type = this.model.sourcetypeModel.getDataFormat();
                switch(type){
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

            events: {
                'click .accordion-heading a': function(e) {
                    e.preventDefault();
                    if ($(e.target).hasClass('icon-accordion-toggle')) {
                        $(e.target).toggleClass("icon-triangle-down-small");
                    }
                    $(e.target).find(".icon-accordion-toggle").toggleClass("icon-triangle-down-small").closest('.accordion-group').toggleClass('active');
                    $(e.target).closest('.accordion-group').find('.accordion-inner').slideToggle(200);
                }
            },

            render: function() {
                _.each(this.children, function(panel) {
                    panel.detach();
                }, this);
                this.$el.html('');
                var i = 0;
                var template = _.template(AccordionGroupTemplate);

                _.each(this.children, function(panel) {
                    var accordionGroup = $(template({
                        heading: panel.options.heading || '',
                        index: i++,
                        enableAccordion: this.options.enableAccordion || panel.options.enableAccordion
                    }));
                    accordionGroup.find('.accordion-inner').append(panel.render().el);
                    accordionGroup.appendTo(this.$el);
                }, this);

                this.setPanels.call(this);

                return this;
            },
            prepareUnstructured: function(){
                this.children.eventBreaksView.$el.closest('.accordion-group').show().addClass('active');
                this.children.timestamp.$el.closest('.accordion-group').show().addClass('active');
                this.children.fields.$el.closest('.accordion-group').hide();
                this.children.metricsView.$el.closest('.accordion-group').hide();
                this.children.advanced.$el.closest('.accordion-group').show().addClass('active');
            },
            prepareHierarchical: function(){
                this.children.eventBreaksView.$el.closest('.accordion-group').hide();
                this.children.timestamp.$el.closest('.accordion-group').show().addClass('active');
                this.children.fields.$el.closest('.accordion-group').hide();
                this.children.metricsView.$el.closest('.accordion-group').hide();
                this.children.advanced.$el.closest('.accordion-group').show().addClass('active');
            },
            prepareTabular: function(){
                this.children.eventBreaksView.$el.closest('.accordion-group').hide();
                this.children.timestamp.$el.closest('.accordion-group').show().addClass('active');
                this.children.fields.$el.closest('.accordion-group').show().addClass('active');
                this.children.metricsView.$el.closest('.accordion-group').hide();
                this.children.advanced.$el.closest('.accordion-group').show().addClass('active');
            },
            prepareMetric: function(){
                this.children.metricsView.setMetricData();

                this.children.eventBreaksView.$el.closest('.accordion-group').show().addClass('active');
                this.children.timestamp.$el.closest('.accordion-group').show().addClass('active');
                this.children.fields.$el.closest('.accordion-group').hide();
                this.children.metricsView.$el.closest('.accordion-group').show().addClass('active');
                this.children.advanced.$el.closest('.accordion-group').show().addClass('active');
            }
        });
    }
);
