define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'models/services/search/IntentionsParser',
    'views/shared/Modal',
    'views/shared/controls/ControlGroup',
	'views/shared/basemanager/SearchableDropdown/Master',
    'views/shared/FlashMessages',
    'views/shared/reportcontrols/dialogs/summaryindexingdialog/AddFieldsSection',
    'views/shared/reportcontrols/dialogs/summaryindexingdialog/Master.pcss',
    'views/shared/reportcontrols/dialogs/schedule_dialog/Master',
    'splunk.util',
    'uri/route',
    'util/string_utils'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        IntentionsParserModel,
        Modal,
        ControlGroup,
		SearchableDropdown,
        FlashMessage,
        AddFieldsSection,
        css,
        ScheduleDialog,
        splunkUtil,
        route,
        stringUtils
    ) {
    var FIELD_PREFIX = 'action.summary_index.';
    return Modal.extend({
        /**
        * @param {Object} options {
        *       model: {
        *           report: <models.Report>,
        *           application: <models.Application>,
        *           user: <models.service.admin.user>,
        *           appLocal: <models.services.AppLocal>,
        *           controller: <Backbone.Model> (Optional),
        *       }
        *       collection: {
        *           indexes {collections/services/data/Indexes}
        *       }
        * }
        */
        moduleId: module.id,
        className: Modal.CLASS_NAME + ' ' + Modal.CLASS_MODAL_WIDE,
        events: $.extend({}, Modal.prototype.events, {
            'click .save.modal-btn-primary': function(e) {

                var summaryIndexOn = this.model.inmem.entry.content.get('action.summary_index');

                // update actions field with summary_index presence
                var untrimmedActions = this.model.inmem.entry.content.get('actions');
                untrimmedActions = untrimmedActions.split(',');
                var actions = [];
                for (var i = 0; i < untrimmedActions.length; i++) {
                    actions.push(untrimmedActions[i].trim());
                }
                if (actions.indexOf('summary_index') === -1) {
                    if (summaryIndexOn) {
                        actions.push('summary_index');
                    }
                } else {
                    if (!summaryIndexOn) {
                        actions.splice(actions.indexOf('summary_index'), 1);
                    }
                }
                actions = actions.join(',');
                this.model.inmem.entry.content.set('actions', actions);

                if (summaryIndexOn) {
                    // update existing fields
                    _.each(_.keys(this.filterToExistingFields()), function(key) {
                        var slicedKey = key.slice(FIELD_PREFIX.length);
                        if (this.model.fieldList.has(slicedKey)) {
                            this.model.inmem.entry.content.set(key, this.model.fieldList.attributes[slicedKey]);
                        } else {
                            // If user deleted the field, set the key to empty, and the field will be deleted.
                            this.model.inmem.entry.content.set(key, '');
                        }
                    }.bind(this));

                    // add in new fields
                    _.each(_.keys(this.model.fieldList.attributes), function(key) {
                        this.model.inmem.entry.content.set(FIELD_PREFIX + key, this.model.fieldList.get(key));
                    }.bind(this));
                }

                this.model.inmem.save({}, {
                    success: function(model, response) {
                        this.model.report.fetch();
                        this.remove();
                        if (this.model.controller) {
                            this.model.controller.trigger('refreshEntities');
                        }
                    }.bind(this)
                });
                e.preventDefault();
            },
            'click .modal-btn-primary.schedule-report': function(e) {
                this.hide();
                var scheduleDialog = new ScheduleDialog({
                    model: {
                        report: this.model.report,
                        application: this.model.application,
                        user: this.model.user,
                        appLocal: this.model.appLocal,
                        controller: this.model.controller
                    },
                    onHiddenRemove: true
                });

                scheduleDialog.render().appendTo($("body"));
                scheduleDialog.show();

                e.preventDefault();
            }
        }),

        initialize: function(options) {
            Modal.prototype.initialize.apply(this, arguments);

            this.model = {
                report: this.model.report,
                inmem: this.model.report.clone(),
                application: this.model.application,
                user: this.model.user,
                controller: this.model.controller
            };

            this.model.intentionsParser = new IntentionsParserModel();
            this.intentionsParserDeferred = this.model.intentionsParser.fetch({
                data:{
                    q:this.model.report.entry.content.get('search'),
                    timeline: false,
                    app: this.model.application.get('app'),
                    owner: this.model.application.get('owner'),
                    parse_only: true,
                    ignore_parse_error: true
                }
            });

            this.children.flashMessage = new FlashMessage({ model: this.model.inmem });

            this.children.name = new ControlGroup({
                controlType: 'Label',
                controlOptions: {
                    modelAttribute: 'name',
                    model: this.model.inmem.entry
                },
                label: _('Report').t()
            });

            var summaryIndexingHelpLink = route.docHelp(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            'learnmore.summaryindexing'
            );

            this.children.summarize = new ControlGroup({
                controlType: 'SyntheticCheckbox',
                controlOptions: {
                    modelAttribute: 'action.summary_index',
                    model: this.model.inmem.entry.content
                },
                label: _('Enable Summary Indexing').t(),
                help: _('Summary indexing is an alternative to report acceleration. Only use it if report acceleration does not fit your use case. ').t() +
                      '<a href="' + _.escape(summaryIndexingHelpLink) + '" target="_blank">' + _("Learn More").t() + ' <i class="icon-external"></i></a>'
            });

            this.summaryIndexesSelect = new SearchableDropdown({
                modelAttribute: 'action.summary_index._name',
                model: this.model.inmem.entry.content,
				multiSelect: false,
                toggleClassName: 'btn',
                popdownOptions: {
                    attachDialogTo: '.modal:visible',
                    scrollContainer: '.modal:visible .modal-body:visible'
                },
				collection: {search: this.collection.indexes.clone(), listing: this.collection.indexes}
            });

            this.children.summaryIndexes = new ControlGroup({
                controls: [this.summaryIndexesSelect],
                label: _('Select the summary index').t(),
                help: _('Only indexes you can write to are listed.').t()
            });

            var existingFields = this.filterToExistingFields();
            var choppedFields = {};
            _.each(_.keys(existingFields), function(key) {
                choppedFields[key.slice(FIELD_PREFIX.length)] = existingFields[key];
            }.bind(this));

            this.model.fieldList = new Backbone.Model(choppedFields);
            this.children.addFields = new AddFieldsSection({
                model: {
                    fieldList: this.model.fieldList
                }
            });

            this.model.inmem.entry.content.on('change:action.summary_index', function() {
                if (this.model.inmem.entry.content.get('action.summary_index')) {
                    this.showSummaryOptions();
                } else {
                    this.hideSummaryOptions();
                }
            }, this);
        },

        filterToExistingFields: function() {
            var filteredKeys = this.model.inmem.entry.content.keys().filter(function(key) {
                                    return stringUtils.strStartsWith(key, FIELD_PREFIX);
                               });
            var defaultFields = ['action.summary_index._name', 'action.summary_index.inline',
                                 'action.summary_index.command', 'action.summary_index.ttl',
                                 'action.summary_index.hostname', 'action.summary_index.track_alert',
                                 'action.summary_index.maxresults', 'action.summary_index.maxtime'];
            return _(this.model.inmem.entry.content.omit(defaultFields)).pick(filteredKeys);
        },

        showSummaryOptions: function() {
            this.children.summaryIndexes.$el.show();
            if(this.model.inmem.entry.content.get('action.summary_index._name') === '') {
                this.model.inmem.entry.content.set('action.summary_index._name','summary');
            }
            this.children.addFields.$el.show();
        },

        hideSummaryOptions: function() {
            this.children.summaryIndexes.$el.hide();
            this.children.addFields.$el.hide();
        },

        render: function() {
            this.$el.html(Modal.TEMPLATE);

            this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Edit Summary Index').t());

            this.children.flashMessage.render().prependTo(this.$(Modal.BODY_SELECTOR));

            this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);

            $.when(this.intentionsParserDeferred).then(function(){
                var isScheduled = this.model.report.entry.content.get('is_scheduled');
                if (isScheduled) {

                    if(!(this.model.intentionsParser.has('hasDFSearch') && this.model.intentionsParser.get('hasDFSearch')))
                    {
                        this.children.name.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));
                        this.children.summarize.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));
                        this.children.summaryIndexes.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));
                        this.children.addFields.render().appendTo(this.$(Modal.BODY_FORM_SELECTOR));

                        if (this.model.inmem.entry.content.get('action.summary_index')) {
                            this.showSummaryOptions();
                        } else {
                            this.hideSummaryOptions();
                        }
                        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                        this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="save btn btn-primary modal-btn-primary pull-right">' + _('Save').t() + '</a>');
                    }
                    else {
                        this.$(Modal.BODY_FORM_SELECTOR).append('<div>' + _('Summary indexing cannot be enabled for' +
                                ' a Data Fabric Search.').t() + '</div>');
                        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                        this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn btn-primary modal-btn-primary pull-right schedule-report">' + _('Schedule Report').t() + '</a>');
                    }
                } else {
                    this.$(Modal.BODY_FORM_SELECTOR).append('<div>' + _('This report must be scheduled before summary indexing can be enabled.').t() + '</div>');
                    this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                    this.$(Modal.FOOTER_SELECTOR).append('<a href="#" class="btn btn-primary modal-btn-primary pull-right schedule-report">' + _('Schedule Report').t() + '</a>');
                }
            }.bind(this),function(){
                this.$(Modal.BODY_FORM_SELECTOR).append('<div>' + _('This saved search cannot perform summary indexing because it has a malformed search.').t() + '</div>');
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_DONE);
            }.bind(this));

            return this;
        }
    });
});
