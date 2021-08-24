define(
    [
        'underscore',
        'models/SplunkDBase'
    ],
    function (_, SplunkDBaseModel) {
        var HEALTHY_STATUS = 'green';

        return SplunkDBaseModel.extend({
            urlRoot: 'server/health/splunkd',
            id: 'details',
            _processFeatures: function (features) {
                var output = [];
                _.each(features, function(comp, name) {
                    var obj = {
                        name: name,
                        health: comp.health,
                        reasons: comp.reasons,
                        messages: comp.messages,
                        disabled: comp.disabled
                    };
                    if (comp.features) {
                        obj.features = this._processFeatures(comp.features);
                    }
                    output.push(obj);
                    var map = this.get('map') || {};
                    map[name] = obj;
                    this.set('map', map);

                }.bind(this));
                return output;
            },
            
            /*
             * Constructing a flat array of all health anomalies using BFS algorithm
             */
            _findAnomalies: function(features) {
                var result = [],
                    queue = [];
                
                _.each(features, function(feature) {
                    if (feature.health !== HEALTHY_STATUS) {
                        feature.name = [feature.name]; // Storing feature hierarchy 
                        queue.push(feature);
                    }
                });

                while (queue.length > 0) {
                    var curFeature = queue.shift(),
                        nameArr = curFeature.name,
                        childFeatures = curFeature.features;
                    
                    if (childFeatures) {
                        _.each(childFeatures, function(feature) {
                            var nameArrCopy = nameArr.slice();
                            if (feature.health !== HEALTHY_STATUS) {
                                nameArrCopy.push(feature.name);
                                feature.name = nameArrCopy; // Storing feature hierarchy 
                                queue.push(feature);
                            }
                        });
                    } else {
                        result.push(curFeature);
                    }
                }
                return result;
            },

            getAnomalies: function() {
                return this.get('parsed') ? this.get('parsed').anomalies : [];
            },

            getFeatures: function() {
                return this.get('parsed') ? this.get('parsed').features : [];
            },

            parse: function(response) {
                if (!response.entry) return;
                var responseObj = response.entry[0],
                    rootObj = {
                        name: responseObj.name,
                        health: responseObj.content.health,
                        disabled: responseObj.content.disabled,
                        anomalies: []
                    };

                if (_.keys(responseObj.content.features).length > 0) {
                    rootObj.features = this._processFeatures(responseObj.content.features);
                }

                if (rootObj.features && rootObj.features.length > 0 && rootObj.health !== HEALTHY_STATUS) {
                    // Making a deep copy of features array
                    var featuresArrCopy = JSON.parse(JSON.stringify(rootObj.features));
                    rootObj.anomalies = this._findAnomalies(featuresArrCopy);  
                }

                this.set('parsed', rootObj);
                return SplunkDBaseModel.prototype.parse.call(this, response);

            }

        });
    });