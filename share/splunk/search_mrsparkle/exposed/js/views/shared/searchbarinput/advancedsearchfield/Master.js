define(
    [
        'jquery',
        'underscore',
        'module',
        'ace/ace',
        'ace/mode-spl',
        'views/Base',
        './AutoCompletion',
        'models/services/authentication/User',
        'util/keyboard',
        'util/general_utils',
        'helpers/Printer',
        'helpers/user_agent',
        'splunk.util',
        './Master.pcss'
    ],
    function($, _, module, Ace, ModeSpl, Base, AutoCompletion, UserModel, keyboard_utils, general_utils, Printer, userAgent, splunkUtils, css) {
        return Base.extend({
            moduleId: module.id,
            className: 'search-field-wrapper',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                this._disabled = false;
                this._useAssistant = false;
                var disableSearchField = _.isUndefined(this.options.enabled) ?
                    false : 
                    !this.options.enabled;
                if (disableSearchField) {
                    this.disable();
                }
                this.activate();
            },
            startListening: function() {
                this.listenTo(Printer, Printer.PRINT_START, this.invalidateReflow);
                this.listenTo(Printer, Printer.PRINT_END, this.invalidateReflow);

                this.listenTo(this.model.searchBar, 'searchFieldfocus', this.searchFieldfocus);

                this.listenTo(this.model.searchBar, 'change:search', function() {
                    this.setSearchString(this.model.searchBar.get('search') || "");
                });

                this.listenTo(this.model.content, 'applied', function(options) {
                    this.submit(options);
                });

                this.listenTo(this.model.content, 'change:' + this.options.searchAttribute, function() {
                    this.setSearchString(this.model.content.get(this.options.searchAttribute) || "");
                });

                this.listenTo(this.model.searchBar, 'setCaretPositionToEnd', this.setCaretPositionToEnd);

                this.listenTo(this.model.searchBar, 'reformatSearch', function() {
                    if (this.options.autoFormat) {
                        this.reformatSearch();
                    }
                });
            },

            setupEditorListeners: function() {
                this.editor.on('input', function(e) {
                    this.model.searchBar.set('search', this.editor.getValue());
                }.bind(this));

                this.editor.on('focus', function(e) {
                    this.model.searchBar.set('assistantCursor', - 1);
                    $(this.editor.container).addClass('focused');
                }.bind(this));

                this.editor.on('blur', function(e) {
                    $(this.editor.container).removeClass('focused');
                    if (this.options.submitOnBlur) {
                        this.submit();
                    }
                }.bind(this));

                // This fix can be reverted once the ace editor is updated to 1.2.6. https://github.com/ajaxorg/ace/pull/3116
                if (userAgent.getChromeVersion() >= 53 || userAgent.isIE11) {
                    var textArea = this.editor.textInput && this.editor.textInput.getElement();
                    if (textArea) {
                        $(textArea).on("compositionend", function() {
                            var inputEvent;
                            if (typeof window.Event === "function") {
                                inputEvent = new window.Event('input');
                            }
                            else if (typeof document.createEvent === "function") {
                                inputEvent = document.createEvent("Event");
                                inputEvent.initEvent("input", true, true);
                            }
                            inputEvent && textArea.dispatchEvent(inputEvent);
                        });
                    }
                }

                this.editor.keyBinding.originalOnCommandKey = this.editor.keyBinding.onCommandKey;

                //SPL-123019,SPL-125909 - Removing unused keyboard accelerator
                this.editor.commands.removeCommands({
                    "Command-L": "gotoline",
                    "Command-,": "showSettingsMenu",
                    "Ctrl-E": "goToNextError",
                    "Ctrl-Shift-E" : "goToPreviousError",
                    "Command-Shift-E" : "replaymacro"   //this shortcut is used to expand macros and saved searches
                });

                this.editor.keyBinding.onCommandKey = function(e, hashId, keyCode) {
                    var completer = this.editor.completer,
                        popup = completer && completer.popup;
                    if (!e.metaKey && !e.ctrlKey) {
                        switch (e.keyCode) {
                            case keyboard_utils.KEYS['DOWN_ARROW']:
                                // Left bracket and down arrow register as 40. If the shift key is down, then it must be a bracket.
                                if (this._useAssistant && !e.shiftKey) {
                                    if (this.editor.selection.getCursor().row + 1 === this.editor.session.getLength()) {
                                        this.model.searchBar.trigger('openOrEnterAssistant');
                                        e.preventDefault();
                                        return;
                                    }
                                }
                                break;
                            case keyboard_utils.KEYS['ENTER']:
                                if (!(popup && popup.isOpen && popup.getData(popup.getRow()))) {
                                    if (completer) {
                                        completer.detach();
                                    }
                                    if (!e.shiftKey) {
                                        this.submit();
                                        e.preventDefault();
                                        return;
                                    }
                                }
                                break;
                            case keyboard_utils.KEYS['TAB']:
                                if (!(popup && popup.isOpen && popup.getData(popup.getRow()))) {
                                    if (e.shiftKey) {
                                        this.model.searchBar.trigger('closeAssistant');
                                    }
                                    return;
                                }
                                break;
                            default:
                                break;
                        }
                    }
                    if (e.which === keyboard_utils.KEYS['F'] &&
                        (e.metaKey || e.ctrlKey) &&
                        !e.shiftKey &&
                        (this.editor.session.getLength() === 1 && this.editor.session.getRowWrapIndent() === 0)) {
                        //SPL-123020 Remove find key binding for single line searches.
                        return;
                    }
                    this.editor.keyBinding.originalOnCommandKey(e, hashId, keyCode);
                }.bind(this);

                var reformatCommand = {
                    name: "autoFormat",
                    bindKey: {win: 'Ctrl-\\|Ctrl-Shift-F', mac: 'Command-\\|Command-Shift-F'},
                    exec: function(editor) {
                        editor.reformatSearch();
                    },
                    readOnly: false
                };

                this.editor.commands.addCommand(reformatCommand);

                var update = function() {
                    var shouldShow = !(this.editor.getValue() || "").length;
                    var node = this.editor.renderer.emptyMessageNode;
                    if (!shouldShow && node) {
                        this.editor.renderer.scroller.removeChild(this.editor.renderer.emptyMessageNode);
                        this.editor.renderer.emptyMessageNode = null;
                    } else if (shouldShow && !node) {
                        node = this.editor.renderer.emptyMessageNode = document.createElement("div");
                        node.textContent = _("enter search here...").t();
                        node.className = "ace_invisible ace_emptyMessage";
                        this.editor.renderer.scroller.appendChild(node);
                    }
                }.bind(this);
                this.editor.on("input", update);
                setTimeout(update, 100);
            },

            activate: function(options) {
                if (this.active) {
                    return Base.prototype.activate.apply(this, arguments);
                }

                if (this.editor) {
                    this.setSearchString(this.model.searchBar.get('search'));
                }

                return Base.prototype.activate.apply(this, arguments);
            },

            disable: function () {
                this._disabled = true;
                if (this.editor) {
                    this._setReadOnly(true);
                    this.editor.setStyle('disabled');
                }
            },

            enable: function () {
                this._disabled = false;
                if (this.editor) {
                    this._setReadOnly(this.options.readOnly);
                    this.editor.unsetStyle('disabled');
                }
            },

            _setReadOnly: function (value) {
                if (this.editor) {
                    this.editor.setOptions({
                        readOnly: value
                    });

                    value ? this.editor.setStyle('read-only') : this.editor.unsetStyle('read-only');
                }
            },

            setEditorTabbable: function(value) {
                value = value === false ? value : true;
                if (this.editor) {
                    var $textArea = this.editor.textInput && $(this.editor.textInput.getElement());
                    value ? $textArea.removeAttr('tabindex') : $textArea.attr('tabindex', -1);
                }
            },

            /**
             * Closes the auto completer dialog if the dialog is open
             */
            closeCompleter: function() {
                if (this.editor && this.editor.completer && this.editor.completer.activated) {
                    this.editor.completer.detach();
                }
            },

            submit: function(options) {
                if (this.editor && !this.editor.getReadOnly()) {
                    this.model.searchBar.trigger('closeAssistant');
                    this._onFormSubmit(options);
                }
            },

            _onFormSubmit: function(options) {
                options = options || {};
                var defaults = {
                    forceChangeEvent: this.options.forceChangeEventOnSubmit
                };
                _.defaults(options, defaults);

                // don't do anything if there's nothing in the search box and submitEmptyString = false
                var search = this.model.searchBar.get('search'),
                    currentSearch = this.model.content.get(this.options.searchAttribute),
                    searchFromTextarea = this.getSearchFieldValue();

                if (search !== searchFromTextarea) {
                    this.model.searchBar.set('search', searchFromTextarea);
                    search = searchFromTextarea;
                }
                if (this.options.submitEmptyString || search) {
                    if (this.options.disableOnSubmit) {
                        this.disable();
                    }
                    var setData = {};
                    setData[this.options.searchAttribute] = search;
                    if (currentSearch !== search){
                        this.model.content.set(setData, options);
                    } else {
                        if (options.forceChangeEvent) {
                            this.model.content.unset(this.options.searchAttribute, {silent: true});
                            this.model.content.set(setData, options);
                        }
                    }
                }
            },

            /**
             * Sometimes, like when we're resurrecting a search, we will
             * write our own input value.
             */
            setSearchString: function(search) {
                var currentVal = (this.editor && this.editor.getValue() || '') ;
                this.model.searchBar.set('search', search);
                if (this.editor && search !== currentVal) {
                    this.editor.setValue(search || '', 1);
                }
            },

            /**
             * Calls the reformatSearch function on the editor if available.
             */
            reformatSearch: function() {
                if (this.editor && _.isFunction(this.editor.reformatSearch)) {
                    this.editor.reformatSearch();
                }
            },

            getSearchFieldValue: function(){
                return $.trim(this.editor.getValue());
            },

            searchFieldfocus: function() {
                this.editor && this.editor.focus();
            },

            removeSearchFieldFocus: function() {
                this.editor && this.editor.blur();
            },

            setCaretPositionToEnd: function() {
                this.editor && this.editor.navigateFileEnd();
            },

            /**
             * setEditorOptions trumps user preference in user model with new options passed in, and
             * set them to editor.
             * @param  {Object} options. e.g, {autoFormat: false, syntaxHighiligting: 'dark'}
             */
            setEditorOptions: function(options) {
                options = options || {};
                $.extend(this.options, options);

                var defaults = {
                        autoFormat: this.model.user ? this.model.user.getSearchAutoFormat() : false,
                        showLineNumbers: this.model.user ? this.model.user.getSearchLineNumbers() : false,
                        syntaxHighlighting: this.model.user? this.model.user.getSearchSyntaxHighlighting()
                            : UserModel.EDITOR_THEMES.DEFAULT
                    },
                    clonedOptions = $.extend(true, {}, defaults, this.options);

                this.editor.setOptions({
                    showLineNumbers: clonedOptions.showLineNumbers,
                    showGutter: clonedOptions.showLineNumbers,
                    behavioursEnabled: clonedOptions.autoFormat,
                    theme: 'ace/theme/spl-' + clonedOptions.syntaxHighlighting
                });
            },

            /**
             * setSearchAssistant enable/disable auto-completion.
             * @param  {Object} options. e.g, {useAssistant: true, useAutocomplete: false}
             */
            setSearchAssistant: function(options) {
                options = options || {};
                this._useAssistant = splunkUtils.normalizeBoolean(options.useAssistant);

                if (this.children.autoCompletion) {
                    this.children.autoCompletion[
                        splunkUtils.normalizeBoolean(options.useAutocomplete)? "enable" : "disable"
                    ]();
                }
            },

            // SPL-131215 - Dashboards use the helperModel that loads collections/models asyn. In this case we must reset the mode once the
            // searchbnfs collection's fetch is complete.
            setMode: function(module) {
                if (this.editor && module) {
                    if (this.collection.searchBNFs.dfd && this.collection.searchBNFs.dfd.state() === 'pending') {
                        this.collection.searchBNFs.dfd.done(this.setMode.bind(this, module));
                    }
                    var splMode = new module.Mode(this.collection.searchBNFs.getCommandsParsedSyntax());
                    this.editor.session.setMode(splMode);
                }
            },

            render: function() {
                if (!this.$el.html()) {
                    this.$searchField = $('<textarea class="search-field"></textarea>');
                    this.$searchField.appendTo(this.$el);
                    this.editor = Ace.edit(this.$searchField[0]);
                    this.editor.setSession(Ace.createEditSession(this.model.searchBar.get('search') || ''));
                    this.setupEditorListeners();
                    this.setMode(ModeSpl);

                    this.editor.setOptions({
                        maxLines: this.options.maxSearchBarLines,
                        wrap: true,
                        fontSize: 12,
                        highlightActiveLine: false,
                        highlightGutterLine: false,
                        showPrintMargin: false,
                        enableMultiselect: false,
                        displayIndentGuides: false,
                        minLines: this.options.minSearchBarLines
                    });

                    this.setEditorOptions();

                    // for screen readers
                    var elementID = 'id-' + general_utils.generateUUID();
                    this.$('.ace_content').attr('id', elementID);
                    this.$('textarea.ace_text-input').attr('aria-describedby', elementID);
                    this.$('textarea.ace_text-input').attr('aria-label', _('Search').t());

                    this._disabled ? this.disable() : this.enable();

                    this.editor.session.setUndoSelect(false);

                    // Disable the warning message.
                    this.editor.$blockScrolling = Infinity;

                    this.children.autoCompletion = new AutoCompletion($.extend(true, {}, this.options, {
                        editor: this.editor,
                        model: {
                            application: this.model.application
                        },
                        collection: {
                            searchBNFs: this.collection.searchBNFs
                        }
                    }));
                }

                if (this.options.giveFocusOnRender) {
                    this.searchFieldfocus();
                }
                this.setCaretPositionToEnd();

                this.setEditorTabbable(this.options.isTabbable);

                return this;
            },

            reflow: function() {
                this.editor.resize(true);
            },

            remove: function() {
                if (this.editor) {
                    this.editor.destroy();
                }
                return Base.prototype.remove.apply(this, arguments);
            }
        });
    }
);
