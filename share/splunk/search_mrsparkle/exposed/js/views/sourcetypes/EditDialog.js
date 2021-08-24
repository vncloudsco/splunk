/**
 * @author lbudchenko / callan
 * @date 5/5/15
 *
 * Popup dialog for editing sourcetype config
 */

define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'models/services/data/transforms/MetricSchema',
    'views/shared/FlashMessages',
    'views/shared/Modal',
    'views/shared/controls/ControlGroup',
    'views/datapreview/settings/SettingsTabControls',
    'views/shared/waitspinner/Master'
],

    function(
        $,
        _,
        Backbone,
        module,
        MetricTransformsModel,
        FlashMessages,
        Modal,
        ControlGroup,
        SettingsTabControls,
        WaitSpinner
        ) {

        return Modal.extend({
            moduleId: module.id,
            className: Modal.CLASS_NAME + ' edit-dialog-modal modal-wide',

            events: $.extend({}, Modal.prototype.events, {
                'click .btn-primary': function(e) {
                    this.updateModel();

                    var selectedCategory = this.model.entity.entry.content.get('category');
                    var isCategoryLogToMetrics = selectedCategory === 'Log to Metrics';
                    if (!isCategoryLogToMetrics) {
                        this.saveSourcetype(isCategoryLogToMetrics);
                        return;
                    }
                    var app = this.canUseApps ? this.model.entity.entry.acl.get('app') : "search";
                    var saveOptions = {
                        sourcetypeModel: this.model.entity,
                        data: {app: app, owner: 'nobody'}
                    };
                    var saveDfd = this.model.metricTransformsModel.save(null, saveOptions);
                    if (saveDfd) {
                        this.$('.shared-waitspinner').show();
                        saveDfd.done(function() {
                            // Remove timeout after SPL-157987 is fixed
                            setTimeout(function() {
                                this.saveSourcetype(isCategoryLogToMetrics);
                            }.bind(this), 2000);
                        }.bind(this))
                        .fail(function() {
                            this.$el.find('.modal-body').animate({ scrollTop: 0 }, 'fast');
                            this.$('.shared-waitspinner').hide();
                        }.bind(this));
                    }
                }
            }),

            initialize: function(options) {
                Modal.prototype.initialize.apply(this, arguments);
                options = options || {};
                _(options).defaults({isNew:true});

                this.model.metricTransformsModel = new MetricTransformsModel({
                    isCloud: this.model.serverInfo.isCloud()
                });

                this.renderDfd = new $.Deferred();
                this.deferreds = options.deferreds;

                this.canUseApps = this.model.user.canUseApps();

                this.children.flashMessagesView = new FlashMessages({
                    helperOptions: {
                        removeServerPrefix: true,
                        postProcess: this.postProcess
                    }
                });
                this.children.flashMessagesView.register(this.model.entity);
                this.children.flashMessagesView.register(this.model.metricTransformsModel);

                this.children.waitSpinner = new WaitSpinner({});

                // Create the form controls
                this.children.entityName = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'name',
                        model: this.model.entity.entry
                    },
                    label: _('Name').t()
                });

                this.children.entityDesc = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'description',
                        model: this.model.entity.entry.content,
                        placeholder: _('optional').t()
                    },
                    label: _('Description').t(),
                    required: false
                });

                this.children.appSelect = new ControlGroup({
                    label: _('Destination app').t(),
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        model: this.model.entity.entry.acl,
                        modelAttribute: 'app',
                        items: [],
                        additionalClassNames: 'fieldAppSelect',
                        toggleClassName: 'btn',
                        popdownOptions: {
                            detachDialog: true
                        },
                        save: false
                    }
                });

                this.children.categorySelect = new ControlGroup({
                    label: _('Category').t(),
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        model: this.model.entity.entry.content,
                        modelAttribute: 'category',
                        items: [],
                        additionalClassNames: 'fieldCategorySelect',
                        toggleClassName: 'btn',
                        popdownOptions: {
                            detachDialog: true
                        },
                        save: false
                    }
                });

                var indexedExtractionItems = [
                    {value: '', label: 'none'},
                    {value: 'json'},
                    {value: 'csv'},
                    {value: 'tsv'},
                    {value: 'psv'},
                    {value: 'w3c'}
                ];
                var selectedCategory = this.model.entity.entry.content.get('category');
                var isCategoryLogToMetrics = selectedCategory === 'Log to Metrics';
                if (isCategoryLogToMetrics) {
                    indexedExtractionItems.push({value: 'field_extraction'});
                }
                this.children.indexedExtractions = new ControlGroup({
                    label: _('Indexed Extractions').t(),
                    controlType: 'SyntheticSelect',
                    tooltip: _('Use this setting only for structured data files whose type matches an entry in this list. Choose \'none\' for other types of data.').t(),
                    controlOptions: {
                        model: this.model.entity.entry.content,
                        modelAttribute: 'INDEXED_EXTRACTIONS',
                        items: indexedExtractionItems,
                        additionalClassNames: 'fieldIndexedExtractionsSelect',
                        toggleClassName: 'btn',
                        popdownOptions: {
                            attachDialogTo: 'body'
                        },
                        save: false
                    }
                });

                this.children.settingsTabControls = new SettingsTabControls({
                    collection: this.collection,
                    model: {
                        sourcetypeModel: this.model.entity,
                        metricTransformsModel: this.model.metricTransformsModel,
                        application: this.model.application
                    },
                    enableAccordion: false,
                    advancedToggle: true,
                    updateSilent: false
                });

                this.startListening();

                $.when(
                    this.deferreds.entity
                ).done(function(){
                    this.setIndexedExtractions();
                    this.setEnabledState();
                }.bind(this));

                if (this.canUseApps) {
                    $.when(
                        this.deferreds.entity,
                        this.deferreds.appLocals
                    ).done(function(){
                        this.setAppItems();
                    }.bind(this));
                }

                $.when(
                    this.deferreds.entity,
                    this.deferreds.entities,
                    this.deferreds.sourcetypesCategories
                ).done(function(){
                    this.setCategoryItems();
                }.bind(this));
            },

            startListening: function() {
                this.listenTo(this.model.entity.entry.content, 'change:category', this.updateIndexedExtractions);
                this.listenTo(this.model.entity.entry.content, 'change:INDEXED_EXTRACTIONS', this.updateIndexedExtractionWarning);
            },

            saveSourcetype: function(isCategoryLogToMetrics) {
                var saveOptions = {};
                if (this.model.entity.isNew() || this.options.isClone) {
                    var app = this.canUseApps ? this.model.entity.entry.acl.get('app') : 'search';
                    saveOptions.data = {app: app, owner: 'nobody'};
                    this.model.entity.entry.content.set('pulldown_type', 1);
                }

                var schemaName = this.model.metricTransformsModel.get('name') || this.model.entity.get('ui.metric_transforms.schema_name');
                if (schemaName && (schemaName.indexOf('metric-schema:') >= 0)) {
                    schemaName = schemaName.split('metric-schema:')[1];
                }
                if (!isCategoryLogToMetrics && schemaName) {
                    this.model.entity.set('ui.metric_transforms.schema_name', '');
                } else if (schemaName) {
                    this.model.entity.set({'ui.metric_transforms.schema_name': 'metric-schema:' + schemaName});
                }
                var saveDfd = this.model.entity.save({}, saveOptions);
                if (saveDfd) {
                    saveDfd.done(function() {
                        this.$('.shared-waitspinner').hide();
                        this.trigger("entitySaved", this.model.entity.get("name"));
                        this.hide();
                        var schemaNameExists = !_.isEmpty(schemaName);
                        if (!isCategoryLogToMetrics && schemaNameExists) {
                            this.model.metricTransformsModel.deleteMetricTranform(schemaName, this.model.entity);
                        }
                    }.bind(this))
                    .fail(function() {
                        this.$('.shared-waitspinner').hide();
                        this.$el.find('.modal-body').animate({ scrollTop: 0 }, 'fast');
                        if (isCategoryLogToMetrics) {
                            this.model.metricTransformsModel.deleteMetricTranform(schemaName, this.model.entity);
                        }
                    }.bind(this));
                } else {
                    this.$('.shared-waitspinner').hide();
                }
            },

            postProcess: function(messages) {
                if (messages.length) {
                    messages[0].set({'html': _.unescape(messages[0].get('html'))});
                }
                return messages;
            },

            setEnabledState: function(){
                //TODO this is a bit of a hack (renderDfd and setTimeout) in order to get synthetic select to do the right thing.
                //TODO synthetic select control should allow disabled as option on instantiation, rather than depending on disable() method
                this.renderDfd.done(function(){
                    setTimeout(function(){
                        if(!this.model.entity.isNew() && !this.options.isClone){
                            this.children.appSelect.childList[0].disable();
                            this.children.entityName.childList[0].disable();
                        }else{
                            this.children.appSelect.childList[0].enable();
                            this.children.entityName.childList[0].enable();
                        }
                    }.bind(this),0);
                }.bind(this));
            },

            setIndexedExtractions: function() {
                var indexedExtraction = this.model.entity.entry.content.get('INDEXED_EXTRACTIONS');
                this.children.indexedExtractions.childList[0].setValue(indexedExtraction);
            },

            setCategoryItems: function() {
                var items = this.collection.sourcetypesCategories.getCategories();
                this.children.categorySelect.childList[0].setItems(items);
                this.children.categorySelect.childList[0].setValue(this.model.entity.entry.content.get('category') || _('Custom').t());
            },

            setAppItems: function() {
                var items = this.buildAppItems();
                this.children.appSelect.childList[0].setItems(items);
                this.children.appSelect.childList[0].setValue(this.model.entity.entry.acl.get('app') || 'search');
            },

            buildAppItems: function() {
                var items = [];
                this.collection.appLocals.each(function(app){
                    items.push( {
                        value: app.entry.get('name'),
                        label: app.entry.content.get('label') //do not translate app names
                    });
                });
                items.push( {value: 'system', label: 'system'} );
                return _.sortBy(items, function(item){
                    return (item.label||'').toLowerCase();
                });
            },

            updateModel: function() {
                var sourceTypeName = this.model.entity.entry.get('name');
                if (_.isUndefined(sourceTypeName)) {
                    this.model.entity.entry.set({name:''}, {silent:true});
                } else {
                    this.model.entity.set('name', sourceTypeName);
                }

                if (this.options.isClone){
                    this.model.entity.set('id', undefined);
                    this.model.entity.set('ui.metric_transforms.schema_name','');
                }
            },

            updateIndexedExtractions: function() {
                var newItems = this.children.indexedExtractions.options.controlOptions.items;
                var selectedCategory = this.model.entity.entry.content.get('category');
                var isCategoryLogToMetrics = selectedCategory === 'Log to Metrics';
                if (isCategoryLogToMetrics) {
                    newItems.push({value: 'field_extraction'});
                } else {
                    var fieldExtractionIndex = newItems.map(function(e) {
                        return e.value;
                    }).indexOf('field_extraction');
                    if (fieldExtractionIndex >= 0) {
                        newItems.splice(fieldExtractionIndex, 1);
                    }
                }
                var indexedExtractionList = this.children.indexedExtractions.childList[0];
                indexedExtractionList.setItems(newItems);
                if (indexedExtractionList._value === 'field_extraction') {
                    isCategoryLogToMetrics ? this.showIndexedExtractionWarning() : this.hideIndexedExtractionWarning();
                }
            },

            updateIndexedExtractionWarning: function() {
                var indexedExtraction = this.model.entity.entry.content.get('INDEXED_EXTRACTIONS');
                indexedExtraction === 'field_extraction' ? this.showIndexedExtractionWarning() : this.hideIndexedExtractionWarning();
            },

            showIndexedExtractionWarning: function() {
                this.$('.extractions-warning').show();
            },

            hideIndexedExtractionWarning: function() {
                this.$('.extractions-warning').hide();
            },

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                var title = (this.options.isNew || this.options.isClone) ? _('Create Source Type').t() : (_('Edit Source Type: ').t() + ' ' + _.escape(this.model.entity.entry.get('name')));
                this.$(Modal.HEADER_TITLE_SELECTOR).html(title);
                this.$(Modal.BODY_SELECTOR).show();
                this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
                this.$(Modal.BODY_FORM_SELECTOR).html(_(this.dialogFormBodyTemplate).template({}));
                this.children.flashMessagesView.render().appendTo(this.$(".flash-messages-view-placeholder"));
                if (this.options.isNew || this.options.isClone) {
                    this.children.entityName.render().appendTo(this.$(".name-placeholder"));
                }
                this.children.entityDesc.render().appendTo(this.$(".desc-placeholder"));

                if (this.canUseApps) {
                    this.children.appSelect.render().appendTo(this.$(".appselect-placeholder"));
                }

                this.children.categorySelect.render().appendTo(this.$(".category-placeholder"));
                this.children.indexedExtractions.render().appendTo(this.$(".extractions-placeholder"));
                this.children.settingsTabControls.render().appendTo(this.$(".settings-placeholder"));
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);
                this.$(Modal.FOOTER_SELECTOR).append(this.children.waitSpinner.render().el);
                this.children.waitSpinner.start();
                this.$('.shared-waitspinner').hide();

                this.$('.accordion-group').find('.accordion-inner').show();
                this.$('.icon-accordion-toggle').addClass('icon-triangle-down-small');
                this.$('.accordion-group').last().removeClass('active').find('.accordion-inner').hide();
                this.$('.icon-accordion-toggle').last().removeClass('icon-triangle-down-small');
                this.$('.copyToClipboardDialog textarea').removeProp('readonly');
                this.updateIndexedExtractionWarning();

                this.renderDfd.resolve();

                return this;
            },

            dialogFormBodyTemplate: '\
                <div class="flash-messages-view-placeholder"></div>\
                <div class="name-placeholder"></div>\
                <div class="desc-placeholder"></div>\
                <div class="appselect-placeholder"></div>\
                <div class="category-placeholder"></div>\
                <div class="extractions-placeholder"></div>\
                <div class="extractions-warning">\
                    <div class="extractions footer"><%- _("Performs simple key=value field extractions based on a default regular expression.").t() %></div>\
                    <a class="extractions learn-more-extractions-warning external" href="/help?location=settings.sourcetype.fieldextraction" target="_blank"><%- _("Learn More").t() %></a>\
                </div>\
                <div class="settings-placeholder"></div>\
            '
        });
    });
