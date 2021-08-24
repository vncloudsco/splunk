define([
            'jquery',
            'underscore',
            'module',
            'models/config',
            'views/shared/viz/Base',
            'util/jscharting_utils',
            'util/general_utils',
            'splunk.util',
            'splunk.legend',
            'uri/route',
            '@splunk/charting'
        ],
        function(
            $,
            _,
            module,
            configModel,
            VisualizationBase,
            jschartingUtils,
            generalUtils,
            splunkUtils,
            SplunkLegend,
            route,
            splunkCharting
        ) {

    // Strings that the charting library will display, adding them here so that the extractor can find them.
    _('Invalid timestamp').t();
    _('Reset').t();
    _('Reset Zoom').t();
    _('Pan Right').t();
    _('Pan Left').t();
    _('No Results').t();
    _('Invalid Data').t();
    _('Numeric Data Required').t();
    _('Invalid data: second column must be numeric for a pie chart').t();

    jschartingUtils.prepareChartingLibrary(splunkCharting);

    var JSChart = VisualizationBase.extend({
        VIZ_PROPERTY_PREFIX_REGEX: /^display\.visualizations\.charting\./,
        className: 'chart',
        moduleId: module.id,
        initialize: function(options) {
            VisualizationBase.prototype.initialize.apply(this, arguments);
            this.options = options || {};
            this._selectedRange = null;

            this.$el.width(this.options.width || '100%');
            this.$el.height(this.options.height || '100%');

            this.$chart = $('<div></div>');
            this.$inlineMessage = $('<div></div>').css('text-align', 'center')
                .addClass(this.options.messageContainerClass || '');

            this.computeDisplayProperties();

            this.listenTo(this.getPrimaryDataSource(), 'destroy', this.empty);
            this.onExternalPaletteChange = _(this.onExternalPaletteChange).bind(this);
            this.legendId = (this.options.parentCid || '') + this.cid;
            SplunkLegend.register(this.legendId);
            SplunkLegend.addEventListener('labelIndexMapChanged', this.onExternalPaletteChange);
        },
        empty:  function() {
            this.destroyChart();
            this.$chart.empty();
            this.$inlineMessage.empty();
            return this;
        },
        remove: function() {
            this.removed = true;
            this.destroyChart();
            SplunkLegend.unregister(this.legendId);
            SplunkLegend.removeEventListener('labelIndexMapChanged', this.onExternalPaletteChange);
            return VisualizationBase.prototype.remove.apply(this, arguments);
        },
        render: function() {
            this.$chart.appendTo(this.el);
            this.$inlineMessage.appendTo(this.el);
            return VisualizationBase.prototype.render.apply(this, arguments);
        },

        onConfigChange: function(changedAttributes) {
            var updateNeeded = _(changedAttributes).chain().keys()
                .any(function(key) {
                    return key.indexOf('display.visualizations.charting.') === 0;
                })
                .value();

            if (!updateNeeded) {
                return;
            }
            this.computeDisplayProperties();

            // Any config attributes used (directly or indirectly) by the formatData method below
            // should be in this list.  By checking for these attributes in what has changed,
            // we can decide whether to reformat the data or just re-update the view.
            var dataRelevantConfigAttributes = [
                'display.visualizations.charting.chart',
                'display.visualizations.charting.chart.resultTruncationLimit',
                'display.visualizations.charting.resultTruncationLimit',
                'display.visualizations.charting.axisY2.enabled',
                'display.visualizations.charting.chart.overlayFields',
                'display.visualizations.charting.chart.stackMode'
            ];
            var formatDataNeeded = _(changedAttributes).any(function(value, key) {
                return _(dataRelevantConfigAttributes).contains(key);
            });
            if (formatDataNeeded) {
                this.invalidate('formatDataPass');
            } else {
                this.invalidate('updateViewPass');
            }
        },
        combineData: function(dataFromAllSources) {
            return _.extend({}, dataFromAllSources.primary, {
                annotation: dataFromAllSources.annotation
            });
        },
        formatData: function(combinedData) {
            if (!combinedData || !combinedData.columns || combinedData.columns.length === 0) {
                return splunkCharting.extractChartReadyData({fields:[], columns:[]});
            }
            var results = jschartingUtils.preprocessChartData(combinedData, this.displayProperties);
            // if the preprocessChartData method truncated the data, add a flag to the formatted results
            if(results.columns.length > 0 &&
                    (results.columns.length < combinedData.columns.length ||
                        results.columns[0].length < combinedData.columns[0].length)) {
                results.areTruncated = true;
            }

            if (combinedData.annotation) {
                // format annotation data if there's any
                results.annotations = this.formatAnnotationData(combinedData.annotation);
            }

            var resultsDataSet = splunkCharting.extractChartReadyData(results);

            if (results.areTruncated) {
                resultsDataSet.resultsAreTruncated = true;
            }
            // this is used to extract visual regression test cases easier
            // read more at https://git.splunk.com/users/pwied/repos/chartconfig-downloader/browse/README.md
            try {
                if (window.__splunk__prepareChartCfgDownload) {
                    window.__splunk__prepareChartCfgDownload(this.cid, JSON.stringify({ data: combinedData, props: this.displayProperties }, null, 2));
                }
            } catch(e) {
                // failed to prepare chart cfg download
            }

            return resultsDataSet;
        },
        formatAnnotationData: function(annotationData) {
            var annotations = [];
            if (annotationData && annotationData.columns && annotationData.columns.length > 0) {
                var annotationDataSet = splunkCharting.extractChartReadyData(annotationData);
                if (annotationDataSet.hasField('_time')) {
                    var timeList = annotationDataSet.getSeriesAsTimestamps('_time');
                    var labelList = annotationDataSet.getSeries('annotation_label');
                    var colorList = annotationDataSet.getSeries('annotation_color');
                    var categoryList = annotationDataSet.getSeries('annotation_category');
                    _.each(timeList, function (time, index) {
                        annotations.push({
                            time: time,
                            label: labelList[index],
                            color: colorList[index],
                            category: categoryList[index]
                        });
                    }, this);
                }
            }
            return annotations;
        },
        provideScaleValues: function(dataSet, config){
            if(dataSet.seriesList && dataSet.seriesList.length > 1) {
                var fields = dataSet.getFieldData();

                var yAxisFields = fields.yFields;

                // If in overlay mode, we split the scale
                if (splunkUtils.normalizeBoolean(config['display.visualizations.charting.axisY2.enabled'])){
                    var overlayFields = splunkUtils.stringToFieldList(
                            config['display.visualizations.charting.chart.overlayFields']
                        );
                    // Set up overlay data
                    var overlayData = [];
                    _.each(overlayFields, function(field) {
                        var index = _.indexOf(dataSet.fields, field);
                        if(index > -1 ) {
                            overlayData = overlayData.concat(dataSet.seriesList[index]);
                        }
                    });
                    yAxisFields = _.difference(fields.yFields, overlayFields);
                }

                // Set up main y axis data
                var yAxisData = [];
                var maxValues = [];
                _.each(yAxisFields, function(field) {
                    var index = _.indexOf(dataSet.fields, field);
                    if(index > -1 ) {
                        yAxisData = yAxisData.concat(dataSet.seriesList[index]);
                        maxValues.push(_.max(dataSet.getSeriesAsFloats(field)));
                    }
                });

                // Series max values are combined to find the max in stacked mode
                if (config['display.visualizations.charting.chart.stackMode'] === 'stacked'){
                    var maxValue = _.reduce(maxValues, function(memo, num){
                        return memo + num;
                    }, 0);
                    yAxisData.push(maxValue);
                }

                var xAxisData = [];
                _.each(fields.xFields, function(field){
                    var index = _.indexOf(dataSet.fields, field);
                    if(index > -1 ) {
                        xAxisData = xAxisData.concat(dataSet.seriesList[index]);
                    }
                });

                return {
                    xAxis: xAxisData,
                    yAxis: yAxisData,
                    overlayAxis: overlayData
                };
            }
        },

        // The initial version of updateView performs the lazy loading of the charting library source code.
        // Once the load is complete, the updateView method is reassigned to point to the _updateViewAfterLoad
        // method below.  Any subsequent calls to updateView will actually call _updateViewAfterLoad.
        updateView: function(dataSet, config, async) {
            var done = async();
            if(_.isUndefined(dataSet.seriesList)) {
                return;
            }
            // SPL-181033: update timezone before re-render the view.
            // Can not do this where user preference is updated,
            // because other class may use custom timezone settings.
            splunkCharting.setTimezone(configModel.get('SERVER_ZONEINFO'));
            this.$inlineMessage.empty();

            var maxResultCount = this.getPrimaryDataSource().getFetchParams().count;
            // If the formatData method truncated the data, show a message to that effect
            if(dataSet.resultsAreTruncated) {
                this.renderResultsTruncatedMessage();
            }
            // otherwise if the number of results matches the max result count that was used to fetch,
            // show a message that we might not be displaying the full data set
            else if(dataSet.seriesList.length > 0 && maxResultCount > 0 && dataSet.seriesList[0].length >= maxResultCount) {
                this.renderMaxResultCountMessage(maxResultCount);
            }

            // If populate scale informationwhere possible
            if (!_.isUndefined(this.getScale('xAxis'))) {
                var xCategories = {
                    xCategories: this.getScale('xAxis').get('actualCategories')
                };
            }
            if (!_.isUndefined(this.getScale('yAxis'))) {
                var yAxisMin = this.getScale('yAxis').get('actualMinimum');
                var yAxisMax = this.getScale('yAxis').get('actualMaximum');
                if (yAxisMin < yAxisMax) {
                    var yAxisExtremes = {
                        yAxisMin: yAxisMin,
                        yAxisMax: yAxisMax
                    };
                }
            }
            if (!_.isUndefined(this.getScale('overlayAxis'))) {
                var overlayAxisMin = this.getScale('overlayAxis').get('actualMinimum');
                var overlayAxisMax = this.getScale('overlayAxis').get('actualMaximum');
                if (overlayAxisMin < overlayAxisMax) {
                    var overlayAxisExtremes = {
                        overlayAxisMin: overlayAxisMin,
                        overlayAxisMax: overlayAxisMax
                    };
                }
            }

            // NOTE: naming got weird here, configModel is the representation of the server config endpoint,
            // not to be confused with this.model.config, which is the report configuration.
            var displayProperties = $.extend(
                {},
                this.displayProperties,
                jschartingUtils.getCustomDisplayProperties(dataSet, configModel.toJSON()),
                xCategories,
                yAxisExtremes,
                overlayAxisExtremes
            );
            // If this is the first time creating the chart, or the display configuration has changed,
            // do a full destroy and recreate.
            if(!this.chart || !_.isEqual(displayProperties, this.chart.getCurrentDisplayProperties())) {
                this.destroyChart();
                this.chart = splunkCharting.createChart(this.$chart[0], displayProperties);
            }
            // Otherwise the chart will be updated in place, remove existing listeners since they will
            // be bound below.
            else {
                this.chart.off();
            }
            this.updateChartContainerHeight();
            var that = this;
            this.chart.prepare(dataSet, {});
            var fieldList = this.chart.getFieldList();
            if(this.chart.requiresExternalColorPalette()) {
                SplunkLegend.setLabels(this.legendId, fieldList);
                this.externalPalette = this.getExternalColorPalette();
                this.chart.setExternalColorPalette(this.externalPalette.fieldIndexMap, this.externalPalette.numLabels);
            }
            this.chart.on('pointClick', function(eventInfo) {
                var drilldownEvent = that.normalizeDrilldownEvent(eventInfo, 'cell');
                that.trigger('drilldown', drilldownEvent);
            });
            this.chart.on('legendClick', function(eventInfo) {
                var drilldownEvent;
                if (eventInfo.hasOwnProperty('name') && eventInfo.hasOwnProperty('value')) {
                    // if the legend click has a name and value (this happens for scatter/bubble charts), do a row drilldown
                    drilldownEvent = that.normalizeDrilldownEvent(eventInfo, 'row');
                } else {
                    // otherwise do a column drilldown
                    drilldownEvent = that.normalizeDrilldownEvent(eventInfo, 'column');
                }
                that.trigger('drilldown', drilldownEvent);
            });
            // Bind to the chart object's "chartRangeSelect" event and re-broadcast it upstream.
            // Each chart will broadcast its range when it is created, and since this view abstracts
            // the process of destroying and creating new charts, the currently selected range is cached
            // and the re-broadcast is avoided if the range did not actually change (SPL-121742).
            this.chart.on('chartRangeSelect', function(eventInfo) {
                var newRange = _(eventInfo).pick('startXIndex', 'endXIndex', 'startXValue', 'endXValue');
                if (!_.isEqual(newRange, that._selectedRange)) {
                    that._selectedRange = newRange;
                    that.trigger('chartRangeSelect', eventInfo);
                }
            });
            this.chart.draw(function(chart) {
                that.model.config.set({ currentChartFields: fieldList }, {'transient': true});
                done();
            });
        },
        normalizeDrilldownEvent: function(originalEvent, type) {
            return _.extend(
                {
                    type: type,
                    originalEvent: originalEvent
                },
                _(originalEvent).pick('name', 'value', 'name2', 'value2', '_span', 'rowContext', 'modifierKey')
            );
        },
        getExternalColorPalette: function() {
            // Querying the external color palette will force it to reconcile any deferred work, which means it might
            // fire a "labelIndexMapChanged" event.  This event should be ignored (see onExternalPaletteChange) since we
            // are already in the process of getting the latest palette information.
            this.synchronizingExternalPalette = true;
            var fieldIndexMap = {};
            _(this.chart.getFieldList()).each(function(field) {
                fieldIndexMap[field] = SplunkLegend.getLabelIndex(field);
            });
            this.synchronizingExternalPalette = false;
            return { fieldIndexMap: fieldIndexMap, numLabels: SplunkLegend.numLabels() };
        },
        onExternalPaletteChange: function() {
            if(this.synchronizingExternalPalette) {
                return;
            }
            var oldExternalPalette = this.externalPalette;
            this.externalPalette = this.getExternalColorPalette();
            if (this.chart && this.chart.requiresExternalColorPalette() && !_.isEqual(oldExternalPalette, this.externalPalette)) {
                this.invalidate('updateViewPass');
            }
        },
        destroyChart: function() {
            if(this.chart) {
                this.chart.off();
                this.chart.destroy();
                delete this.chart; // GC handler
            }
        },
        reflow: function() {
            if(this.chart && this.$el.height() > 0) {
                this.updateChartContainerHeight();
                this.chart.resize();
            }
        },
        updateChartContainerHeight: function() {
            var messageHeight = this.$inlineMessage.is(':empty') ? 0 : this.$inlineMessage.outerHeight();
            this.$chart.height(this.$el.height() - messageHeight);
        },
        renderResultsTruncatedMessage: function() {
            var message = _('These results may be truncated. Your search generated too much data for the current visualization configuration.').t();
            message = this.addTruncationDocsLink(message);
            this.$inlineMessage.html(_(this.inlineMessageTemplate).template({ message: message, level: 'warning' }));
        },
        renderMaxResultCountMessage: function(resultCount) {
            var message = splunkUtils.sprintf(
                _('These results may be truncated. This visualization is configured to display a maximum of %s results per series, and that limit has been reached.').t(),
                resultCount
            );
            message = this.addTruncationDocsLink(message);
            this.$inlineMessage.html(_(this.inlineMessageTemplate).template({ message: message, level: 'warning' }));
        },
        computeDisplayProperties: function() {
            this.displayProperties = {};
            var jsonConfig = this.model.config.toJSON();
            _.each(jsonConfig, function(value, key){
                if(this.VIZ_PROPERTY_PREFIX_REGEX.test(key)) {
                    this.displayProperties[key.replace(this.VIZ_PROPERTY_PREFIX_REGEX, '')] = value;
                }
            }, this);
        },
        addTruncationDocsLink: function(message) {
            var docsHref = route.docHelp(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    'learnmore.charting.datatruncation'
                ),
                helpLink = ' <a href="<%- href %>" target="_blank">' +
                                '<span><%- text %></span>' +
                                '<i class="icon-external icon-no-underline"></i>' +
                            '</a>';

            return message + _(helpLink).template({ href: docsHref, text: _('Learn More').t() });
        },
        inlineMessageTemplate: '\
            <div class="alert alert-inline alert-<%= level %> alert-inline"> \
                <i class="icon-alert"></i> \
                <%= message %> \
            </div> \
        '
    });

    return JSChart;

 });