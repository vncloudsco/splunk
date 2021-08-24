define(
    [
        'jquery',
        'underscore',
        'module',
        'models/search/SearchBar',
        'models/services/authentication/User',
        'views/Base',
        'views/shared/searchbarinput/advancedsearchfield/Master',
        'views/shared/searchbarinput/TextAreaSearchField',
        'views/shared/searchbarinput/searchassistant/Master',
        'splunk.util',
        './Master.pcss'
    ],
    function($, _, module, SearchBarModel, UserModel, Base, AdvancedEditorSearchField, TextAreaSearchField, SearchAssistant, splunkUtils, css) {
        return Base.extend({
            moduleId: module.id,
            className: 'search-bar-input',
            /**
             * @param {Object} options {
             *     model: {
             *         content: <models.Backbone> A model with the searchAttribute.
             *                 The value of the searchAttribute populates the search bar on initialize, activate and change.
             *                 The value of the searchAttribute is set on submit.
             *                 Triggering 'applied' on this model calls submit.,
             *         user: <models.services.authentication.User> (Optional) only needed if using user's preferences to determine syntaxHighlighting and searchHelper,
             *         application: <models.Application>
             *         searchBar: <models.search.SearchBar> (Optional) created if not passed in.
             *                    This represents the state of the search string in the text area.
             *                    Listens to change of search attribute and updates text area
             *     },
             *     collection: {
             *         searchBNFs: <collections/services/configs/SearchBNFs>
             *     },
             *     useAdvancedEditor (optional): <Boolean>
             *     showLineNumbers (optional): <Boolean> determines if show line numbers is on, this trumps user preference in user model.
             *     searchAssistant (optional): <String: full|compact|none> determines which search assistant to use, this trumps user preference in user model.
             *     syntaxHighlighting (optional): <String: black-white|light|dark> determines which color theme to use.
             *     autoFormat (optional): <Boolean> determines if auto-format is on, this trumps user preference in user model.
             *     forceChangeEventOnSubmit: <Boolean> If true change:search event will be triggered on the content model on submit regardless of if the search has changed. Defaults to false.
             *     submitEmptyString: <Boolean> If true the value of empty string can be set for the searchAttribute on the content model. Defaults to true.
             *     enabled: <Boolean> Determines if the input will be in a disabled or enabled state. Defaults to true. 
             *     readOnly: <Boolean> If true editor will be put in a read only mode. Set to true if enabled is false. Defaults to false.
             * }
             */
            initialize: function(options) {
                Base.prototype.initialize.apply(this, arguments);

                this.options = $.extend(true, {}, this.options, (options || {}));
                
                var defaults = {
                    useTypeahead: true,
                    showCommandHelp: true,
                    showCommandHistory: true,
                    showFieldInfo: false,
                    autoOpenAssistant: true,
                    disableOnSubmit: false,
                    submitOnBlur: true,
                    giveFocusOnRender: false,
                    maxSearchBarLines: Infinity,
                    minSearchBarLines: 1,
                    forceChangeEventOnSubmit: false,
                    enabled: true,
                    searchAttribute: 'search',
                    submitEmptyString: true,
                    readOnly: false,
                    isTabbable: true
                };
                _.defaults(this.options, defaults);
                
                if (!this.model.searchBar) {
                    this.model.searchBar = new SearchBarModel();
                }
                
                this.model.searchBar.set({'autoOpenAssistant': this.options.autoOpenAssistant});
                this.windowListenerActive = false;
                this.nameSpace = this.uniqueNS();
                
                this.initializeSearchField();

                this.activate();
            },

            initializeSearchField: function(options) {
                if (this.children.searchField) {
                    this.children.searchField.remove();
                    delete this.children.searchField;
                }
                var searchFieldOptions = $.extend(true, {}, this.options, {
                    model: {
                        user: this.model.user,
                        content: this.model.content,
                        searchBar: this.model.searchBar,
                        application: this.model.application
                    },
                    collection: {
                        searchBNFs: this.collection.searchBNFs
                    }

                });

                var useAdvancedEditor = this.options.useAdvancedEditor;
                if (_.isUndefined(useAdvancedEditor)) {
                    useAdvancedEditor = this.model.user ? 
                        this.model.user.canUseAdvancedEditor(): true;
                }

                this.children.searchField = useAdvancedEditor ?
                    new AdvancedEditorSearchField(searchFieldOptions) : new TextAreaSearchField(searchFieldOptions);
            },
            
            startListening: function() {
                this.listenTo(this.model.searchBar, 'change:assistantOpen', function() {
                    if (this.model.searchBar.get('assistantOpen')) {
                        this.$el.addClass('search-assistant-open');
                        if (!this.windowListenerActive) {
                            $(document).on('click.' + this.nameSpace, function(e) {
                                if ((e.target === this.$el[0]) || ($.contains(this.$el[0], e.target))) {
                                    return;
                                }
                                this.model.searchBar.trigger('closeAssistant');
                            }.bind(this));
                            this.windowListenerActive = true;
                        }
                    } else {
                        this.$el.removeClass('search-assistant-open');
                        $(document).off('click.' + this.nameSpace);
                        this.windowListenerActive = false;
                    }
                });

                this.listenTo(this.model.searchBar, 'change:autoOpenAssistant', function(model, value, options) {
                    this.trigger('changedAutoOpenAssistant', value);
                });

                if (this.model.user) {
                    this.listenTo(this.model.user.entry.content, 'change', function() {
                        var changed = this.model.user.entry.content.changedAttributes();
                        
                        if (_.has(changed, 'search_use_advanced_editor') && _.isUndefined(this.options.useAdvancedEditor)) {
                            this.initializeSearchField();
                            this.render();
                            // return since the render will handle updating the other changes
                            return;
                        }

                        if (_.has(changed, 'search_assistant')) {
                            this.setSearchAssistant();
                        }

                        var hasChange = _.some([
                            'search_auto_format',
                            'search_line_numbers',
                            'search_syntax_highlighting'
                        ], function(attr) { return _.has(changed, attr); });

                        if (hasChange) {
                            this.children.searchField.setEditorOptions();
                            this.setAssistantTheme();
                        }
                        
                    });
                }
            },

            activate: function(options) {
                if (this.active) {
                    return Base.prototype.activate.apply(this, arguments);
                }

                if (this.model.content.get(this.options.searchAttribute)) {
                    this.model.searchBar.set(
                        {search: this.model.content.get(this.options.searchAttribute)},
                        {skipOpenAssistant: true}
                    );
                }
                this.model.searchBar.set('autoOpenAssistant', this.options.autoOpenAssistant);

                return Base.prototype.activate.apply(this, arguments);
            },

            deactivate: function(options) {
                if (!this.active) {
                    return Base.prototype.deactivate.apply(this, arguments);
                }
                $(document).off('click.' + this.nameSpace);
                this.windowListenerActive = false;
                Base.prototype.deactivate.apply(this, arguments);
                this.model.searchBar.clear({setDefaults: true});
                return this;
            },

            /**
             * Close search assistant/auto completer whichever is applicable
             */
            closeAssistant: function() {
                this.children.searchField.closeCompleter();
                this.children.searchAssistant && this.children.searchAssistant.closeAssistant();
            },

            setSearchAssistant: function() {
                if (!_.isUndefined(this.options.searchAssistant)) {
                    this.useAssistant = this.options.searchAssistant === UserModel.SEARCH_ASSISTANT.FULL;
                    this.useAutocomplete = this.options.searchAssistant === UserModel.SEARCH_ASSISTANT.COMPACT;
                } else if (!_.isUndefined(this.options.useAssistant)) {
                    this.useAssistant = this.options.useAssistant;
                    this.useAutocomplete = !this.options.useAssistant;
                } else if (this.model.user) {
                    var assistant = this.model.user.getSearchAssistant();
                    this.useAssistant = assistant === UserModel.SEARCH_ASSISTANT.FULL;
                    this.useAutocomplete = assistant === UserModel.SEARCH_ASSISTANT.COMPACT;
                }

                this.toggleFullAssistant();
                this.children.searchField.setSearchAssistant({
                    useAssistant: this.useAssistant,
                    useAutocomplete: this.useAutocomplete
                });
            },

            toggleFullAssistant: function() {
                if (this.useAssistant && !this.options.readOnly) {
                    if (!this.children.searchAssistant) {
                        this.children.searchAssistant = new SearchAssistant($.extend(true, {}, this.options, {
                            model: {
                                searchBar: this.model.searchBar,
                                application: this.model.application
                            }
                        }));
                        this.children.searchAssistant.render().appendTo(this.$el);
                    }
                    this.setAssistantTheme();
                    this.children.searchAssistant.activate({deep: true}).$el.show();
                } else if (this.children.searchAssistant) {
                    this.children.searchAssistant.deactivate({deep: true}).$el.hide();
                }
            },

            setAssistantTheme: function() {
                if (this.children.searchAssistant) {
                    var theme = this.options.syntaxHighlighting;
                    if (!theme && this.model.user) {
                        theme = this.model.user.entry.content.get('search_syntax_highlighting');
                    }
                    this.children.searchAssistant.setTheme(theme);
                }
            },

            /**
             * Disable the input, make the search string unwritable.
             */
            disable: function() {
                this.children.searchField.disable();
                this.closeAssistant();
                this.children.searchAssistant && this.children.searchAssistant.disable();
            },

            /**
             * Enable the input, make the search string editable.
             * If option disableOnSubmit this must be called to re enable the input.
             */
            enable: function() {
                this.children.searchField.enable();
                this.children.searchAssistant && this.children.searchAssistant.enable();
            },

            /**
             * Updates the text value in the searchbar input. The text is not submitted.
             * @param {string} search
             */
            setText: function(search) {
                this.model.searchBar.set('search', search);
            },

            /**
             * Returns the text value in the searchbar input. The text is not necessarily submitted.
             * @return {string} search
             */
            getText: function() {
                return this.model.searchBar.get('search') || '';
            },

            /**
             * Adds focus to the search field.
             */
            searchFieldFocus: function() {
                this.children.searchField.searchFieldfocus();
            },

            /**
             * Removes focus from the search field.
             */
            removeSearchFieldFocus: function() {
                this.children.searchField.removeSearchFieldFocus();
            },

            /**
             * Reformats the search string in the searchbar input. This is an asynchronous function
             * which waits for the reformat functionality to be available on the editor.
             */
            reformatSearch: function() {
                this.children.searchField.reformatSearch();
            },

            /**
             * Sets the autoOpenAssistant option.
             * @param {boolean} value
             */
            setAutoOpenAssistantOption: function (value) {
                this.options.autoOpenAssistant = splunkUtils.normalizeBoolean(value);
                this.model.searchBar.set({'autoOpenAssistant': value});
            },

            setSyntaxHighlightingOption: function (value) {
                this.options.syntaxHighlighting = value;
                this.children.searchField.setEditorOptions({
                    syntaxHighlighting: this.options.syntaxHighlighting
                });
            },

            setUseAdvancedEditorOption: function(value) {
                if (this.options.useAdvancedEditor != value) {
                    this.options.useAdvancedEditor = value;
                    this.initializeSearchField();
                    this.render();
                }
            },

            /**
             * Sets the search attribute on the content model to the text value in the search bar.
             * @param {object} options {
             *     forceChangeEvent: <Boolean> Determines if a change event is triggered on submit if
             *         the search string has not changed. If set to true the event will fire.
             *         Default to the view's option forceChangeEventOnSubmit which defaults to false.
             * }
             */
            submit: function(options) {
                this.children.searchField.submit(options);
            },

            render: function() {
                this.children.searchField.render().prependTo(this.$el);
                this.setSearchAssistant();

                return this;
            }
        });
    }
);
