define(
    [
        'underscore',
        'jquery',
        'module',
        'models/datasets/Column',
        'models/datasets/commands/Base',
        'models/datasets/commands/FillValues',
        'models/datasets/commands/Replace',
        'views/Base',
        'util/keyboard'
    ],
    function(
        _,
        $,
        module,
        ColumnModel,
        BaseCommand,
        FillValuesCommand,
        ReplaceCommand,
        BaseView,
        keyboardUtil
        ) {

        return BaseView.extend({
            moduleId: module.id,

            REAL_TEXT_WRAPPER_CLASS: '.real-text-wrapper',
            REAL_TEXT_CLASS: '.real-text',
            SELECTION_TEXT_CLASS: '.selection > .highlight',

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
            },

            events: {
                'click': function(e) {
                    var isLeftClick = (e.which === 1);
                    if (isLeftClick && !$(e.currentTarget).hasClass('disabled')) {
                        this.model.state.trigger('clearSelection');
                        this.handleCellClick(e);
                    }
                },

                'dblclick': function(e) {
                    if (!$(e.currentTarget).hasClass('disabled') && !$(e.currentTarget).find('.cell-value-input').length) {
                        this.handleCellDoubleClick(e);
                    }
                }
            },

            handleCellClick: function(e) {
                var $cell = $(e.currentTarget),
                    textSelection = window.getSelection(),
                    $realTextWrapper = $cell.find(this.REAL_TEXT_WRAPPER_CLASS),
                    $realText = $realTextWrapper.find(this.REAL_TEXT_CLASS),
                    realTextElem = $realText.get(0),
                    cellValue = $realText.length ? $realText.text() : null,
                    colIndex = $cell.data('col-index'),
                    // anchorOffset is where the selection starts, focus is where it ends. We want to normalize the
                    // start and end so it doesn't matter if the user selected text by dragging leftward or rightward.
                    startPosition = Math.min(textSelection.anchorOffset, textSelection.focusOffset),
                    endPosition = Math.max(textSelection.anchorOffset, textSelection.focusOffset),
                    selectedText = textSelection.toString(),
                    focusNode = textSelection.focusNode,
                    anchorNode = textSelection.anchorNode;

                this.model.state.trigger('clearDragability');

                if (/\S/.test(selectedText) && (startPosition !== endPosition) && this.isTextSelectable() &&
                        // using mouseup so we need to make sure we are not selecting the more/less link
                        !$(e.target).is('a') &&
                        // These two statements will check that the text selection is inside of the text element
                        // and not anywhere outside of it
                        focusNode &&
                        (focusNode === realTextElem || 
                            focusNode.parentNode === realTextElem) &&
                        anchorNode &&
                        (anchorNode === realTextElem || 
                            anchorNode.parentNode === realTextElem)
                    ) {
                    this.selectText(selectedText, startPosition, endPosition);

                    this.model.state.trigger('setSelectedColumn', colIndex);

                    this.model.dataset.entry.content.set({
                        'dataset.display.selectedColumnValue': cellValue,
                        'dataset.display.selectedText': selectedText,
                        'dataset.display.selectedStart': startPosition,
                        'dataset.display.selectedEnd': endPosition,
                        'dataset.display.selectionType': 'text',
                        'dataset.display.isSelectionError': false
                    });

                } else {
                    this.handleCellSelect($cell, colIndex, cellValue);
                }
            },

            handleCellSelect: function($cell, colIndex, cellValue) {
                $cell.addClass('selected');
                this.model.state.trigger('setSelectedColumn', colIndex);

                this.model.dataset.entry.content.set({
                    'dataset.display.selectedColumnValue': cellValue,
                    'dataset.display.selectionType': 'cell',
                    'dataset.display.isSelectionError': this.$el.hasClass('mismatched-type')
                });
            },

            handleCellDoubleClick: function(e) {
                var $cell = $(e.currentTarget),
                    $realTextWrapper = this.$(this.REAL_TEXT_WRAPPER_CLASS),
                    $realText = $realTextWrapper.find(this.REAL_TEXT_CLASS),
                    $selectionText = this.$(this.SELECTION_TEXT_CLASS),
                    colIndex = $cell.data('col-index'),
                    oldCellValue = $realText.length ? $realText.text() : null,
                    selectedColId = this.model.dataset.selectedColumns.pluck('id')[0],
                    selectedCol = this.model.dataset.getCurrentCommandModel().columns.get(selectedColId),
                    selectedColType = selectedCol.get('type');

                // Prevent direct replace value of blacklisted field types
                if (_(oldCellValue).isNull()) {
                    // Use Fill Values Command blacklist
                    if (BaseCommand.isTypeBlacklisted(selectedColType, FillValuesCommand.blacklist, BaseCommand.SELECTION.COLUMN)) {
                        return;
                    }
                } else {
                    // use Replace Command blacklist
                    if (BaseCommand.isTypeBlacklisted(selectedColType, ReplaceCommand.blacklist, BaseCommand.SELECTION.COLUMN)) {
                        return;
                    }
                }
                
                // SPL-146401: Remove text selection for editable cell.
                if ($selectionText.length) {
                    this.handleCellSelect($cell, colIndex, oldCellValue);
                    $selectionText.remove();
                }

                this.renderValueInput(oldCellValue);
            },

            renderValueInput: function(oldCellValue, newCellValue) {
                var $realTextWrapper = this.$(this.REAL_TEXT_WRAPPER_CLASS),
                    triggerDirectReplaceValue = _.bind(function(e) {
                        var newCellValue = e.target.value;
                        // Do not apply new command if user did not change value (including when cell is null aka. empty textbox)
                        if (oldCellValue === newCellValue || (_(oldCellValue).isNull() && newCellValue === "")) {
                            $realTextWrapper.css('display', '');
                            $newValueInput.remove();
                        } else {
                            this.model.state.trigger('directReplaceValue', oldCellValue, newCellValue, this.$el.data('col-index'));
                        }
                    }, this),
                    startingCellValue = _.isUndefined(newCellValue) ? oldCellValue : newCellValue,
                    $newValueInput;

                if (this.$('.cell-value-input').length) {
                    this.$('.cell-value-input').remove();
                }

                $realTextWrapper.hide();
                $newValueInput = $('<input type="text" class="cell-value-input" onfocus="this.value = this.value;">');
                $newValueInput.prependTo(this.$el).focus().val(startingCellValue);

                $newValueInput.off('blur').on('blur', _.bind(function(e) {
                    triggerDirectReplaceValue(e);
                }, this));

                $newValueInput.off('keyup').on('keyup', _.bind(function(e) {
                    // if Enter key, then handle as submit action
                    if (e.which === keyboardUtil.KEYS["ENTER"]) {
                        triggerDirectReplaceValue(e);
                    }
                }, this));
            },

            selectText: function(selectedText, startPosition, endPosition) {
                var $cell = this.$el,
                    $realTextWrapper = $cell.find(this.REAL_TEXT_WRAPPER_CLASS),
                    $realText = $realTextWrapper.find(this.REAL_TEXT_CLASS),
                    cellValue = $realText.text(),
                    newHtml = _.template(this.highlightedTemplate, {
                        startValue: cellValue.substr(0, startPosition),
                        selectedText: selectedText,
                        endValue: cellValue.substr(endPosition)
                    });

                $cell.addClass('text-selected');
                $cell.find('div.selection-container').prepend('<span class="selection"></span>');
                $cell.find('div span.selection').html(newHtml);
            },

            isTextSelectable: function() {
                var columnModel = this.model.column,
                    type = columnModel.get('type');

                return !this.model.cell.isNull() && !(columnModel.isEpochTime() ||
                    type === ColumnModel.TYPES.NUMBER ||
                    type === ColumnModel.TYPES.BOOLEAN);
            },

            render: function() {
                this.$el.html(this.compiledTemplate({
                    result: this.result
                }));
                return this;
            },

            template: '<div class="selection-container"><div class="' + this.REAL_TEXT_WRAPPER_CLASS + '"><span class="' + this.REAL_TEXT_CLASS + '"><%- result %></span></div></div>',

            highlightedTemplate: '<%- startValue %><span class="highlight"><%- selectedText %></span><%- endValue %>'
        });
    }
);


