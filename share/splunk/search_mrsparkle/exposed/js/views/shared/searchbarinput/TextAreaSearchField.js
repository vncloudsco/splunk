define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/delegates/TextareaResize',
        'util/keyboard',
        'util/dom_utils',
        'helpers/Printer',
        'splunk.util',
        'jquery.resize',
        './TextAreaSearchField.pcss'
    ],
    function($, _, module, Base, TextareaResize, keyboard_utils, dom_utils, Printer, splunkUtils, jquery_resize) {
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
                this.multiline = false;
                this.useSyntheticPlaceholder = !dom_utils.supportsNativePlaceholder();
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
                
                this.listenTo(this.model.content, 'change:search', function() {
                    this.setSearchString(this.model.content.get(this.options.searchAttribute) || "");
                });

                this.listenTo(this.model.searchBar, 'setCaretPositionToEnd', this.setCaretPositionToEnd);

                this.$el.on('elementResize', function(e) {
                    if (this.children.resize) {
                        this.children.resize.debouncedResizeTextarea();
                    }
                    this.invalidateReflow();
                }.bind(this));

                this.listenTo(this.model.searchBar, 'resize', function() {
                    if (this.children.resize) {
                        this.children.resize.debouncedResizeTextarea();
                    }
                });
            },

            events: {
                'input textarea': function(e) {
                    // Fix for SPL-102359, IE 10/11 fires input event when search bar is focused.
                    if (this.model.searchBar.get('search') === undefined && this.$(".search-field").val() === "") {
                        return;
                    }
                    this.model.searchBar.set({search: this.$(".search-field").val()});
                    this.updatePlaceholder();
                },
                'propertychange .search-field': function(e) {
                    this.updatePlaceholder();
                },
                'click .placeholder': function(e) {
                    //can only happen if you are using the synthetic placeholder when no HTML5 support
                    this.$(".search-field").focus(); 
                },
                'mouseup textarea': function(e) { //could result in pasted text
                    this.updatePlaceholder();
                },
                'focus .search-field' : function(e) {
                    this.model.searchBar.set('assistantCursor', - 1);
                },
                'blur .search-field': function(e) {
                    if (this.options.submitOnBlur) {
                        this.submit();
                    }
                },
                'keydown .search-field' : 'onSearchFieldKeyDown'
            },
            
            onSearchFieldKeyDown: function(e) {
                if (!e.metaKey && !e.ctrlKey) {
                    switch (e.keyCode) {
                        case keyboard_utils.KEYS['DOWN_ARROW']:
                            // Left bracket and down arrow register as 40. If the shift key is down, then it must be a bracket.
                            if (this._useAssistant && !e.shiftKey) {
                                if (this.children.resize.isCaretLastPos(dom_utils.getCaretPosition(e.currentTarget))) {
                                    this.model.searchBar.trigger('openOrEnterAssistant');
                                    e.preventDefault();
                                }
                            }
                            break;
                        case keyboard_utils.KEYS['ENTER']:
                            if (e.shiftKey) {
                                return;
                            }
                            this.submit();
                            e.preventDefault();
                            break;
                        case keyboard_utils.KEYS['TAB']:
                            if (e.shiftKey) {
                                this.model.searchBar.trigger('closeAssistant');
                            }
                            break;
                        default:
                            break;
                    }
                }
            },

            activate: function(options) {
                if (this.active) {
                    return Base.prototype.activate.apply(this, arguments);
                }
                
                if (this.$el.html()) {
                    this.setSearchString(this.model.searchBar.get('search'));
                }

                return Base.prototype.activate.apply(this, arguments);
            },

            deactivate: function(options) {
                if (!this.active) {
                    return Base.prototype.deactivate.apply(this, arguments);
                }
                Base.prototype.deactivate.apply(this, arguments);
                this.$el.off('elementResize');
                return this;
            },

            disable: function() {
                this._disabled = true;
                this.$(".search-field").attr('disabled', true);
            },

            enable: function() {
                this._disabled = false;
                this.$(".search-field").attr('disabled', false);
                this._setReadOnly(this.options.readOnly);
            },

            _setReadOnly: function (value) {
                var searchField = this.$(".search-field").get(0);
                if (searchField) {
                    this.$(".search-field").get(0).readOnly = value;
                }
            },

            setEditorTabbable: function(value) {
                value = value === false ? value : true;
                var $searchField = this.$(".search-field");
                if ($searchField) {
                    value ? $searchField.removeAttr('tabindex') : $searchField.attr('tabindex', -1);
                }
            },

            updatePlaceholder: function() {
                if (this.useSyntheticPlaceholder) {
                    if (!this.$placeholder) {
                        this.$placeholder = this.$(".placeholder");
                    }
                    this.$placeholder[this.$(".search-field").val() === '' ? 'show' : 'hide']();
                }
            },

            submit: function(options) {
                var $searchField  = this.$(".search-field");
                if ($searchField && !$searchField.readOnly) {
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

                // don't do anything if there's nothing in the search box
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
                var currentVal = this.$(".search-field").val() || '';
                this.model.searchBar.set('search', search);
                if (search !== currentVal) {
                    this.$(".search-field").val(search);
                    this.updatePlaceholder();
                    if (this.children.resize) {
                        this.children.resize.debouncedResizeTextarea();
                    }
                }
            },

            getSearchFieldValue: function(){
                return $.trim(this.$(".search-field").val());
            },

            searchFieldfocus: function() {
                var $searchField = this.$(".search-field");
                if (!$searchField.attr('disabled')) {
                    $searchField.focus();
                }
            },

            removeSearchFieldFocus: function() {
                this.$(".search-field").blur();
            },

            setCaretPositionToEnd: function() {
                var $searchField = this.$(".search-field");
                dom_utils.setCaretPosition($searchField.get(0), $searchField.val().length);                
            },

            reformatSearch: function() {
                return;
            },

            closeCompleter: function() {
                return;
            },
 
            setEditorOptions: function(options) {
                // this editor doesn't have any options to set
                return;
            },

            /**
             * setSearchAssistant enable/disable auto-completion.
             * @param  {Object} options. e.g, {useAssistant: true, useAutocomplete: false}
             */
            setSearchAssistant: function(options) {
                this._useAssistant = splunkUtils.normalizeBoolean(options.useAssistant);
            },

            render: function() {
                var $searchField;
                if (this.$el.html()) {
                    $searchField = this.$(".search-field");
                    this.$(".search-field").val(this.model.searchBar.get('search'));
                } else {
                    var template = _.template(this.template, {
                        placeholder: _("enter search here...").t(),
                        useSyntheticPlaceholder: this.useSyntheticPlaceholder,
                        inputValue: this.model.searchBar.get('search')
                    });
                    this.$el.html(template);
                    $searchField = this.$(".search-field");
                    _.defer(function(){
                        if (this.options.useAutoFocus) {
                            this.searchFieldfocus();
                        }
                        var maxLines = Math.floor(($(window).height() - 100) / parseInt($searchField.css('lineHeight'), 10));
                        this.children.resize = new TextareaResize({el: $searchField.get(0), maxLines: maxLines, minHeight: 20});
                        this.setCaretPositionToEnd();
                    }.bind(this));
                }
                this._disabled ? this.disable() : this.enable();

                this.updatePlaceholder();
                
                if (this.children.resize) {
                    this.children.resize.resizeTextarea();
                }
                
                return this;
            },

            remove: function() {
                this.$el.off('elementResize');
                return Base.prototype.remove.apply(this, arguments);
            },

            template: '\
                <textarea aria-label="<%- _("Search").t() %>"rows="1" name="q" spellcheck="false" class="search-field" autocorrect="off" autocapitalize="off"\
                <% if (!useSyntheticPlaceholder) { %> placeholder="<%- placeholder %>"<% } %>><%- inputValue %></textarea>\
                <% if (useSyntheticPlaceholder) { %> \
                <span class="placeholder"><%- placeholder %></span>\
                <% } %>\
                '
        });
    }
);
