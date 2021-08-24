/**
 * Master View that is responsible for loading Field Extractor page components,
 * depending on whatever automatic wizard step/manual mode the page is in.
 * Instantiated by FieldExtractorRouter.
 */
define([
            'jquery',
            'underscore',
            'module',
            'models/Base',
            'models/services/data/props/Extraction',
            'models/services/configs/Transforms',
            'models/knowledgeobjects/Sourcetype',
            'models/search/Job',
            'collections/Base',
            'collections/services/authorization/Roles',
            'views/Base',
            './ManualExtractionEditor',
            './ExistingExtractionsList',
            './MasterEventViewer',
            './MasterEventEditor',
            './MasterEventDelimEditor',
            './ExtractionViewer',
            './SaveExtractionsView',
            './CounterExampleEditor',
            './ConfirmationView',
            'views/shared/knowledgeobjects/SourcetypeMenu',
            'views/shared/dataenrichment/preview/RexPreviewViewStack',
            'views/shared/dataenrichment/preview/PreviewJobController',
            'views/shared/dataenrichment/preview/RegexGeneratorController',
            'views/shared/controls/ControlGroup',
            'views/shared/controls/SyntheticSelectControl',
            'views/shared/controls/SyntheticRadioControl',
            'views/shared/controls/TextControl',
            'views/shared/controls/StepWizardControl',
            'views/shared/Sidebar',
            'views/shared/FlashMessages',
            'splunk.util',
            'util/field_extractor_utils',
            'util/splunkd_utils',
            'util/string_utils',
            'uri/route',
            'views/shared/pcss/data-enrichment.pcss',
            './FieldExtractorMaster.pcss',
            'bootstrap.tooltip'  // package without return type
        ],
        function(
            $,
            _,
            module,
            BaseModel,
            Extraction,
            TransformModel,
            Sourcetype,
            Job,
            BaseCollection,
            RolesCollection,
            BaseView,
            ManualExtractionEditor,
            ExistingExtractionsList,
            MasterEventViewer,
            MasterEventEditor,
            MasterEventDelimEditor,
            ExtractionViewer,
            SaveExtractionsView,
            CounterExampleEditor,
            ConfirmationView,
            SourcetypeMenu,
            RexPreviewViewStack,
            PreviewJobController,
            RegexGeneratorController,
            ControlGroup,
            SyntheticSelectControl,
            SyntheticRadioControl,
            TextControl,
            StepWizardControl,
            Sidebar,
            FlashMessages,
            splunkUtils,
            fieldExtractorUtils,
            splunkdUtils,
            stringUtils,
            route,
            cssDataEnrichment,
            css
            /* undefined */
        ) {

    return BaseView.extend({

        moduleId: module.id,

        className: 'field-extractor-master',

        SIDEBAR_WIDTH: 350,
        REGEX_MODE: 'regex',
        DELIM_MODE: 'delim',

        events: {
            'click .view-extractions-button:not(.disabled)' : function(e) {
                // Open sidebar that displays existing saved extractions.
                e.preventDefault();
                this._createSidebar();
            },
            'click .content-header .manual-mode-button': function(e) {
                // Enter manual editor from wizard/automatic mode.
                e.preventDefault();
                this.setManualMode();
            },
            'click .btn-regex': function(e) {
                e.preventDefault();
                this.setMethod(this.REGEX_MODE);
                this.children.masterEventViewer.render();
                this._refreshExistingExtractionsButton();
                this.$('.view-all-extractions-button-container').show();
            },
            'click .btn-delim': function(e) {
                e.preventDefault();
                this.setMethod(this.DELIM_MODE);
                this._hideExistingExtractions();
                this.children.masterEventViewer.render();
                this.$('.view-all-extractions-button-container').hide();
            },
            'click .return-automatic-mode': function(e) {
                // Return to wizard/automatic mode from manual editor.
                // This button is only displayed if the user has not manually edited the regex.
                e.preventDefault();
                this.cleanupManualMode();
            },
            'click .return-manual-page': function(e) {
                // Return to manual editor from SaveExtractionsView - user is bailing out from saving the extraction.
                e.preventDefault();
                // In case regex has not been manually edited,
                // allow user to return the most recently visited wizard step in automatic mode.
                this.model.state.set({ mode: this.lastAutomaticMode });
                this._setupManualView();
                this.$('.return-manual-page').hide();
                this.$('.manual-save-button').hide();
            },
            'click .content-header .preview-in-search-link': function(e) {
                e.preventDefault();
                if(!$(e.currentTarget).hasClass('disabled')) {
                    this._handlePreviewInSearch();
                }
            },
            'click .manual-save-button': function(e) {
                e.preventDefault();
                this._validateAndSaveExtraction();
            },
            'keypress' : function(event) {
                var ENTER_KEY = 13;
                if (event.which === ENTER_KEY) {
                    var source = this.$('.source-wrapper .control input').val();
                    if (source) {
                        this.model.state.set({ source: source });
                    }
                }
            }
        },
        /**
         * @constructor
         *
         * @param options {Object} {
         *     sourcetype {String} the name of the current sourcetype
         *     sid (optional) the sid of an existing search job whose results we want to extract fields from
         *     model: {
         *         application <models.Application>
         *         user <models.services.authentication.Users>
         *         extraction <models.services.data.props.Extraction>
         *     }
         *     collection: {
         *         extractions <collections.services.data.props.Extractions>
         *         sourcetypes <collections.knowledgeobjects.Sourcetypes>
         *         roles <collections.services.authorization.Roles>
         *     }
         * }
         *
         */
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.environment = this.model.serverInfo.isLite() ? 'Light' : 'Enterprise';

            this.model.state = new BaseModel({
                type: 'sourcetype',
                source: '',
                sourcetype: this.options.sourcetype,
                sampleSize: { head: 1000 },
                inputField: '_raw',
                regex: this.model.extraction.isNew() ? '' : this.model.extraction.entry.content.get('value'),
                interactiveMode: fieldExtractorUtils.INTERACTION_MODE,
                filter: '',
                clustering: fieldExtractorUtils.CLUSTERING_NONE,
                eventsView: fieldExtractorUtils.VIEW_ALL_EVENTS,
                mode: fieldExtractorUtils.SELECT_SAMPLE_MODE,
                masterEvent: this.options.masterEvent,
                examples: [],
                counterExamples: [],
                sampleEvents: [],
                errorState: false, //used to check server validation errors
                regexGenErrorState: false, //used for regex generator promise errors
                useSearchFilter: true,
                hasSid: false,
                existingExtractions: [],
                existingSampleExtractions: []
            });
            this.model.searchJob = new Job({}, { delay: 1000, processKeepAlive: true });
            if (this.options.sid) {
                this.model.state.set({type: 'sourcetype'});
                this.model.state.set({hasSid: true});
            }
            this.model.transform = new TransformModel();
            if (this.options.sourcetype) {
                this.model.state.set({type: 'sourcetype'});
            }
            if (this.options.existingExtractions) {
                this.model.state.set({type: 'sourcetype'});
                this.model.state.set({existingExtractions: this.options.existingExtractions});
                this._tryToShowExistingExtractions();
            }

            this.collection.wizardSteps = new BaseCollection([
                {
                    value: fieldExtractorUtils.SELECT_SAMPLE_MODE,
                    label: _('Select Sample').t(),
                    nextLabel: _('Next').t(),
                    showPreviousButton: false
                },
                {
                    value: fieldExtractorUtils.SELECT_METHOD_MODE,
                    label: _('Select Method').t(),
                    enabled: !!this.model.state.get('masterEvent'),
                    nextLabel: _('Next').t()
                },
                {
                    value: fieldExtractorUtils.SELECT_DELIM_MODE,
                    label: _('Rename Fields').t(),
                    enabled: (this.model.state.get('method') === this.DELIM_MODE),
                    visible: false,
                    nextLabel: _('Next').t()
                },
                {
                    value: fieldExtractorUtils.SELECT_FIELDS_MODE,
                    label: _('Select Fields').t(),
                    enabled: (this.model.state.get('method') === this.REGEX_MODE),
                    nextLabel: _('Next').t()
                },
                {
                    value: fieldExtractorUtils.VALIDATE_FIELDS_MODE,
                    label: _('Validate').t(),
                    enabled: ((this.model.state.get('examples') || []).length > 0),
                    visible: false,
                    nextLabel: _('Next').t()
                },
                {
                    value: fieldExtractorUtils.SAVE_FIELDS_MODE,
                    label: _('Save').t(),
                    enabled: (((this.model.state.get('examples') || []).length > 0) ||
                              (_(this.model.state.get('delimFieldNames')).keys().length > 0)),
                    nextLabel: _('Finish').t()
                },
                {
                    value: fieldExtractorUtils.CONFIRMATION_MODE,
                    label: '',
                    showPreviousButton: false,
                    showNextButton: false
                }
            ]);
            // If certain values are pre-populated in the state model, make sure to remove the skipped steps from
            // the wizard and set the correct mode in the state model.
            if(this.model.state.has('sourcetype')) {
                // Update the existing extractions if the sourcetype is already set.
                this._refreshExtractions();
            }
            if(this.model.state.has('masterEvent')) {
                this.collection.wizardSteps.remove(
                    this.collection.wizardSteps.findWhere({ value: fieldExtractorUtils.SELECT_SAMPLE_MODE })
                );
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.SELECT_METHOD_MODE })
                    .set({ showPreviousButton: false });
                this.model.state.set({ mode: fieldExtractorUtils.SELECT_METHOD_MODE });
                // Update the existing extractions if the masterEvent is already set.
                this._refreshExtractions();
            }

            this._createComponents();
            this.listenTo(this.model.searchJob, 'serverValidated', _.bind(function(noValidationErrors, searchJobContext, errorMessages) {
                // Set state model's error state attribute if search job returns incomplete and with (and creates page-wide flash message)
                if(!noValidationErrors){
                    this.model.state.set('errorState', true);
                }else{
                    this.model.state.set('errorState', false);
                }
            }, this));
            this.listenTo(this.model.state, 'change:type', function() {
                this.model.state.set('masterEvent', '');
                this._refreshExtractionViews();
            });
            this.listenTo(this.model.state, 'change:source', function() {
                // Refresh the existing extracted fields when the source is updated.
                this._forceRefreshExtractions().done(_(function() {
                    this.children.regexGenerationController.reset();
                    this._syncStateModelFromController();
                    this._refreshExtractionViews();
                }).bind(this));
            });
            this.listenTo(this.model.state, 'change:sourcetype', function() {
                // Refresh the existing extracted fields when the sourcetype is updated.
                this._forceRefreshExtractions().done(_(function() {
                    // Clear any previous extraction information when the sourcetype changes (SPL-89136)
                    this.children.regexGenerationController.reset();
                    this._syncStateModelFromController();
                    this._refreshExtractionViews();
                }).bind(this));
            });
            this.listenTo(this.model.state, 'change:masterEvent', function() {
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.SELECT_METHOD_MODE })
                    .set({ enabled: !!this.model.state.get('masterEvent') });
                if (this.model.state.get('masterEvent')) {
                    this._refreshPreview();
                }
            });
            this.listenTo(this.model.state, 'change:examples', function() {
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.VALIDATE_FIELDS_MODE })
                    .set({ enabled: (this.model.state.get('examples') || []).length > 0 });
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.SAVE_FIELDS_MODE })
                    .set({ enabled: ((this.model.state.get('examples') || []).length > 0) });
            });
            this.listenTo(this.model.state, 'change:method', function() {
                var method = this.model.state.get('method');
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.SELECT_DELIM_MODE })
                    .set({ visible: (method === this.DELIM_MODE),
                           enabled: true });
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.SELECT_FIELDS_MODE })
                    .set({ visible: (method === this.REGEX_MODE),
                           enabled: true });
                this.collection.wizardSteps
                    .findWhere({ value: fieldExtractorUtils.VALIDATE_FIELDS_MODE })
                    .set({ visible: (method === this.REGEX_MODE),
                           enabled: (this.model.state.get('examples') || []).length > 0 });
                this._updateMethodButtons();
                $('html,body').animate({scrollTop: "0px"}, 300);
            });
            this.listenTo(this.model.state, 'change:delimType', function(model, delimType) {
                if (this.model.state.get('mode') === fieldExtractorUtils.SELECT_DELIM_MODE) {
                    if (delimType === 'custom') {
                        if (this.model.state.get('delim') && !_.isEmpty(this.model.state.get('delim'))) {
                            this.applyDelim(this.model.state.get('delim'));
                        }
                        this.children.delimiterCustom.$el.show();
                        return;
                    } else {
                        this.children.delimiterCustom.$el.hide();
                    }
                }
                var delim = fieldExtractorUtils.DELIM_MAP[delimType];
                this.model.state.set('delim', delim);
            });
            this.listenTo(this.model.state, 'change:delim', function(model, delim) {
                if (this.model.state.get('mode') === fieldExtractorUtils.SELECT_DELIM_MODE) {
                    this.applyDelim(delim);
                    if (this.$('.content-body').is(':hidden')) {
                        this.children.previewView.detach();
                        this.children.previewView.appendTo(this.$('.content-body')).$el.show();
                        this.$('.content-body').show();
                    }
                    this.children.masterEventDelimEditor.appendTo(this.$('.content-header')).$el.show();
                    this.collection.wizardSteps
                        .findWhere({ value: fieldExtractorUtils.SAVE_FIELDS_MODE })
                        .set({ enabled: (_(this.model.state.get('delimFieldNames')).keys().length > 0) });
                }
            });
            this.listenTo(this.model.state, 'delimFieldNamesUpdated', function() {
                // When a field is named, update the regex, so that the results table is updated with new field names
                if (this.model.state.get('mode') === fieldExtractorUtils.SELECT_DELIM_MODE) {
                    this.applyDelim(this.model.state.get('delim'));
                    this.collection.wizardSteps
                        .findWhere({ value: fieldExtractorUtils.SAVE_FIELDS_MODE })
                        .set({ enabled: (_(this.model.state.get('delimFieldNames')).keys().length > 0) });
                }
            });
            this.listenTo(this.model.state, 'change:mode', function() {
                var currentMode = this.model.state.get('mode'),
                    previousMode = this.model.state.previous('mode');
                if(currentMode === fieldExtractorUtils.SELECT_SAMPLE_MODE
                    && previousMode === fieldExtractorUtils.SELECT_METHOD_MODE){
                    this.tempClearState();
                    // Set Select Fields mode visible, so wizard steps don't look bad.
                    this.collection.wizardSteps
                        .findWhere({ value: fieldExtractorUtils.SELECT_FIELDS_MODE })
                        .set({ visible: true });
                    this.children.stepWizardControl.updateNavButtons();
                }else if(currentMode === fieldExtractorUtils.SELECT_METHOD_MODE
                    && previousMode === fieldExtractorUtils.SELECT_SAMPLE_MODE) {
                    // we are returning to this step after having gone backwards
                    if(this.cachedStateModel) {
                        var typeHasChanged = this.cachedStateModel.type !== this.model.state.get('type'),
                            sourcetypeHasChanged = this.cachedStateModel.sourcetype !== this.model.state.get('sourcetype'),
                            sourceHasChanged = this.cachedStateModel.source !== this.model.state.get('source'),
                            masterEventHasChanged = this.cachedStateModel.masterEvent !== this.model.state.get('masterEvent'),
                            stateHasChanged = typeHasChanged || sourcetypeHasChanged || sourceHasChanged || masterEventHasChanged;
                        if(stateHasChanged) {
                            this.cachedStateModel = null; // proceed as usual. state is up to date.
                            this.cachedFieldsState = null; // Zero out cached field state if state is up to date.
                        }else{
                            // user has gone back but not made any changes. restore previous state.
                            this.restoreClearedState();
                            // When user entered select sample mode and established enabled state of the next mode (validate fields),
                            // the examples array was empty so validate fields mode's next button is disabled.
                            // Must update enabled state of next mode upon repopulating examples array.
                            this.children.stepWizardControl.updateNavButtons();
                        }
                    }
                } else if (currentMode === fieldExtractorUtils.SELECT_METHOD_MODE &&
                           (previousMode === fieldExtractorUtils.SELECT_FIELDS_MODE || previousMode === fieldExtractorUtils.SELECT_DELIM_MODE)) {
                    this.tempClearFields();
                } else if ((currentMode === fieldExtractorUtils.SELECT_FIELDS_MODE || currentMode === fieldExtractorUtils.SELECT_DELIM_MODE) &&
                           previousMode === fieldExtractorUtils.SELECT_METHOD_MODE) {
                    if (this.cachedFieldsState) {
                        if (this.cachedFieldsState.method !== this.model.state.get('method')) {
                            this.cachedStateModel = null; // proceed as usual. state is up to date.
                        } else {
                            // user has gone back but not made any changes. restore previous state.
                            this.restoreClearedFields();
                            // When user entered select method mode and established enabled state of next mode (validate or save),
                            // the examples array or delimFieldNames array was empty so the next step button was disabled.
                            // So we need to update wizard buttons after repopulating the appropriate info.
                            this.children.stepWizardControl.updateNavButtons();
                            // claral potentially rerender the mastereventdelimeditor
                        }
                    }
                }else if(currentMode === fieldExtractorUtils.VALIDATE_FIELDS_MODE) {
                    // When entering validate fields mode, set the view to all events so the user can find false
                    // positives (SPL-88792).
                    this.model.state.set({ eventsView: fieldExtractorUtils.VIEW_ALL_EVENTS });
                }
                this.cleanUpOldMode(this.model.state.previous('mode'));
                this._refreshExtractionViews();
            });
            this.listenTo(this.model.state, 'change:sampleEvents', function() {
                if(this.model.state.get('errorState') !== true){
                    this.children.previewView.setAddSamplesEnabled(this.model.state.get('sampleEvents').length < fieldExtractorUtils.SAMPLE_EVENT_LIMIT);
                }
            });

            this.listenTo(this.model.state, 'change:regex', function() {
                if (this.model.state.get('regex') && this.$('.content-body').is(':hidden')) {
                    this.children.previewView.detach();
                    this.children.previewView.appendTo(this.$('.content-body')).$el.show();
                    this.$('.content-body').show();
                }
                if(this.model.state.get('interactiveMode') === fieldExtractorUtils.NO_INTERACTION_MODE){
                    if(this.regexManuallyModified() || this.model.state.get('mode') === fieldExtractorUtils.SELECT_SAMPLE_MODE) {
                        this.$('.return-automatic-mode').hide();
                        this.children.manualExtractionEditor.$('.edit-regex-warning').hide();
                    }
                }
            });

            this.listenTo(this.model.state, 'change', function() {
                var whitelist = ['filter', 'regex', 'clustering', 'eventsView', 'sampleSize', 'useSearchFilter'],
                    shouldRefreshPreview = _(whitelist).any(function(attrName) {
                        return this.model.state.hasChanged(attrName);
                    }, this);

                if(shouldRefreshPreview) {
                    this._refreshPreview();
                }
            });
        },
        setManualMode: function() {
            // Store most recently visited wizard step to allow user to return to this step if re-entering automatic mode
            this.lastAutomaticMode = this.model.state.get('mode');
            this.model.state.set({ interactiveMode: fieldExtractorUtils.NO_INTERACTION_MODE });
            this.children.stepWizardControl.$el.hide();
            this._setupManualView();
            this.$('.page-header').attr('data-mode', 'manual');
        },
        _setupManualView: function() {
            this.cleanUpOldMode(this.model.state.get('mode'));
            this._refreshExtractionViews();
            if(this.model.extraction.isNew() && (!this.regexManuallyModified() || !this.model.state.get('regex'))) {
                this.$('.return-automatic-mode').show();
                this.children.manualExtractionEditor.$('.edit-regex-warning').show();
                this.$('.regex-editor-wrapper').find('textarea').focus();
            }
        },
        setMethod: function(method) {
            if (method === this.REGEX_MODE || method === this.DELIM_MODE) {
                this.model.state.set('method', method);
            }
        },
        cleanupManualMode: function(){
            this.model.state.set('interactiveMode', fieldExtractorUtils.INTERACTION_MODE);
            this.children.stepWizardControl.$el.show();
            this.children.manualExtractionEditor.cleanupState();
            this._cleanupManualView();
            this._refreshExtractionViews();
            this.$('.page-header').attr('data-mode', 'auto');
        },
        _cleanupManualView: function() {
            this.$('.select-sourcetype-header').detach();
            this.children.previewView.$el.detach().hide();
            this.children.manualExtractionEditor.$el.detach().hide();
            this.$('.return-automatic-mode').hide();
            this.children.manualExtractionEditor.$('.edit-regex-warning').hide();
            this.$('.view-all-extractions-button-container').hide();
        },
        cleanUpOldMode: function(mode) {
            // Teardown routines for each previous step of wizard mode as user goes to another step
            if(mode === fieldExtractorUtils.SELECT_SAMPLE_MODE) {
                this.$('.select-sample-header').detach();
                if (!this.options.sid && !this.options.sourcetype) {
                    this.children.typeDropDown.$el.detach().hide();
                    this.children.source.$el.detach().hide();
                }
                this.children.sourcetypeDropDown.$el.detach().hide();
                this.children.previewView.$el.detach().hide();
                this.children.masterEventViewer.detach();
            }
            else if(mode === fieldExtractorUtils.SELECT_METHOD_MODE) {
                this.$('.select-method-header').detach();
                if (this.model.state.get('method') === this.DELIM_MODE) {
                    this.$('.view-all-extractions-button-container').hide();
                }
            }
            else if(mode === fieldExtractorUtils.SELECT_FIELDS_MODE) {
                this.$('.select-fields-header').detach();
                this.children.extractionViewer.detach();
                this.children.masterEventEditor.$el.detach().hide();
                this.children.previewView.$el.detach().hide();
                this.$('.body-instructions').detach();
                if (this.$('.content-body').is(':hidden')) {
                    this.$('.content-body').css("display", "block");
                }
            }
            else if(mode === fieldExtractorUtils.SELECT_DELIM_MODE) {
                this.$('.select-fields-header').detach();
                this.children.extractionViewer.detach();
                this.children.masterEventViewer.detach();
                this.children.masterEventDelimEditor.$el.detach().hide();
                this.children.previewView.$el.detach().hide();
                this.$('.body-instructions').detach();
                if (this.$('.content-body').is(':hidden')) {
                    this.$('.content-body').css("display", "block");
                }
            }
            else if(mode === fieldExtractorUtils.VALIDATE_FIELDS_MODE) {
                this.$('.validate-fields-header').detach();
                this.children.previewView.$el.detach().hide();
                this.children.extractionViewer.detach();
                this.children.counterExampleEditor.$el.detach().hide();
                this.$('.view-all-extractions-button-container').hide();
            }
            else if(mode === fieldExtractorUtils.SAVE_FIELDS_MODE) {
                this.$('.save-extractions-header').detach();
                this.children.saveView.remove();
                this.$('.content-body').show();
                // When leaving the save mode, clear any errors that ocurred trying to save the extraction (SPL-89627).
                this.model.extraction.trigger('serverValidated', false, this.model.extraction);
                this.model.extraction.acl.trigger('serverValidated', false, this.model.extraction.acl);
                this.model.transform.trigger('serverValidated', false, this.model.transform);
            }
            else if(mode === fieldExtractorUtils.CONFIRMATION_MODE) {
                this.$('.confirmation-header').detach();
                this.children.confirmationView.$el.detach().hide();
            }
        },

        _tryToShowExistingExtractions: function() {
            var existingExtractions = this.model.state.get('existingExtractions');
            if (fieldExtractorUtils.containsNoOverlappingExtractions(existingExtractions)) {
                // No extraction overlaps, so set all existing extractions to hidden: false.
                _.each(existingExtractions, function(extraction) {
                    extraction.hidden = false;
                });
                this.model.state.set({extractionWarningOn: false});
            } else {
                this.model.state.set({extractionWarningOn: true});
            }
        },

        _hideExistingExtractions: function() {
            var existingExtractions = this.model.state.get("existingExtractions") || [];
            _.each(existingExtractions, function(extraction) {
                extraction.hidden = true;
            });
        },

        _refreshExistingExtractionsButton: function() {
            var warningOn = this.model.state.get('extractionWarningOn');
            this.$('.view-all-extractions-button-container').html(_(this.viewAllExtractionsTemplate).template({
                warningOn: warningOn
            }));
            if (warningOn) {
                var $warningIcon = this.$('.view-all-extractions-button-container .icon-alert');
                var tooltipText = _("There are existing extractions, however because they overlap, they can only be manually turned on.").t();
                $warningIcon.tooltip({ animation: false, title: tooltipText, container: $warningIcon });
            }
        },

        _createSidebar: function() {
            if(this.children.extractionsSidebar) {
                this.children.extractionsSidebar.remove();
            }
            this.children.extractionsSidebar = new Sidebar({ modalize : true });
            this.children.extractionsSidebar.render().$el.appendTo($('body'));
            this.children.extractionsSidebar.addSidebar(this.children.existingExtractions.render().$el.css({'width' : this.SIDEBAR_WIDTH + 'px'}));
            // The sidebar clobbers DOM event listeners when it gets removed, so refresh them (SPL-88877).
            this.children.existingExtractions.delegateEvents();
            this._refreshExtractions();
        },

        _forceRefreshExtractions: function() {
            var stanza = '';
            if (this.model.state.get('type') === 'sourcetype') {
                stanza = this.model.state.get('sourcetype');
            } else if (this.model.state.get('type') === 'source') {
                stanza = 'source::' + this.model.state.get('source');
            }
            var extractionSearch = 'type=inline AND stanza=' + stanza;
            if(this.collection.extractions.fetchData.get('search') !== extractionSearch) {
                this.collection.extractions.reset();
                // Update the fetch data silently and then force a synchronous fetch so observers will see the collection
                // in a loading state.
                this.collection.extractions.fetchData.set({
                    search: extractionSearch,
                    count: 0
                }, { silent: true });
                return this.collection.extractions.fetch({ data: this.model.application.pick('app', 'owner') }).then(_(function() {
                    // Filter out extractions that are using the <regex> in <field> syntax, we only want extractsion from _raw.
                    var filteredModels = this.collection.extractions.filter(function(model) {
                        return !/ in [a-zA-Z0-9_]+$/.test(model.entry.content.get('value'));
                    });
                    this.collection.extractions.reset(filteredModels);
                }).bind(this));
            }
        },

        _refreshExtractions: function() {
            this._forceRefreshExtractions();
        },

        // TODO(claral): need to fix this to account for user changing method as well as changing master event.
        tempClearState: function() {
            // Create deep copy of state model
            this.cachedStateModel = $.extend(true, {}, this.model.state.attributes);
            // Set cached mode to the mode at which the cached state model would be restored
            this.cachedStateModel.mode = fieldExtractorUtils.SELECT_METHOD_MODE;
            // Clear state model so user sees clean state when returning to previous step.
            // Selectively set only attributes that will affect how preview table is rendered
            this.model.state.set({
                sampleSize: { head: 1000 },
                regex: '',
                filter: '',
                clustering: fieldExtractorUtils.CLUSTERING_NONE,
                eventsView: fieldExtractorUtils.VIEW_ALL_EVENTS,
                examples: [],
                counterExamples: [],
                sampleEvents: [],
                requiredText: '',
                delimType: '',
                delim: '',
                delimFieldNames: [],
                method: ''
            });
        },

        restoreClearedState: function() {
            // Restore state model to cached state as user did not make any changes
            this.model.state.set(this.cachedStateModel);
            // Reset cached field names because setting delim reset them to default
            if (this.cachedFieldsState) {
                this.model.state.set({delimFieldNames: this.cachedFieldsState.delimFieldNames});
            }
            // Delete cached state model
            this.cachedStateModel = null;
        },

        tempClearFields: function() {
            this.cachedFieldsState = $.extend(true, {}, this.model.state.attributes);
            this.cachedFieldsState.mode = this.model.state.previous('mode');

            this.model.state.set({
                sampleSize: { head: 1000 },
                regex: '',
                filter: '',
                clustering: fieldExtractorUtils.CLUSTERING_NONE,
                eventsView: fieldExtractorUtils.VIEW_ALL_EVENTS,
                examples: [],
                counterExamples: [],
                sampleEvents: [],
                requiredText: '',
                delimType: '',
                delim: '',
                delimFieldNames: [],
                delimItems: []
            });
        },

        restoreClearedFields: function() {
            this.model.state.set(this.cachedFieldsState);
            // Reset cached field names because setting delim reset them to default
            this.model.state.set({delimFieldNames: this.cachedFieldsState.delimFieldNames});
            this.cachedFieldsState = null;
        },

        _createComponents: function() {
            this._setupControllers();
            this._setupStepWizard();
            this._setupFlashMessages();
            this._setupSelectSourcetypeMode();
            this._setupSelectMasterMode();
            this._setupCounterExampleEditor();
            this._setupMasterEventEditor();
            this._setupMasterEventDelimEditor();
            this._setupManualExtractionEditor();
            this._setupExtractionViewer();
            this._setupExistingExtractionsList();
            this._setupResultsTable();
            this._initializeHide();
            this._setupConfirmationView();
        },

        _setupControllers: function() {
            this.children.previewJobController = new PreviewJobController({
                model: {
                    application: this.model.application,
                    state: this.model.state,
                    searchJob: this.model.searchJob
                }
            });

            this.children.regexGenerationController = new RegexGeneratorController({
                model: {
                    application: this.model.application,
                    state: this.model.state,
                    searchJob: this.model.searchJob
                }
            });
            if(this.model.state.has('masterEvent')) {
                this.children.regexGenerationController.setMasterEvent(this.model.state.get('masterEvent'));
                // Since in this entry flow the user did not choose a sample event, we do not yet have a running job to
                // pass to the regex generator, so we dispatch one here and store the resulting promise.
                this.jobReadyDfd = this.children.previewJobController.preview(this._generatePreviewBasesearch(), {data:{provenance:"UI:FieldExtractor"}});
            }
            else {
                // If we reach this branch we are in an entry flow where the user selects a sample event.  This means
                // we are guaranteed to have a running job for the regex generator.
                this.jobReadyDfd = $.Deferred().resolve();
            }
        },

        _setupStepWizard: function() {
            this.children.stepWizardControl = new StepWizardControl({
                model: this.model.state,
                modelAttribute: 'mode',
                collection: this.collection.wizardSteps,
                validateNext: _(function() {
                    if(this.model.state.get('mode') === fieldExtractorUtils.SAVE_FIELDS_MODE) {
                        this._validateAndSaveExtraction();
                        // Return false because the validation will advance to the next step only on a successful save.
                        return false;
                    }
                    return true;
                }).bind(this)
            });
        },

        _setupFlashMessages: function() {
            this.children.flashMessages = new FlashMessages({
                model: {
                    searchJob: this.model.searchJob,
                    extraction: this.model.extraction,
                    transform: this.model.transform,
                    extractionAcl: this.model.extraction.acl
                },
                whitelist: [splunkdUtils.FATAL, splunkdUtils.ERROR, splunkdUtils.WARNING]
            });
            this.regexErrorMessageId = _.uniqueId('regex-error-');
        },

        _setupSelectSourcetypeMode: function() {
            var currentSourcetype = new Sourcetype();
            currentSourcetype.entry.set({ name: this.model.state.get('sourcetype') });
            // If we're bootstrapping from an sid, show a simple drop-down control since it will only
            // contain the few sourcetypes from that job.
            var sourcetypePrompt = _('-- Select Source Type --').t();
            if(this.options.sid) {
                this.children.sourcetypeDropDown = new SyntheticSelectControl({
                    model: this.model.state,
                    modelAttribute: 'sourcetype',
                    toggleClassName: 'btn',
                    prompt: sourcetypePrompt,
                    items: this.collection.sourcetypes.map(function(sourcetype) {
                        return ({
                            description: sourcetype.entry.content.get('description') || '',
                            value: sourcetype.entry.get('name')
                        });
                    })
                });
            } else {
                var items = [{description: 'Source type', value: 'sourcetype'},
                             {description: 'Source', value: 'source'}];
                this.children.typeDropDown = new SyntheticSelectControl({
                    model: this.model.state,
                    modelAttribute: 'type',
                    toggleClassName: 'btn',
                    items: items
                });

                this.children.sourcetypeDropDown = new SourcetypeMenu({
                    addLabel: false,
                    prompt: sourcetypePrompt,
                    model: currentSourcetype.entry,
                    modelAttribute: 'name',
                    collection: {
                        sourcetypesCollection: this.collection.sourcetypes
                    }
                });

                this.children.source = new ControlGroup({
                    controlType: 'Text',

                    controlOptions: {
                        modelAttribute: 'source',
                        model: this.model.state
                    },
                    label: _('Source Name').t()
                });
            }
            this.listenTo(currentSourcetype.entry, 'change:name', function() {
                this.model.state.set({ sourcetype: currentSourcetype.entry.get('name') });
            });
        },

        _setupSelectMasterMode: function() {
            this.children.masterEventViewer = new MasterEventViewer({
                model: {
                    state: this.model.state
                }
            });
        },

        _setupCounterExampleEditor: function() {
            this.children.counterExampleEditor = new CounterExampleEditor({
                model: {
                    state: this.model.state
                }
            });
            this.listenTo(this.children.counterExampleEditor, 'action:removeCounterExample', function(index) {
                var promise = this.children.regexGenerationController.removeCounterExample(index);
                this._handleRegexGeneratorPromise(promise);
            });
        },

        _setupMasterEventEditor: function() {
            this.children.masterEventEditor = new MasterEventEditor({
                model: {
                    state: this.model.state
                }
            });
            this.listenTo(this.children.masterEventEditor, 'action:addExtraction', function(selection) {
                this.showLoading();
                $.when(this.jobReadyDfd).then(_(function() {
                    var promise = this.children.regexGenerationController.addExample(
                        _(selection).pick('fieldName', 'startIndex', 'endIndex')
                    );
                    this._handleRegexGeneratorPromise(promise);
                }).bind(this));
            });
            this.listenTo(this.children.masterEventEditor, 'action:addSampleExtraction', function(selection, index) {
                var promise = this.children.regexGenerationController.addSampleExtraction(
                    _(selection).pick('fieldName', 'startIndex', 'endIndex'),
                    index
                );
                this._handleRegexGeneratorPromise(promise);
            });
            this.listenTo(this.children.masterEventEditor, 'action:addRequiredText', function(selection) {
                var promise = this.children.regexGenerationController.addRequiredText(selection.selectedText);
                this._handleRegexGeneratorPromise(promise);
            });
            this.listenTo(this.children.masterEventEditor, 'action:removeRequiredText', function() {
                var promise = this.children.regexGenerationController.removeRequiredText();
                this._handleRegexGeneratorPromise(promise);
            });
            this.listenTo(this.children.masterEventEditor, 'action:selectManualMode', function() {
                this.setManualMode();
            });
            this.listenTo(this.children.masterEventEditor, 'action:renameExistingExample', function(oldFieldName, newFieldName) {
                var promise = this.children.regexGenerationController.renameExample(oldFieldName, newFieldName);
                this._handleRegexGeneratorPromise(promise);
            });
            this.listenTo(this.children.masterEventEditor, 'action:removeExistingExample', function(fieldName) {
                var promise = this.children.regexGenerationController.removeExample(fieldName);
                this._handleRegexGeneratorPromise(promise);
            });
            this.listenTo(this.children.masterEventEditor, 'action:removeExistingSampleExtraction', function(fieldName, index) {
                var promise = this.children.regexGenerationController.removeSampleExtraction(fieldName, index);
                this._handleRegexGeneratorPromise(promise);
            });
            this.listenTo(this.children.masterEventEditor, 'action:removeExistingSampleEvent', function(index) {
                var existingSampleExtractions = this.model.state.get('existingSampleExtractions');
                existingSampleExtractions.splice(index, 1);
                this.model.state.set('existingSampleExtractions', existingSampleExtractions);
                var promise = this.children.regexGenerationController.removeSampleEvent(index);
                this._handleRegexGeneratorPromise(promise);
            });
        },

        _setupMasterEventDelimEditor: function() {
            this.children.masterEventDelimEditor = new MasterEventDelimEditor({
                model: {
                    state: this.model.state
                }
            });
            this.listenTo(this.children.masterEventDelimEditor, 'action:hideMasterEventViewer', function() {
                this.children.masterEventViewer.detach();
            });
        },

        _setupManualExtractionEditor: function() {
            this.children.manualExtractionEditor = new ManualExtractionEditor({
                model: {
                    state: this.model.state,
                    application: this.model.application
                }
            });
            this.listenTo(this.children.manualExtractionEditor, 'action:selectAutomaticMode', function() {
                this.model.state.set('interactiveMode', fieldExtractorUtils.INTERACTION_MODE);
            });
            this.listenTo(this.children.manualExtractionEditor, 'action:save', this._handleManualExtractionSave);
            this.listenTo(this.children.manualExtractionEditor, 'action:previewInSearch', this._handlePreviewInSearch);
        },

        // The save action can have two different meanings to upstream handlers.
        // If the active extraction is already saved, then it's an in-place update.  If not, it's a creation.
        // In either case, the contract with upstream logic is that the model passed will not already be part of
        // the extractions collection, and the event handler is responsible for saving that model to the back end
        // and updating the extractions collection accordingly or displaying an error message.
        _setupSaveView: function() {
            var stanza = '';
            if (this.model.state.get('type') === 'sourcetype') {
                stanza = this.model.state.get('sourcetype');
            } else if (this.model.state.get('type') === 'source') {
                stanza = 'source::' + this.model.state.get('source');
            }
            if (this.model.state.get('method') === this.DELIM_MODE) {
                var delimiter = fieldExtractorUtils.DELIM_CONF_MAP[this.model.state.get('delimType')] ?
                    '"' + fieldExtractorUtils.DELIM_CONF_MAP[this.model.state.get('delimType')] + '"' :
                    JSON.stringify(this.model.state.get('delim'));//JSON.stringify will escape quotes
                this.model.transform.entry.content.set({
                    DELIMS: delimiter,
                    FIELDS: '"'+_(this.model.state.get('delimFieldNames')).values().join('","')+'"'
                });

                if (this.model.extraction.isNew()) {
                    this.model.extraction.entry.content.set({
                        stanza: stanza,             // value, name
                        type: 'Uses transform'
                    });
                }
                else {
                    this.model.extraction.entry.content.set({
                        value: this.model.state.get('transformName')
                    });
                }
            } else {
                if (this.model.extraction.isNew()) {
                    this.model.extraction.entry.content.set({
                        name: splunkUtils.fieldListToString(
                            fieldExtractorUtils.getCaptureGroupNames(this.model.state.get('regex'))
                        ),
                        value: this.model.state.get('regex'),
                        stanza: stanza,
                        type: 'Inline'
                    });
                }
                else {
                    this.model.extraction.entry.content.set({
                        value: this.model.state.get('regex')
                    });
                }
            }
            if(this.children.saveView) {
                this.children.saveView.detach();
                this.children.saveView.remove();
            }
            this.children.saveView = new SaveExtractionsView({
                model: {
                    extraction: this.model.extraction,
                    user: this.model.user,
                    application: this.model.application,
                    state: this.model.state,
                    serverInfo: this.model.serverInfo,
                    transform: this.model.transform
                },
                collection: {
                    roles: this.collection.roles
                }
            });
            this.listenTo(this.children.saveView, 'action:finish', function() {
                this._validateAndSaveExtraction();
            });
        },

        _setupExtractionViewer: function() {
            this.children.extractionViewer = new ExtractionViewer({
                model: {
                    state: this.model.state
                }
            });
            this.listenTo(this.children.extractionViewer, 'action:previewInSearch', this._handlePreviewInSearch);
            this.listenTo(this.children.extractionViewer, 'action:selectManualMode', function() {
                this.setManualMode();
            });
        },

        _setupExistingExtractionsList: function() {
            this.children.existingExtractions = new ExistingExtractionsList({
                collection: {
                    extractions: this.collection.extractions
                },
                model: {
                    state: this.model.state,
                    application: this.model.application
                }
            });

            this.listenTo(this.children.existingExtractions, 'action:updateHighlighting', function() {
                this._refreshPreview();
                this.children.masterEventEditor.render();
                this.children.masterEventViewer.render();
            });
        },

        _setupResultsTable: function() {
            this.children.previewView = new RexPreviewViewStack({
                model: {
                    application: this.model.application,
                    searchJob: this.model.searchJob,
                    state: this.model.state
                },
                className: 'preview-view-stack',
                autoDrilldownEnabled: false
            });

            this.listenTo(this.children.previewView, 'action:selectEvent', function(rawText, existingExtractions) {
                if(this.model.state.get('mode') === fieldExtractorUtils.SELECT_SAMPLE_MODE) {
                    this.children.regexGenerationController.setMasterEvent(rawText);
                    this.model.state.set({ existingExtractions: existingExtractions });
                    this._tryToShowExistingExtractions();
                    this._refreshExistingExtractionsButton();
                    $('html,body').animate({scrollTop: "0px"}, 300);
                } else {
                    this.children.regexGenerationController.addSampleEvent(rawText);
                    var existingSampleExtractions = this.model.state.get('existingSampleExtractions');
                    existingSampleExtractions.push(existingExtractions);
                    this.model.state.set('existingSampleExtractions', existingSampleExtractions);
                }
                this._syncStateModelFromController();
            });
            this.listenTo(this.children.previewView, 'action:removeExtraction', function(selection) {
                var promise = this.children.regexGenerationController.addCounterExample(
                    _(selection).pick('fieldName', 'rawText', 'startIndex', 'endIndex')
                );
                this._handleRegexGeneratorPromise(promise);
                $('html,body').animate({scrollTop: "0px"}, 300);
            });
            this.listenTo(this.children.previewView, 'action:valueDrilldown', function(fieldName, value) {
                this.model.state.set({ filter: fieldName + '=' + value });
            });
            this.listenTo(this.children.previewView, 'action:nextStep', function() {
                this.model.state.set({ mode: this._getNextMode().get('value') });
            });
        },

        regexManuallyModified: function() {
            var regex = this.model.state.get('regex'),
                regexManuallyModified = regex !== this.children.regexGenerationController.getCurrentRegex();
            return regexManuallyModified;
        },

        applyDelim: function(delim) {
            // split sample event by this delim
            var sampleEvent = this.model.state.get('masterEvent'),
                delimSanitized,
                regexp,
                match,
                names = this.model.state.get('delimFieldNames'),
                delimItems = [];
            var delimRegex,
                delimRegexSep,
                uiRegex,
                baseRegex;
            // preprocess to get rid of leading and trailing delim characters
            var delimString = fieldExtractorUtils.DELIM_CONF_MAP[this.model.state.get('delimType')] ?
                    fieldExtractorUtils.DELIM_CONF_MAP[this.model.state.get('delimType')] :
                    this.model.state.get('delim');
            // clean up any previous error messages before we try
            this.model.state.set({ errorState: false });
            this.children.flashMessages.flashMsgHelper.removeGeneralMessage(this.regexErrorMessageId);
            this.clearError();
            try {
                if (delim.length===0) {
                    throw new Error ("Delimiter field cannot be empty");
                }
                delimSanitized = fieldExtractorUtils.getMultiCharDelimRegex(delim);
            } catch (e) {
                this.model.state.set({ errorState: true });
                this.showError();
                this.children.flashMessages.flashMsgHelper.addGeneralMessage(this.regexErrorMessageId, {
                    type: splunkdUtils.ERROR,
                    html: e.name + ': ' + e.message
                });
                return;
            }

            // SPL-145193 - Extractor doesn't recognized escaped delimiter in event. This is tricky to do with regular
            // expressions on the UI, because of lack of support for lookbehind on current Javascript. What I'm doing
            // is matching (non-backslash non-delimiters or escaped stuff)*
            //           (  !(delim or backslash or quote)           |(whatever escaped) )*
            baseRegex = "(?:(?:(?!(?:"+delimSanitized+")|\\\\|\").)|(?:\\\\.))";
            // if delimiters include double-quotes, baseRegex is already good
            if (delimString.includes('"')) {
                baseRegex += '*';
            } else {
                // if not, then fields can be quoted -- in that case, the full expression is either
                // the regex above or any non-quote (including anything escaped) between double-quotes
                // think about cases such as these (using , as delimiter):
                // "fiel\""\""d1","fiel,d2",field\,3,""fi"e"ld4
                baseRegex = "(?:\"(?:[^\\\\\"]|\\\\.)*\"|"+baseRegex+")*";
            }
            uiRegex = "^("+baseRegex+")("+delimSanitized+"|$)";
            regexp = new RegExp(uiRegex);
            while ((match = regexp.exec(sampleEvent))!=null) {
                // matching nothing with no delimiter is normal at the end of the event
                // it could also be a sign we got stuck -- haven't seen that with the
                // current regex though. breaking is the safe thing to do regardless.
                if (match[0]==='') {
                    break;
                }
                delimItems.push(match[1]);
                sampleEvent = sampleEvent.substr(match[0].length);
            }
            // dangling quotes and other oddities may cause us to abort early in the string.
            // the backend plods on, so that's what we'll do. unfortunately I have no clue of
            // how to do that for |rex... simply making the last field consume .* is wrong,
            // if the event has more delimiters after the last one in the sample used by the UI
            // resulting searches will simply trim the remaining fields, whereas .* squashes them
            // all into the last one.
            // TODO: figure out a way to preview with |rex situations like dangling quotes in the
            // last field (PBL-12571)
            if (sampleEvent.length!==0) {
                delimItems.push(sampleEvent);
            }

            delimRegex = '';
            delimRegexSep = '^';
            for (var i=0; i<delimItems.length; i++) {
                if (names.length <= i) {
                    names.push('field' + (i+1));
                }
                delimRegex += delimRegexSep + "(?P<"+names[i]+">"+baseRegex+")";
                // must start at the beginning of the string, after that all entries should
                // end with a separator, unless they are empty. the weird hacky ternary operator
                // will deal with this last alternative.
                delimRegexSep = "(?:"+delimSanitized+")" + (i>0 ? "?" : "");
            }

            this.model.state.set('delimItems', delimItems);
            this.model.state.set('regex', delimRegex);
            this.model.state.set('delimFieldNames', names);
        },

        _initializeHide: function() {
            this.children.masterEventEditor.$el.hide();
            this.children.masterEventDelimEditor.$el.hide();
            this.children.manualExtractionEditor.$el.hide();
            this.children.previewView.$el.hide();
        },

        _setupConfirmationView: function() {
            this.children.confirmationView = new ConfirmationView({
                model: {
                    state: this.model.state,
                    application: this.model.application
                }
            });
        },

        _syncStateModelFromController: function() {
            this.model.state.set({
                masterEvent: this.children.regexGenerationController.getCurrentMasterEvent(),
                examples: this.children.regexGenerationController.getCurrentExamples(),
                requiredText: this.children.regexGenerationController.getCurrentRequiredText(),
                counterExamples: this.children.regexGenerationController.getCurrentCounterExamples(),
                sampleEvents: this.children.regexGenerationController.getCurrentSampleEvents(),
                regex: this.children.regexGenerationController.getCurrentRegex()
            });
        },

        _handleRegexGeneratorPromise: function(promise) {
            this._syncStateModelFromController();
            this.showLoading();
            promise.done(_(function(regexes) {
                var newRegex = regexes[0] || '';
                this.model.state.set({ regex: newRegex });
                this.hideLoading();
                if(newRegex || this.model.state.get('examples').length === 0) {
                    // valid regex returned by endpoint
                    this.model.state.set({ errorState: false });
                    this.model.state.set({ regexGenErrorState: false });
                    this.children.flashMessages.flashMsgHelper.removeGeneralMessage(this.regexErrorMessageId);
                }
                else {
                    // regex invalid - error state
                    this.model.state.set({ errorState: true });
                    this.showError();
                }
            }).bind(this));
            promise.fail(_(function() {
                var errorMessage,
                    mode = this.model.state.get('mode');
                if(mode === fieldExtractorUtils.SELECT_FIELDS_MODE){
                    errorMessage = _('The extraction failed. If you are extracting multiple fields, try removing one or more fields. Start with extractions that are embedded within longer text strings.').t();
                }else if(mode === fieldExtractorUtils.VALIDATE_FIELDS_MODE){
                    errorMessage = _('This counterexample cannot update the extraction. Remove it and try another counterexample. If you are extracting multiple fields, you may need to step back and remove one or more of them.').t();
                }else{
                    errorMessage = splunkUtils.sprintf(_('Splunk %s cannot generate a regular expression based on the current event and field selections.').t(), this.environment);
                }
                this.children.flashMessages.flashMsgHelper.addGeneralMessage(this.regexErrorMessageId, {
                    type: splunkdUtils.ERROR,
                    html: errorMessage
                });
                this.model.state.set({ regex: '' });
                this.hideLoading();
                this.model.state.set({ regexGenErrorState: true });
                this.showError();
            }).bind(this));
        },

        _refreshPreview: function() {
            if (this.model.state.get('method') === this.DELIM_MODE){
                var filler = splunkUtils.sprintf(_('Preview (%s fields)').t(),
                                                 this.model.state.get('delimFieldNames').length);
                this.$('.instructions-title').text(filler);
            }
            this.children.previewJobController.preview(this._generatePreviewBasesearch(), {data:{provenance:"UI:FieldExtractor"}});
        },

        _generatePreviewBasesearch: function() {
            var mode = this.model.state.get('mode'),
                prefix = '';
            if (this.options.sid &&
                ((mode === fieldExtractorUtils.SELECT_SAMPLE_MODE && this.model.state.get('useSearchFilter')) ||
                 (mode === fieldExtractorUtils.SELECT_FIELDS_MODE && this.model.state.get('useSearchFilter')) ||
                 (mode === fieldExtractorUtils.SELECT_DELIM_MODE && this.model.state.get('useSearchFilter')) ||
                 (mode === fieldExtractorUtils.VALIDATE_FIELDS_MODE && this.model.state.get('useSearchFilter')) ||
                 (mode !== fieldExtractorUtils.SELECT_FIELDS_MODE && mode !== fieldExtractorUtils.VALIDATE_FIELDS_MODE && mode !== fieldExtractorUtils.SELECT_SAMPLE_MODE))) {
                prefix = '| loadjob ' + this.options.sid + ' events=t ignore_running=f require_finished=f | search ';
            }
            var previewBaseSearch = prefix + 'index=* OR index=_*';
            if (this.model.state.get('type') === 'sourcetype' && this.model.state.get('sourcetype')) {
                previewBaseSearch += ' sourcetype=' +  splunkUtils.searchEscape(this.model.state.get('sourcetype'));
            } else if (this.model.state.get('type') === 'source' && this.model.state.get('source')) {
                previewBaseSearch += ' source="' +  splunkUtils.searchEscape(this.model.state.get('source')) + '"';
            }

            var regex = "(?ms)" + this.model.state.get('regex');

            if(regex && fieldExtractorUtils.getCaptureGroupNames(regex).length > 0) {
                var pipeToRex = splunkUtils.sprintf(
                    ' | rex field=%s %s' + ' offset_field=%s',
                    splunkUtils.searchEscape(this.model.state.get('inputField')),
                    splunkUtils.searchEscape(regex, { forceQuotes: true }),
                    fieldExtractorUtils.OFFSET_FIELD_NAME
                );
                previewBaseSearch += pipeToRex;
            }
            // Add a rex command for each existing extraction.
            (this.collection.extractions).each((function(extraction, i) {
                var pipeToRex = splunkUtils.sprintf(
                    ' | rex field=%s %s' + ' offset_field=%s' + i,
                    splunkUtils.searchEscape(this.model.state.get('inputField')),
                    splunkUtils.searchEscape(extraction.entry.content.get('value'), { forceQuotes: true }),
                    fieldExtractorUtils.OFFSET_FIELD_NAME
                );
                previewBaseSearch += pipeToRex;
            }).bind(this));
            return previewBaseSearch;
        },

        _refreshExtractionViews: function() {
            // Setup routines for each wizard/manual mode that user enters

            this.$('.content-header').removeClass('content-header-narrow');
            this.$('.content-body').show();

            var mode = this.model.state.get('mode'),
                interactiveMode = this.model.state.get('interactiveMode'),
                isManualMode = interactiveMode === fieldExtractorUtils.NO_INTERACTION_MODE,
                method = this.model.state.get('method'),
                type = this.model.state.get('type'),
                sourcetype = this.model.state.get('sourcetype'),
                source = this.model.state.get('source');

            if(isManualMode) {
                if(fieldExtractorUtils.isManualEditorMode(mode, interactiveMode)) {
                   this.children.manualExtractionEditor.appendTo(this.$('.content-header')).$el.show();
                   this.$('.regex-editor-wrapper').find('textarea').focus();
                }
            }else{
                if(mode === fieldExtractorUtils.SELECT_SAMPLE_MODE){
                    this.$('.select-sample-header').detach();
                    $(_(this.selectMasterEventTemplate).template({
                        urlSourcetype: this.options.sourcetype,
                        sourcetype: sourcetype,
                        source: source,
                        type: type,
                        fieldsHelpHref: route.docHelp(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            'manager.fields'
                        )
                    })).appendTo(this.$('.content-header'));
                    this.children.sourcetypeDropDown.detach();
                    if (!this.options.sid && !this.options.sourcetype) {
                        this.children.typeDropDown.detach();
                        this.children.source.detach();
                        // Only show type drop down when starting from bare field_extractor page
                        this.children.typeDropDown.appendTo(this.$('.type-dropdown-wrapper')).$el.show();
                        if (type === 'sourcetype') {
                            this.children.sourcetypeDropDown.appendTo(this.$('.sourcetype-dropdown-wrapper')).$el.show();
                        } else if(type === 'source') {
                            this.children.source.appendTo(this.$('.source-wrapper')).$el.show();
                        }
                    } else {
                        this.children.sourcetypeDropDown.appendTo(this.$('.sourcetype-dropdown-wrapper')).$el.show();
                    }
                    this.children.masterEventViewer.render().appendTo(this.$('.content-header')).$el.show();
                }

                else if(mode === fieldExtractorUtils.SELECT_METHOD_MODE){
                    $(_(this.selectMethodTemplate).template({
                        type: type,
                        sourcetype: sourcetype,
                        source: source,
                        ifxHelpHref: route.docHelp(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            'learnmore.field.extraction.method'
                        ),
                        regexTxt: splunkUtils.sprintf(_('Splunk %s will extract fields using a Regular Expression.').t(), this.environment),
                        delimTxt: splunkUtils.sprintf(_('Splunk %s will extract fields using a delimiter (such as commas, spaces, or characters). Use this method for delimited data like comma separated values (CSV files).').t(), this.environment)
                    })).appendTo(this.$('.content-header'));
                    this.$('.content-body').hide();
                    this.children.masterEventViewer.render().insertBefore(this.$('.method-switch'));
                    this._updateMethodButtons();
                }

                else if(mode === fieldExtractorUtils.SELECT_DELIM_MODE){
                    var delimiters = [
                            {label: _('Space').t(), value: 'space'},
                            {label: _('Comma').t(), value: 'comma'},
                            {label: _('Tab').t(), value: 'tab'},
                            {label: _('Pipe').t(), value: 'pipe'},
                            {label: _('Other').t(), value: 'custom'}];

                    this.children.delimiterRadio = new SyntheticRadioControl({
                        model: this.model.state,
                        modelAttribute: 'delimType',
                        toggleClassName: 'btn',
                        prompt: _('Delimiter').t(),
                        items: delimiters
                    });
                    this.children.delimiterCustom = new TextControl({
                        model: this.model.state,
                        modelAttribute: 'delim',
                        inputClassName: 'delim-custom',
                        trimLeadingSpace: false,
                        trimTrailingSpace: false
                    });

                    $(_(this.selectDelimTemplate).template({
                        delimRenameHelp: route.docHelp(
                            this.model.application.get('root'),
                            this.model.application.get('locale'),
                            'learnmore.field.extraction.rename'
                        )
                    })).appendTo(this.$('.content-header'));
                    this.$('.delimiter-radio').append(this.children.delimiterRadio.render().$el);
                    this.$('.delimiter-radio').append(this.children.delimiterCustom.render().$el);

                    this._hideExistingExtractions();

                    if (this.model.state.get('delimType') !== 'custom') {
                        this.children.delimiterCustom.$el.hide();
                    }
                    this.children.masterEventDelimEditor.detach();
                    if (!this.model.state.get('delimItems') || this.model.state.get('delimItems').length === 0) {
                        this.children.masterEventViewer.render().appendTo(this.$('.delim-selector'));
                    } else {
                        this.children.masterEventDelimEditor.appendTo(this.$('.content-header')).$el.show();
                    }
                    if(this.$('.content-body').find('.body-instructions').length === 0){
                        this.$('.content-body').prepend(_(this.previewInstructionsTemplate).template({
                            text: ''
                        }));
                    }
                }

                else if(mode === fieldExtractorUtils.SELECT_FIELDS_MODE){
                    this.$('.select-fields-header').detach();
                    $(_(this.selectFieldsTemplate).template(
                        {
                            ifxHelpHref: route.docHelp(
                                this.model.application.get('root'),
                                this.model.application.get('locale'),
                                'learnmore.field.extraction.automatic'
                            )
                        }
                    )).appendTo(this.$('.content-header'));
                    this.children.masterEventEditor.detach();
                    this.children.masterEventEditor.appendTo(this.$('.content-header')).$el.show();
                    this.children.extractionViewer.appendTo(this.$('.content-header'));
                    if(this.$('.content-body').find('.body-instructions').length === 0){
                        this.$('.content-body').prepend(_(this.previewInstructionsTemplate).template({
                            text: _('If you see incorrect results below, click an additional event to add it to the set of sample events. Highlight its values to improve the extraction. You can remove incorrect values in the next step.').t()
                        }));
                    }
                }

                else if(mode === fieldExtractorUtils.VALIDATE_FIELDS_MODE){
                    //Render the instructions
                    this.$('.validate-fields-header').detach();
                    $(_(this.validateFieldsTemplate).template({
                        instructionsText: _('Validate your field extractions and remove values that are incorrectly highlighted in the Events tab. In the field tabs, inspect the extracted values for each field, and optionally click a value to apply it as a search filter to the Events tab event list.').t()
                    })).appendTo(this.$('.content-header'));

                    this.children.counterExampleEditor.detach();
                    this.children.counterExampleEditor.appendTo(this.$('.content-header')).$el.show();
                    this.children.extractionViewer.appendTo(this.$('.content-header'));
                }
            }

            if(mode === fieldExtractorUtils.SAVE_FIELDS_MODE){
                this.$('.save-extractions-header').detach();
                $(_(this.saveExtractionsTemplate).template({
                    extractionIsNew: this.model.extraction.isNew()
                })).appendTo(this.$('.content-header'));
                this._setupSaveView();
                this.children.saveView.render().appendTo(this.$('.content-header').addClass('content-header-narrow')).$el.show();
                this.$('.content-body').hide();
                if(this.model.state.get('interactiveMode') === fieldExtractorUtils.NO_INTERACTION_MODE){
                    this.$('.return-manual-page').show();
                    this.$('.manual-save-button').show();
                }
            }

            if(mode === fieldExtractorUtils.CONFIRMATION_MODE) {
                this.$('.confirmation-header').detach();
                this.$('.content-body').hide();
                if(this.model.state.get('interactiveMode') === fieldExtractorUtils.NO_INTERACTION_MODE){
                    this.$('.return-manual-page').hide();
                    this.$('.manual-save-button').hide();
                }
                var editExtractionsHref = route.manager(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    this.model.application.get('app'),
                    ['data', 'props', 'extractions']
                );
                var successMessage = splunkUtils.sprintf(
                        _('You have extracted additional fields from your data (sourcetype=%s).').t(),
                        this.model.state.get('sourcetype'));
                if (this.model.state.get('type') === 'source') {
                    successMessage = splunkUtils.sprintf(
                        _('You have extracted additional fields from your data (source=%s).').t(),
                        this.model.state.get('source'));
                }
                $(_(this.confirmationTemplate).template({
                    successMessage: successMessage,
                    editExtractionsMessage: splunkUtils.sprintf(
                        _('Edit your field extractions at any time by going to %s.').t(),
                        '<a href="' + editExtractionsHref + '" class="edit-extractions-link">' + _('Field Extractions').t() + '</a>'
                    )
                })).appendTo(this.$('.content-header'));
                this.children.confirmationView.render().appendTo(this.$('.content-header').addClass('content-header-narrow')).$el.show();
            }

            // Only show existing extractions flyout button when in the first two wizard steps
            // or when selecting fields not in delim mode.
            // Do not show for save or confirm steps.
            if (mode === fieldExtractorUtils.SELECT_SAMPLE_MODE ||
                mode === fieldExtractorUtils.SELECT_METHOD_MODE ||
                mode === fieldExtractorUtils.SELECT_FIELDS_MODE ||
                mode === fieldExtractorUtils.VALIDATE_FIELDS_MODE) {
                this._refreshExistingExtractionsButton();
                this.$('.view-all-extractions-button-container').show();
            }
            if (!this.model.state.get('masterEvent')) {
                this.$('.view-all-extractions-button-container').find('.view-extractions-button').addClass('disabled');
            }

            if(fieldExtractorUtils.isEventsTableMode(mode, interactiveMode)){
                if (mode === fieldExtractorUtils.SELECT_FIELDS_MODE && !this.model.state.get('regex') ||
                    mode === fieldExtractorUtils.SELECT_DELIM_MODE && !this.model.state.get('delim') ||
                    (mode === fieldExtractorUtils.SELECT_SAMPLE_MODE &&
                        (type === '' || !this.model.state.get(type) || this.model.state.get(type) === '' ))) {
                    this.$('.content-body').hide();
                }
                else {
                    if (mode === fieldExtractorUtils.SELECT_SAMPLE_MODE &&
                        this.model.state.previous('interactiveMode') !== fieldExtractorUtils.NO_INTERACTION_MODE &&
                        this.model.state.get('interactiveMode') !== fieldExtractorUtils.NO_INTERACTION_MODE &&
                        ((type === 'sourcetype' && sourcetype) || (type === 'source' && source))) {
                        this._refreshPreview();
                    }
                    this.children.previewView.detach();
                    this.$('.content-body').show();
                    this.children.previewView.appendTo(this.$('.content-body')).$el.show();
                }
            }
        },

        _handlePreviewInSearch: function() {
            var url = route.search(
                this.model.application.get('root'),
                this.model.application.get('locale'),
                this.model.application.get('app'),
                { data: { q: this._generatePreviewBasesearch() } }
            );
            window.open(url, '_blank');
        },

        _handleManualExtractionSave: function() {
            this.model.state.set({ mode: fieldExtractorUtils.SAVE_FIELDS_MODE });
            this._cleanupManualView();
        },

        _validateAndSaveExtraction: function() {
            this.children.saveView.saveExtractions().done(_(function() {
                this.model.state.set({ mode: fieldExtractorUtils.CONFIRMATION_MODE });
            }).bind(this));
        },

        _getNextMode: function() {
            var activeMode = this._getCurrentMode(),
                activeModeIndex = this.collection.wizardSteps.indexOf(activeMode);

            return this.collection.wizardSteps.at(activeModeIndex + 1);
        },

        _getCurrentMode: function() {
            return this.collection.wizardSteps.findWhere({ value: this.model.state.get('mode') });
        },

        _updateMethodButtons: function() {
            var method = this.model.state.get('method');
            if (method === this.DELIM_MODE) {
                this.$('.btn-delim').addClass('selected-method');
                this.$('.btn-regex').removeClass('selected-method');
            } else if (method === this.REGEX_MODE) {
                this.$('.btn-regex').addClass('selected-method');
                this.$('.btn-delim').removeClass('selected-method');
            }
        },

        render: function() {
            this.$el.html(this.compiledTemplate({
                sourcetype: this.model.state.get('sourcetype')
            }));
            this.children.stepWizardControl.render().appendTo(this.$('.step-buttons-container'));
            this.children.flashMessages.render().appendTo(this.$('.flash-messages-container'));
            if (!this.options.sid && !this.options.sourcetype) {
                this.children.typeDropDown.render();
                this.children.source.render();
            }
            this.children.sourcetypeDropDown.render();
            this.children.extractionViewer.render();
            this.children.previewView.render();
            this.children.masterEventEditor.render();
            this.children.manualExtractionEditor.render();
            this._refreshExtractionViews();
            if(!this.model.extraction.isNew()) {
                this.setManualMode();
            }
            return this;
        },

        showLoading: function() {
            this.children.stepWizardControl.disable();
            this.$('.instruction a').addClass('disabled');
            this.children.masterEventEditor.disable();
            this.children.counterExampleEditor.disable();
            this.children.previewView.$el.hide();
            this.$('.regex-loading-message').show();
            this.children.extractionViewer.disable();
        },

        hideLoading: function() {
            this.children.stepWizardControl.enable();
            this.$('.instruction a').removeClass('disabled');
            this.children.masterEventEditor.enable();
            this.children.counterExampleEditor.enable();
            this.children.previewView.$el.show();
            this.$('.regex-loading-message').hide();
            this.children.extractionViewer.enable();
        },

        showError: function() {
            this.children.stepWizardControl.disable();
            this.$('.instruction a').addClass('disabled');
            this.children.extractionViewer.disable();
        },

        clearError: function() {
            this.children.stepWizardControl.enable();
            this.$('.instruction a').removeClass('disabled');
            this.children.extractionViewer.enable();
        },

        viewAllExtractionsTemplate: '\
            <% if(warningOn) { %>\
                <i class="icon-alert" title="<%- _("There are existing extractions, however because they overlap, they can only be manually turned on.").t() %>"></i>\
            <% } %>\
            <button class="view-extractions-button btn"><%- _("Existing fields").t() %> <i class="icon-chevron-right"></i></button>\
        ',

        selectMasterEventTemplate: '\
            <div class="select-sample-header">\
                <div class="instruction">\
                    <h2 class="instruction-title"><%- _("Select Sample Event").t() %></h2>\
                    <span class="instruction-text">\
                        <%- _("Choose a source or source type, select a sample event, and click Next to go to the next step. The field extractor will use the event to extract fields. ").t() %>\
                        <a href="<%- fieldsHelpHref %>" class="external" target="_blank"><%- _("Learn more").t() %></a>\
                        <% if (urlSourcetype || sourcetype || source) { %>\
                            <div class="manual-mode-button-container"><a href="#" class="manual-mode-button"><%- _("I prefer to write the regular expression myself").t() %> <i class="icon-chevron-right"></i></a></div>\
                        <% } %>\
                    </span>\
                </div>\
                <% if (!urlSourcetype) { %>\
                    <div class="type-wrapper form-horizontal">\
                        <span class="type-label"><%- _("Data Type").t() %></span>\
                        <div class="type-dropdown-wrapper"></div>\
                        <% if (type === "sourcetype") { %>\
                            <div class="sourcetype-wrapper"><span class="sourcetype-label"><%- _("Source Type").t() %></span>\
                            <div class="sourcetype-dropdown-wrapper"></div></div>\
                        <% } else if (type === "source") { %>\
                            <div class="source-wrapper form-horizontal align-left"></div>\
                        <% } %>\
                    </div>\
                <% } else { %>\
                    <div class="sourcetype-wrapper"><span class="sourcetype-label"><%- _("Source type ").t() %></span>\
                    <span class="sourcetype-name"><%- urlSourcetype %></span></div>\
                <% } %>\
            </div>\
        ',

        selectMethodTemplate: '\
            <div class="select-method-header">\
                <div class="instruction">\
                    <h2 class="instruction-title"><%- _("Select Method").t() %></h2>\
                    <span class="instruction-text">\
                        <%- _("Indicate the method you want to use to extract your field(s).").t() %>\
                        <a href="<%- ifxHelpHref %>" class="external" target="_blank"><%- _("Learn more").t() %></a>\
                    </span>\
                    <div class="manual-mode-button-container"><a href="#" class="manual-mode-button"><%- _("I prefer to write the regular expression myself").t() %> <i class="icon-chevron-right"></i></a></div>\
                </div>\
                <% if (type === "sourcetype") { %>\
                    <div class="sourcetype-wrapper"><span class="sourcetype-label"><%- _("Source type").t() %></span>\
                    <span class="sourcetype-name"><%- sourcetype %></span></div>\
                <% } else { %>\
                    <div class="source-wrapper"><span class="source-label"><%- _("Source").t() %></span>\
                    <span class="source-name"><%- source %></span></div>\
                <% } %>\
                <div class="method-switch">\
                    <div class="type-container">\
                        <div class="type-btn btn-regex" tabIndex="0">\
                            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="72px" height="72px" viewBox="-3 -18 72 72">\
                                <circle class="fill" cx="44.9" cy="31" r="2"/>\
                                <circle class="fill"  cx="15.9" cy="31" r="2"/>\
                                <path class="fill"  d="M46.1,25h-2.4c0-5,2.5-7.1,4.6-8.8c1.6-1.4,2.5-2.2,2.5-3.9c0-4.8-3.8-5.2-5.4-5.2 c-0.2,0-5.9-0.1-5.9,6.9h-2.4c0-8,5.4-9.3,8.3-9.3c3.6,0,7.8,1.9,7.8,7.7c0,2.9-1.8,4.4-3.4,5.7C47.9,19.7,46.1,21.1,46.1,25z"/>\
                                <polygon class="fill"  points="32.3,9.6 31.6,7.7 26.9,9.5 26.9,5 24.9,5 24.9,9.5 20.3,7.7 19.5,9.6 24.3,11.5  21.2,15.6 22.8,16.8 25.9,12.7 29,16.8 30.6,15.6 27.5,11.5 "/>\
                                <path class="fill"  d="M60.5,36h2.1c2-6.2,3.2-11.7,3.2-18.4c0-6.4-1.1-12.8-2.8-17.6h-2.2c1.9,4.6,3,11.2,3,17.6 C63.8,24.2,62.6,29.7,60.5,36z"/>\
                                <path class="fill"  d="M5.4,36H3.2C1.2,30,0,24.3,0,17.6C0,11.2,1.1,5,2.8,0H5C3.2,5,2,11.2,2,17.6 C2,24.2,3.3,30,5.4,36z"/>\
                            </svg>\
                            <div class="type-title-text"><%=_("Regular Expression").t()%></div>\
                        </div>\
                        <div class="type-desc-text"><%= regexTxt %></div>\
                    </div>\
                    <div class="type-container">\
                        <div class="type-btn btn-delim" tabIndex="0">\
                            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="72px" height="72px" viewBox="-2 -20 72 72">\
                            <rect x="19" class="fill" width="2" height="26"/>\
                            <rect x="47" class="fill" width="2" height="26"/>\
                            <polygon class="fill" points="0,21 2.5,21 7,15.1 11.5,21 14.1,21 8.3,13.5 14.1,6 11.5,6 7,11.9 2.5,6 0,6 5.8,13.5 "/>\
                            <path class="fill" d="M39.2,6c-1.2,2.9-3.4,8-5.3,12.5L28.9,6h-2.2l6,15.1c-1.2,2.8-2.1,5.1-2.4,5.8 c-0.7,1.8-1.7,2-3.4,2H27v2c0,0,0,0,0.1,0c1.7,0,3.8-0.3,5.1-3.3C33,25.7,39.3,10.9,41.3,6H39.2z"/>\
                            <polygon class="fill" points="68,21 54,21 64,8 54,8 54,6 68.1,6 58.1,19 68,19 "/>\
                            </svg>\
                            <div class="type-title-text"><%=_("Delimiters").t()%></div>\
                        </div>\
                        <div class="type-desc-text"><%= delimTxt %></div>\
                    </div>\
                </div>\
            </div>\
        ',

        selectDelimTemplate: '\
            <div class="select-fields-header">\
                <div class="instruction">\
                    <h2 class="instruction-title"><%- _("Rename Fields").t() %></h2>\
                    <span class="instruction-text">\
                        <%- _("Select a delimiter. In the table that appears, rename fields by clicking on field names or values. ").t() %>\
                        <a href="<%- delimRenameHelp %>" class="external" target="_blank"><%- _("Learn more").t() %></a>\
                    </span>\
                    <div class="delim-selector">\
                        <span><%= _("Delimiter").t() %></span>\
                        <div class="delimiter-radio"></div>\
                    </div> \
                </div>\
            </div>\
        ',

        selectFieldsTemplate: '\
            <div class="select-fields-header">\
                <div class="instruction">\
                    <h2 class="instruction-title"><%- _("Select Fields").t() %></h2>\
                    <span class="instruction-text">\
                        <%- _("Highlight one or more values in the sample event to create fields. You can indicate one value is required, meaning it must exist in an event for the regular expression to match. Click on highlighted values in the sample event to modify them. To highlight text that is already part of an existing extraction, first turn off the existing extractions.").t() %>\
                        <a href="<%- ifxHelpHref %>" class="external" target="_blank"><%- _("Learn more").t() %></a>\
                    </span>\
                </div>\
            </div>\
        ',

        validateFieldsTemplate: '\
            <div class="validate-fields-header">\
                <div class="instruction">\
                    <h2 class="instruction-title"><%- _("Validate").t() %></h2>\
                    <span class="instruction-text"><%= instructionsText %></span>\
                </div>\
            </div>\
        ',

        saveExtractionsTemplate: '\
            <div class="save-extractions-header">\
                <div class="instruction"> \
                    <h2 class="instruction-title"><%- _("Save").t() %></h2>\
                    <span class="instruction-text">\
                        <% if(extractionIsNew) { %>\
                            <%- _("Name the extraction and set permissions.").t() %> \
                        <% } else { %>\
                            <%- _("Verify permissions").t() %> \
                        <% } %>\
                    </span>\
                </div>\
            </div>\
        ',

        confirmationTemplate: '\
            <div class="confirmation-header">\
                <div class=" instructions">\
                    <h2 class="instruction-title"><%- _("Success!").t() %></h2>\
                </div>\
                <p class="success-message"><%- successMessage %></p>\
                <p class="edit-extractions-message">\
                    <%= editExtractionsMessage %>\
                </p>\
            </div>\
        ',

        previewInstructionsTemplate: '\
            <div class="body-instructions">\
                <h3 class="instructions-title"><%- _("Preview").t() %></h3>\
                <div class="instructions-text">\
                    <%= text %>\
                </div>\
            </div>\
        ',

        template: '\
            <div class="page-header">\
                <h1 class="extract-fields-page-title"><%- _("Extract Fields").t() %></h1>\
                <a href="#" class="btn previous-button return-automatic-mode" style="display:none"><i class="icon-chevron-left"></i> <%- _("Back").t() %></a>\
                <a href="#" class="btn previous-button return-manual-page" style="display:none"><i class="icon-chevron-left"></i> <%- _("Back").t() %></a>\
                <a href="#" class="btn btn-primary manual-save-button" style="display:none"><i class="icon-chevron-right"></i> <%- _("Finish").t() %></a>\
                <div class="step-buttons-container"></div>\
                <div class="view-all-extractions-button-container"></div>\
            </div>\
            <div class="page-content">\
                <div class="content-header">\
                    <div class="flash-messages-container"></div>\
                </div>\
                <div class="content-body preview-container">\
                    <div class="regex-loading-message" style="display: none;">\
                        <div class="alert alert-info">\
                            <i class="icon-alert"></i>\
                            <%- _("Generating a Regular Expression...").t() %>\
                        </div>\
                    </div>\
                </div>\
            </div>\
        '

    });

});
