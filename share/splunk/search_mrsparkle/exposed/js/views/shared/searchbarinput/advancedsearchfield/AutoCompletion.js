define([
    'jquery',
    'underscore',
    'ace/ace',
    'views/shared/delegates/Base',
    'models/search/SHelper',
    'uri/route',
    'splunk.util',
    'util/string_utils',
    'ace/spl_tools',
    'bootstrap.tooltip'
],function($, _, Ace, DelegateBase, SHelperModel, route, splunk_utils, string_utils) {
    return DelegateBase.extend({
        initialize: function(options) {
            this.editor = this.options.editor;
            this.useAutocomplete = this.options.useAutocomplete;
            this.model.sHelper = new SHelperModel();

            // Create a completer
            this.searchHelperCompleter = this.createCompleter();
        },

        enable: function() {
            this.editor.setOptions({
                enableSplLiveAutocompletion: [this.searchHelperCompleter],
                extraTooltipForAutoCompletion: this.handleExtraTooltip.bind(this)
            });
        },

        disable: function() {
            this.editor.setOptions({
                enableSplLiveAutocompletion: false,
                extraTooltipForAutoCompletion: false
            });
        },

        /**
         * handleExtraTooltip will be passed to editor for showing a tooltip of the trimmed option
         * @param  {Object} popup  Completion popup
         * @param  {Number} row   Row of the selected/hovered option
         */
        handleExtraTooltip: function(popup, row) {
            if (this.$preTooltip) {
                this.$preTooltip.tooltip('destroy');
                this.$preTooltip = null;
            }

            if (!popup || !popup.isOpen || row < 0) {
                return;
            }

            var item = popup.data && popup.data[row];
            if (item && item.value && (item.value !== item.caption)) {
                var t = popup.renderer.$textLayer,
                    node = t.element.childNodes[row - t.config.firstRow],
                    $node = $(node);

                $node.tooltip({
                    animation: false,
                    trigger: 'manual',
                    title: item.value,
                    container: 'body',
                    placement: 'right'
                }).tooltip("show");
                this.$preTooltip = $node;
            }
        },

        /**
         * createCompleter will create a object which has a function for gathering all avaliable completion options
         * , and another function for generating tooltip content for the selected/hovered option.
         */
        createCompleter: function() {
            var Range = Ace.require('ace/range').Range;
            return {
                getCompletions: function(editor, session, pos, prefix, callback) {
                    var cursorPosition = editor.selection.getCursor(),
                        range = new Range(0, 0, cursorPosition.row, cursorPosition.column),
                        searchString = session.getTextRange(range),
                        deferred = this.fetchSearchHelper(searchString),
                        token = editor.session.getTokenAt(cursorPosition.row, cursorPosition.column);

                    deferred.done(function() {
                        var completions = [];
                        
                        if (!token || token.type !== "quoted") {
                            this.addNextCommands(completions);
                            this.addCommandArgs(completions);
                            this.addCommandHistory(completions);
                        }

                        // SPL-133160: Search term can be field value pair or just value. 
                        // Suggestion shows up when user edits the value.
                        // 1. When editing value within a quoted string, no suggestion shows up if
                        //    having whitespace ahead of cursor.
                        // 2. When user edits value for a field, suggestion shows up only if
                        //    field syntax matches "field=", "field= ", "field =", or "field = ".
                        range.setStart(cursorPosition.row, 0);
                        var leftOfCursor = session.getTextRange(range);
                        if (token && token.type === "quoted") {
                            if (token.value[0] === "\"" && /\S$/.test(leftOfCursor)) {
                                var leftOfToken = leftOfCursor.substring(0, token.start);
                                // Check if "=" is ahead of token.
                                if (/=\s*$/.test(leftOfToken)) {
                                    // Only "field=", "field = ", "field =" are valid cases.
                                    if (/\w ?= ?$/.test(leftOfToken)) {
                                        this.addMatchingTerms(completions);
                                    }
                                // Check if cursor is immediately after a quote.
                                } else if (!/[^\\]"$/.test(leftOfCursor)){
                                    this.addMatchingTerms(completions);
                                }
                            }
                        } else if (token && 
                            (/[^\s=]$/.test(leftOfCursor) || /\w ?= ?$/.test(leftOfCursor))) {
                            this.addMatchingTerms(completions); 
                        }
                        
                        this.addMatchingSearches(completions);
                        
                        callback(null, completions);
                    }.bind(this));

                    deferred.fail(function() {
                        callback(null, []);
                    });
                }.bind(this),
                getDocTooltip: function(item) {
                    if (item.docHTML) {
                        return;
                    }
                    if (item.type === "next" || item.type.indexOf("command") !== -1) {
                        if (!item.command.shortDesc && !item.command.example) {
                            item.docHTML = "";
                        } else {
                            var command = item.command;
                            command['learnMoreLink'] = route.docHelp(
                                this.model.application.get("root"),
                                this.model.application.get("locale"),
                                'search_app.assist.' + command.name
                            );
                            item.docHTML = _.template(this.templateForCommand, command);
                        }
                    } else {
                        item.docHTML = item.value;
                    }
                }.bind(this)
            };
        },

        /**
         * addNextCommands gets avaliable commands from sHelper model and add them to completions array
         * @param  {Object} completions  An array of all available options
         */
        addNextCommands: function(completions) {
            var commonNextCommands = this.model.sHelper.get('commonNextCommands') || [],
                commandErrors = this.model.sHelper.get('commandErrors') || [],
                typedCommand = commandErrors.length > 0 ? commandErrors[0]['unknown'] : '',
                escaped = splunk_utils.escapeRegex(typedCommand),
                regex = new RegExp(escaped);

            commonNextCommands.map(function(item){
                if (item.nextCommand !== "test" && (!typedCommand || regex.test(item.nextCommand))) {
                    var commandModel = this.collection.searchBNFs.findByEntryName(item.nextCommand + '-command'),
                        name = commandModel && commandModel.entry.get('name').replace(/-command$/, ''),
                        example = commandModel && commandModel.getOneExample(),
                        shortDesc = commandModel && commandModel.getShortDescription();
                        
                    completions.push({
                        value: item.nextCommand,
                        replacement: ' ' + item.nextCommand + ' ',
                        meta: _("Command").t(),
                        type: "next",
                        command: {
                            name: name || item.nextCommand,
                            shortDesc: shortDesc || item.description,
                            example: example
                        },
                        completer: {
                            insertMatch: this.insertMatchForCommand.bind(this)
                        }
                    });
                }
            }.bind(this));
        },

        /**
         * addCommandArgs gets command arguments, arguments values or value type from sHelper model and add
         * them to completions array
         * @param  {Object} completions  A array of all available options
         */
        addCommandArgs: function(completions) {
            var commandArgs = this.model.sHelper.get('commandArgs') || [],
                name = this.model.sHelper.command.get("name") || "",
                shortDesc = this.model.sHelper.command.get("shortdesc"),
                examples = this.model.sHelper.command.get("examples"),
                example = (examples && examples.length > 0) && examples[0][0];

            commandArgs.map(function(item) {
                if (item.valueChoice && item.valueChoice.length > 0) {
                    var valueChoice = item.valueChoice;
                    valueChoice.map(function(value){
                        completions.push({
                            value: value,
                            replacement: item.replacement + value + ' ', // Insert it to search string
                            relatedArg: item.arg,
                            meta: _("Command Args").t(), 
                            type: "commandArgs",
                            command: {
                                name: name,
                                shortDesc: shortDesc,
                                example: example
                            },
                            completer: {
                                insertMatch: this.insertMatchForArgValue.bind(this)
                            }
                        });
                    }.bind(this));
                } else if (item.valueType) {
                    completions.push({
                        value: item.valueType,
                        meta: _("Command Args").t(),
                        type: "commandArgs",
                        command: {
                            name: name,
                            shortDesc: shortDesc,
                            example: example
                        },
                        completer: {
                            insertMatch: function(){}
                        }
                    });
                } else {
                    var matchingSearch = this.model.sHelper.get('matchingSearch'),
                        escaped = splunk_utils.escapeRegex(item.replacement),
                        regex = new RegExp(escaped + "$");

                    if (!regex.test(matchingSearch)) {
                        completions.push({
                            relatedArg: item.arg,
                            value: item.replacement,
                            replacement: item.replacement,
                            meta: _("Command Args").t(),
                            type: "commandArgs",
                            command: {
                                name: name,
                                shortDesc: shortDesc,
                                example: example
                            },
                            completer: {
                                insertMatch: this.insertMatchForArg.bind(this),
                                keepPopupAfterInsert: true //After inserts a matched search, keep completion popup open 
                            }
                        });
                    }
                }
            }.bind(this));
        },

        /**
         * addCommandHistory gets history of a specific command from sHelper model and add 
         * them to completions array.
         * @param  {Object} completions  A array of all available options
         */
        addCommandHistory: function(completions) {
            var commandHistory = _.first(this.model.sHelper.get("commandHistory") || [], 
                this.model.sHelper.MAX_COMMAND_HISTORY),
                name = this.model.sHelper.command.get("name") || "",
                shortDesc = this.model.sHelper.command.get("shortdesc"),
                examples = this.model.sHelper.command.get("examples"),
                example = (examples && examples.length > 0) && examples[0][0];

            commandHistory.map(function(item) {
                item.arg = item.arg.trim();
                item.arg = string_utils.removeNewlines(item.arg);
                completions.push({
                    value: splunk_utils.sprintf("%s %s", name, item.arg),
                    replacement: item.replacement.trim() + ' ',
                    command: {
                        name:name,
                        shortDesc: shortDesc,
                        example: example
                    },
                    meta: _("Command History").t(),
                    type: "command",
                    completer: {
                        insertMatch: this.insertMatchForHistory.bind(this)
                    }
                });
            }.bind(this));
        },

        /**
         * addMatchingTerms gets terms which match user input from sHelper model and add them 
         * to completions array
         * @param  {Object} completions  A array of all available options
         */
        addMatchingTerms: function(completions) {
            var matchingTerms = _.first(this.model.sHelper.get("matchingTerms") || [], 
                this.model.sHelper.MAX_MATCHING_TERMS),
                mainSearch = this.model.sHelper.get("matchingSearch") || "";

            mainSearch = mainSearch.trim();
            matchingTerms.map(function(item){
                item.term = item.term.trim();
                if (item.term !== mainSearch) {
                    completions.push({
                        value: item.term,
                        replacement: item.term + ' ', //SPL-122778: item.replacement is not always correct. Use term itself to replace.
                        meta: _("Matching Term").t(),
                        type: "term",
                        completer: {
                            insertMatch: this.insertMatchForTerm.bind(this)
                        },
                        hideDocTooltip: true
                    }); 
                }
            }.bind(this));
        },

        /**
         * addMatchingSearches gets full searches which match user input from sHelper model 
         * and add them to completions array.
         * @param  {Object} completions  A array of all available options
         */
        addMatchingSearches: function(completions) {
            var matchingSearches = _.first(this.model.sHelper.get("matchingSearches") || [], 
                this.model.sHelper.MAX_MATCHING_SEARCHES),
                mainSearch = this.model.sHelper.get("matchingSearch") || "",
                escaped = splunk_utils.escapeRegex(mainSearch),
                regex = new RegExp("^" + escaped);

            mainSearch = mainSearch.trim();
            matchingSearches.map(function(item) {
                item = item.trim();
                item = string_utils.removeNewlines(item);
                if (item !== mainSearch && regex.test(item)) {
                    completions.push({
                        value: item,
                        replacement: item + ' ',
                        meta: _("Matching Search").t(),
                        type: "search",
                        completer: {
                            insertMatch: this.insertMatchForSearch.bind(this)
                        },
                        hideDocTooltip: true
                    });
                }
            }.bind(this));
        },

        /**
         * insertMatchForCommand handles the insertion of a command name. 
         * @param {Object} editor  Ace editor
         * @param {Object} data  The selected command option
         */
        insertMatchForCommand: function(editor, data) {
            // Find the pipe for this command, and the current token the cursor is in.
            var cursorRange = editor.selection.getRange(),
                pipeRange = editor.find('|', {
                    backwards: true,
                    start: cursorRange
                }),
                token = editor.session.getTokenAt(cursorRange.start.row, cursorRange.start.column);

            // Set start position of the cursor range to be the end position of the pipe.
            cursorRange.setStart(pipeRange.end.row, pipeRange.end.column);

            if (token) {
                 // Find the first whitespace on the right side of the cursor within the token.
                 // If it exists, set end position of the cursor range to the poisiton of this whitespace.
                 // Otherwise, the end position will be the end poisiton of the token.
                var rightOfCursor = token.value.substring(cursorRange.end.column - token.start),
                    matches = rightOfCursor.match(/\s/);
                if (matches) {
                    cursorRange.setEnd(cursorRange.end.row, cursorRange.end.column + matches.index);
                } else {
                    cursorRange.setEnd(cursorRange.end.row, token.start + token.value.length);
                }
            } 

            editor.session.replace(cursorRange, data.replacement);
            editor.clearSelection();
        },

        /**
         * insertMatchForHistory handles the insertion of a command history. 
         * @param {Object} editor  Ace editor
         * @param {Object} data  The selected history option
         */
        insertMatchForHistory: function(editor, data) {
            var TokenIterator = Ace.require('ace/token_iterator').TokenIterator,
                cursorPosition = editor.getCursorPosition(),
                iter = new TokenIterator(editor.session, cursorPosition.row, cursorPosition.column),
                subsearchOpen = 0,
                token,
                position,
                endPosition;

            while (iter.stepForward()) {
                token = iter.getCurrentToken();
                position = iter.getCurrentTokenPosition();

                if (token.type === "subsearch" && token.value === "[") {
                    subsearchOpen += 1;
                } 

                if (token.type === "subsearch" && token.value[0] === "]") {
                    // If number of open bracket of subsearches is less than the token.value.length,
                    // it means this command is inside a subsearch.
                    // We find the close bracket of a subsearch earlier than the next pipe
                    if (token.value.length > subsearchOpen) {
                        endPosition = position;
                        endPosition.column += subsearchOpen;
                        break;
                    } else {
                        subsearchOpen -= token.value.length; 
                    }
                }

                // This will be the start of next command.
                if (token.type === "pipe" && subsearchOpen === 0) {
                    endPosition = position;
                    break;
                }
            }

            if (endPosition) {
                editor.selection.moveCursorToPosition(endPosition); 
            } else {
                editor.selection.moveCursorFileEnd();
            }
            editor.selection.selectFileStart();
            editor.insert(data.replacement);
        },

        /**
         * insertMatchForArg handles the insertion of a command argument. 
         * @param {Object} editor  Ace editor
         * @param {Object} data  The selected argument option
         * e.g, if user inputs "| top li", and selects "limit=" from completion list,
         * it will find substring "li", and replace it with "limit=".
         */
        insertMatchForArg: function(editor, data) {
            var cursorPosition = editor.getCursorPosition(),
                token = editor.session.getTokenAt(cursorPosition.row, cursorPosition.column),
                line = editor.session.doc.getLine(cursorPosition.row),
                value = data.replacement,
                start = token ? token.start : cursorPosition.column,
                end = token ? (token.start + token.value.length) : cursorPosition.column;
                 
            if (token && token.type !== "quoted") {
                start = cursorPosition.column - data.relatedArg.length;
                
                if (cursorPosition.column !== line.length) {
                    var rightOfStart = line.substring(start),
                        rex = new RegExp('^'+ data.relatedArg + '[^=(\\s]*(?:=(\\w*)|(\\(\\w*\\)?))?'),
                        matches = rightOfStart.match(rex);
                    // If user has already typed a value for this argument
                    if (matches[1] || matches[2]) {
                        value += matches[1] || matches[2];
                    }
                    end = start + matches[0].length;
                } else {
                    end = cursorPosition.column;
                }
            }

            editor.selection.moveCursorToPosition({row: cursorPosition.row, column: start});
            editor.selection.selectToPosition({row: cursorPosition.row, column: end});
            editor.insert(value);
        },

        /**
         * insertMatchForArgValue handles the insertion of a command argument value. 
         * @param {Object} editor  Ace editor
         * @param {Object} data  The selected argument value option
         */
        insertMatchForArgValue: function(editor, data) {
            var range = editor.selection.getRange(),
                cursorPosition = editor.getCursorPosition(),
                line = editor.session.doc.getLine(cursorPosition.row),
                rightOfCursor = line.substring(cursorPosition.column),
                textRange = editor.find(data.relatedArg, {
                    backwards: true,
                    wholeWord: true,
                    start: range
                });
            // Set the start of replacement range
            range.setStart(textRange.start.row, textRange.start.column);

            // Set the end of replacement range
            var matches = /\s/.exec(rightOfCursor),
                endColumn = line.length;

            if (matches) {
                var matchesColumn = cursorPosition.column + matches.index,
                    token = editor.session.getTokenAt(cursorPosition.row, matchesColumn + 1);

                if (token) {
                    endColumn = token.type !== "invalid" ? matchesColumn + 1 : 
                        token.start + token.value.length;
                }
            }

            range.setEnd(cursorPosition.row, endColumn);
            editor.session.replace(range, data.replacement);
        },

        /**
         * insertMatchForTerm handles the insertion of a matched term.
         * @param {Object} editor  Ace editor
         * @param {Object} data  The selected matched term option
         */
        insertMatchForTerm: function(editor, data) {
            var range = editor.selection.getRange(),
                cursorPosition = editor.getCursorPosition(),
                token = editor.session.getTokenAt(cursorPosition.row, cursorPosition.column),
                line = editor.session.doc.getLine(cursorPosition.row),
                leftOfCursor = line.substring(0, cursorPosition.column),
                rightOfCursor = line.substring(cursorPosition.column),
                whitespaceRex = /\s/;
                
            if (!token) {
                editor.session.replace(range, data.replacement);
                return;
            }

            // Set left boundary of the range.
            var start, matches;
            if (token.type === "quoted") {
                var leftOfToken = leftOfCursor.substring(0, token.start);
                matches = leftOfToken.match(/(\w) ?= ?$/);
                // If matches exists, it will be one of the cases similar to 
                // "index=", "index =", or "index = ". start will be set to
                // the index of 'x'.
                start = matches? matches.index : token.start - 1;
            } else {
                matches = leftOfCursor.match(/(\w) ?= ?$/);
                start = matches ? matches.index : leftOfCursor.length - 1;
            }

            while (start > 0) {
                if (whitespaceRex.test(leftOfCursor[start])) {
                    break;
                }
                start --;
            }
            range.start.column = start > 0 ? start + 1 : 0;

            // Set right boundary of the range.
            var tokenLastIndex = token.value.length - 1;
            if (token.type === "quoted" && token.value[tokenLastIndex] === "\"") {
                range.end.column = token.start + token.value.length;
            } else {
                if (cursorPosition.column !== line.length) {
                    matches = rightOfCursor.match(whitespaceRex);
                    if (matches) {
                        range.end.column += matches.index;
                    } else {
                        range.end.column = line.length;
                    }
                }
            }

            editor.session.replace(range, data.replacement);
        },

        /**
         * insertMatchForSearch handles the insertion of a matched search.
         * @param {Object} editor  Ace editor
         * @param {Object} data  The selected matched term/search option
         */
        insertMatchForSearch: function(editor, data) {
            editor.setValue(data.replacement);
            editor.clearSelection();
            if (this.options.autoFormat) {
                editor.execCommand("autoFormat");
            }
        },

        fetchSearchHelper: function(searchString) {
            var $deferred = $.Deferred();
            searchString = splunk_utils.addLeadingSearchCommand(searchString || '*', true);
            this.model.sHelper.safeFetch({
                data: {
                    'snippet': 'true',
                    'snippetEmbedJS': 'false',
                    'namespace': this.model.application.get('app') || 'search',
                    'search': searchString,
                    'useTypeahead': this.options.useTypeahead,
                    'showCommandHelp': this.options.showCommandHelp,
                    'showCommandHistory': this.options.showCommandHistory,
                    'showFieldInfo': this.options.showFieldInfo
                },
                success: function() {
                    $deferred.resolve();
                },
                error: function() {
                    $deferred.reject();
                }
            });
            return $deferred.promise();
        },

        remove: function() {
            var completer = this.editor.completer,
                popup = completer ? completer.popup : null;
            if (completer) {
                completer.detach();
            }
            if (popup) {
                popup.destroy();
                $(popup.container).remove();
            }

            return DelegateBase.prototype.remove.apply(this, arguments);
        },

        templateForCommand:'\
            <div><b><%- name %></b><a class="pull-right" href="<%= learnMoreLink %>" target="_blank"><%- _("Learn More").t()%> <i class="icon-external"></i></a></div>\
            <% if (shortDesc) {%>\
                <div class="command-intro">\
                    <div><%- _(shortDesc).t() %></div>\
                </div>\
            <% } %>\
            <% if (example) {%>\
                <div class="command-example">\
                    <%- _("Example:").t() %>\
                    <div><%- example %></div>\
                </div>\
            <% } %>\
        '
    });
});