define([
    'underscore',
    'jquery',
    'backbone',
    'module',
    'views/Base',
    'views/shared/FlashMessages',
    'views/shared/controls/ControlGroup',
    'views/shared/controls/SyntheticSelectControl',
    'models/knowledgeobjects/Sourcetype',
    'splunk.util'
],
function(
    _,
    $,
    Backbone,
    module,
    Base,
    FlashMessages,
    ControlGroup,
    SyntheticSelectControl,
    SourcetypeModel,
    splunkUtil
){
    return Base.extend({
        moduleId: module.id,
        initialize: function(options) {
            Base.prototype.initialize.apply(this, arguments);

            this.canUseApps = this.model.user.canUseApps();

            this.children.flashMessages = new FlashMessages({
                helperOptions: {
                    postProcess: function(errors) {
                        if(errors && errors.length > 0 ){
                            var realErrors = [];
                            for(var i = 0, len = errors.length;i<len;i++){
                                var error = errors[i];
                                if(error && error.get){
                                    var message = error.get('html') || '';
                                    if(message.indexOf('An object with name=') < 0){
                                        realErrors.push(error);
                                    }
                                }
                            }
                            return realErrors;
                        }
                        return errors;
                    }
                }
            });

            this.children.sourcetypeName = new ControlGroup({
                label: _("Name").t(),
                controlType: 'Text',
                controlOptions: {
                    model: this.model.sourcetypeModel.entry,
                    modelAttribute: 'name',
                    className:'fieldName',
                    save: false,
                    updateModel: false
                }
            });

            this.children.description = new ControlGroup({
                label: _('Description').t(),
                controlType: 'Text',
                controlOptions: {
                    model: this.model.sourcetypeModel.entry.content,
                    modelAttribute: 'description',
                    additionalClassNames: 'fieldDesc',
                    save: false,
                    updateModel: false
                }
            });

            var categoryItems = this.buildCategoryItems();
            var selectedCategory = this.model.sourcetypeModel.entry.content.get('category');
            if (selectedCategory !== 'Log to Metrics') {
                var logToMetricsIndex = categoryItems.map(function(e) {
                    return e.value;
                }).indexOf('Log to Metrics');
                if (logToMetricsIndex >= 0) {
                    categoryItems.splice(logToMetricsIndex, 1);
                }
            }
            this.children.categorySelect = new ControlGroup({
                label: _('Category').t(),
                controlType: 'SyntheticSelect',
                controlOptions: {
                    model: this.model.sourcetypeModel.entry.content,
                    modelAttribute: 'category',
                    items: categoryItems,
                    additionalClassNames: 'fieldCategorySelect',
                    toggleClassName: 'btn',
                    popdownOptions: {
                        attachDialogTo: 'body'
                    },
                    save: false,
                    updateModel: false
                }
            });

            var appItems = this.buildAppItems();
            this.children.appSelect = new ControlGroup({
                label: _('App').t(),
                controlType: 'SyntheticSelect',
                controlOptions: {
                    model: this.model.sourcetypeModel.entry.acl,
                    modelAttribute: 'app',
                    items: appItems,
                    additionalClassNames: 'fieldAppSelect',
                    toggleClassName: 'btn',
                    popdownOptions: {
                        attachDialogTo: 'body'
                    },
                    save: false,
                    updateModel: false
                }
            });

            //TODO could not find more elegant way to set default values.
            var currentName = this.model.sourcetypeModel.entry.get('name');
            if(currentName === 'default' || currentName === '__auto__learned__'){
                this.children.sourcetypeName.childList[0].setValue('');
                this.children.categorySelect.childList[0].setValue('Custom');

                if(!this.canUseApps){
                    //if can't use apps, default to search namespace
                    this.children.appSelect.childList[0].setValue('search');
                }else{
                    //set app namespace to current app context in URL
                    this.children.appSelect.childList[0].setValue(this.model.application.get('app'));
                }
            }

        },
        buildAppItems: function(){
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
        buildCategoryItems: function(){
            return this.collection.sourcetypesCollection.getCategories();
        },
        save: function(done) {
            var selectedCategory = this.children.categorySelect.childList[0].getValue();
            var isCategoryLogToMetrics = selectedCategory === 'Log to Metrics';
            if (!isCategoryLogToMetrics) {
                this.saveSourcetype(isCategoryLogToMetrics, done);
                return;
            }
            var sourcetypeModel = this.model.sourcetypeModel;
            var metricTransformsModel = this.model.metricTransformsModel;
            this.children.flashMessages.register(metricTransformsModel);

            var saveOptions = {
                sourcetypeModel : sourcetypeModel,
                data: this.getAppOwner()
            };
            var saveDfd = metricTransformsModel.save(null, saveOptions);
            if (saveDfd) {
                saveDfd.done(function() {
                    // Remove timeout after SPL-157987 is fixed
                    setTimeout(function() {
                        this.saveSourcetype(isCategoryLogToMetrics, done);
                    }.bind(this), 2000);
                }.bind(this))
                .fail(function() {
                    done();
                }.bind(this));
            }
        },

        getAppOwner: function () {
            return {
                app: this.children.appSelect.childList[0].getValue(),
                owner: 'nobody'
            };
        },

        saveSourcetype: function(isCategoryLogToMetrics, done) {
            var self = this;

            var appOwner = this.getAppOwner();
            var app = appOwner.app;
            var owner = appOwner.owner;
            var saveOptions = {
                data: appOwner
            };

            var schemaName = this.model.metricTransformsModel.get('name') || this.model.sourcetypeModel.get('ui.metric_transforms.schema_name');
            if (schemaName && (schemaName.indexOf('metric-schema:') >= 0)) {
                schemaName = schemaName.split('metric-schema:')[1];
            }
            if (!isCategoryLogToMetrics && schemaName) {
                this.model.sourcetypeModel.set('ui.metric_transforms.schema_name', '');
            } else if (schemaName) {
                this.model.sourcetypeModel.set({'ui.metric_transforms.schema_name': 'metric-schema:' + schemaName});
            }

            var propsToSave = this.model.sourcetypeModel.getExplicitProps();

            propsToSave.pulldown_type = 'true';
            propsToSave.description = this.children.description.childList[0].getValue();
            propsToSave.category = this.children.categorySelect.childList[0].getValue();

            var newModel = new SourcetypeModel();
            var sourcetypeName = this.children.sourcetypeName.childList[0].getValue();
            newModel.entry.set('name', sourcetypeName);
            newModel.entry.acl.set('app', app);
            newModel.entry.content.set(propsToSave);
            newModel.set('name', sourcetypeName);

            this.children.flashMessages.register(newModel);
            if (!newModel.entry.isValid(true)) {
                done();
                return;
            }

            var saveDfd = newModel.save({}, saveOptions);
            if (saveDfd) {
                saveDfd.done(function(){
                    var schemaNameExists = !_.isEmpty(schemaName);
                    if (!isCategoryLogToMetrics && schemaNameExists) {
                        this.model.metricTransformsModel.deleteMetricTransform(schemaName, this.model.sourcetypeModel);
                    }
                    self.onSaveDone.apply(self, [newModel]);
                    done();
                }.bind(this))
                .fail(function(jqXhr){
                    if (parseInt(jqXhr.status, 10) === 409) {
                        //409 is splunkd telling us we have name conflict.
                        self.confirmOverwrite(sourcetypeName, function(confirmed){
                            if (!confirmed) {
                                done();
                                return;
                            }
                            //TODO must overwrite with the same app TODO
                            var fullId = ['/servicesNS', encodeURIComponent(owner), encodeURIComponent(app), 'saved/sourcetypes', encodeURIComponent(sourcetypeName)].join('/');
                            newModel
                                .set({
                                    id: fullId
                                })
                                .save({data:{
                                    app: app,
                                    owner: owner
                                }}).done(function() {
                                    self.onSaveDone.apply(self, [newModel]);
                                    done();
                                }).fail(function() {
                                    this.model.metricTransformsModel.deleteMetricTransform(schemaName, this.model.sourcetypeModel);
                                    done();
                                }.bind(this));
                        });
                    } else {
                        if (isCategoryLogToMetrics) {
                            this.model.metricTransformsModel.deleteMetricTransform(schemaName, this.model.sourcetypeModel);
                        }
                        done();
                    }
                }.bind(this));
            }
        },
        onSaveDone: function(newModel){
            var id = newModel && newModel.entry && newModel.entry.get('name');
            this.trigger('savedSourcetype', id);
        },
        confirmOverwrite: function(name, callback){
            this.model.previewPrimer.trigger('confirmOverwrite', name, callback);
        },
        render: function() {
            this.$el.append(this.children.flashMessages.render().el);
            this.$el.append(this.children.sourcetypeName.render().el);
            this.$el.append(this.children.description.render().el);
            this.$el.append(this.children.categorySelect.render().el);
            this.$el.append(this.children.appSelect.render().el);

            if(!this.canUseApps){
                this.children.appSelect.$el.hide();
            }

            return this;
        }
    });
});
