define(['splunkjs/mvc/utils'], function(utils) {
    return {
        "typeMap": {
            "dashboard": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/dashboardview"); },
                "class": "container",
                "autoId": "dashboard"
            },
            "row": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/dashboard/row"); },
                "class": "container",
                "autoId": "row"
            },
            "panel": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/dashboard/panel"); },
                "class": "container",
                "settingsOptions": {
                    "tokens": true
                },
                "autoId": "panel"
            },
            "fieldset": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/fieldsetview"); },
                "class": "container",
                "autoId": "fieldset"
            },
            "panelref": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/dashboard/panelref"); },
                "class": "container",
                "settingsOptions": {
                    "tokens": true
                },
                "autoId": "panel"
            },
            "chart": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/chart"); },
                "class": "viz",
                "reportContent": {
                    "display.general.type": "visualizations",
                    "display.visualizations.type": "charting"
                }
            },
            "table": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/table"); },
                "class": "viz",
                "reportContent": {
                    "display.general.type": "statistics"
                }
            },
            "single": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/single"); },
                "class": "viz",
                "reportContent": {
                    "display.general.type": "visualizations",
                    "display.visualizations.type": "singlevalue"
                }
            },
            "map": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/map"); },
                "class": "viz",
                "reportContent": {
                    "display.general.type": "visualizations",
                    "display.visualizations.type": "mapping"
                }
            },
            "event": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/event"); },
                "class": "viz",
                "reportContent": {
                    "display.general.type": "events"
                }
            },
            "viz": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/visualization"); },
                "class": "viz",
                "reportContent": {
                    "display.general.type": "visualizations",
                    "display.visualizations.type": "custom"
                }
            },
            "html": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/element/html"); },
                "class": "content",
                "renameSettings": {
                    "content": "html"
                }
            },
            "text-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/text"); },
                "class": "input",
                "settingsToCreate": {
                    "blankIsUndefined": true
                }
            },
            "dropdown-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/dropdown"); },
                "class": "input"
            },
            "radio-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/radiogroup"); },
                "class": "input",
                "settingsToCreate": {
                    "multiValue": false
                }
            },
            "link-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/linklist"); },
                "class": "input"
            },
            "multiselect-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/multiselect"); },
                "class": "input",
                "settingsToCreate": {
                    "multiValue": true
                }
            },
            "checkbox-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/checkboxgroup"); },
                "class": "input",
                "settingsToCreate": {
                    "multiValue": true
                }
            },
            "time-input": {
                "getModule": function() { return require("splunkjs/mvc/simpleform/input/timerange"); },
                "class": "input"
            },
            "drilldown": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/eventhandler"); },
                "class": "event",
                "settingsToCreate": {
                    "event": "drilldown"
                }
            },
            "selection": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/eventhandler"); },
                "class": "event",
                "settingsToCreate": {
                    "event": "selection"
                }
            },
            "input-change": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/eventhandler"); },
                "class": "event",
                "settingsToCreate": {
                    "event": "valueChange"
                }
            },
            "init-event-handler": {
                "class": "event",
                "getModule": function() { return require("splunkjs/mvc/simplexml/dashboardeventhandler"); }
            },
            "event-manager": {
                "class": "eventmanager",
                "getModule": function() { return require("dashboard/manager/EventManager"); }
            },
            "inline-search": {
                "getModule": function() { return require("splunkjs/mvc/searchmanager"); },
                "class": "manager",
                "settingsToCreate": {
                    "status_buckets": 0,
                    "cancelOnUnload": true,
                    "auto_cancel": 90,
                    "preview": true,
                    "runWhenTimeIsUndefined": false,
                    "defaultsToGlobalTimerange": true,
                    "replaceTabsInSearch": true,
                    "provenance": function(){
                        return "UI:Dashboard:" + utils.getPageInfo().page;
                    }
                },
                "renameSettings": {
                    "query": "search",
                    "earliest": "earliest_time",
                    "latest": "latest_time",
                    "sampleRatio": "sample_ratio"
                }
            },
            "saved-search": {
                "getModule": function() { return require("splunkjs/mvc/savedsearchmanager"); },
                "class": "manager",
                "settingsToCreate": {
                    "status_buckets": 0,
                    "cancelOnUnload": true,
                    "auto_cancel": 90,
                    "preview": true,
                    "runWhenTimeIsUndefined": false,
                    "provenance": function(){
                        return "UI:Dashboard:" + utils.getPageInfo().page;
                    }
                },
                "renameSettings": {
                    "ref": "searchname",
                    "name": "searchname",
                    "earliest": "earliest_time",
                    "latest": "latest_time"
                }
            },
            "postprocess-search": {
                "getModule": function() { return require("splunkjs/mvc/postprocessmanager"); },
                "settingsToCreate": {
                    "replaceTabsInSearch": true
                },
                "renameSettings": {
                    "base": "managerid",
                    "query": "search",
                    "postprocess": "search"
                },
                "class": "manager"
            },
            "search-eventhandler": {
                "getModule": function() { return require("splunkjs/mvc/simplexml/searcheventhandler"); },
                "class": "event"
            }
        },
        "classes": {
            "container": {
                "dom": true
            },
            "content": {
                "settingsOptions": {
                    "tokens": true
                },
                "autoId": "content",
                "dom": true
            },
            "viz": {
                "settingsOptions": {
                    "tokens": true
                },
                "autoId": "element",
                "dom": true
            },
            "input": {
                "settingsToCreate": {
                    "handleValueChange": true
                },
                "settingsOptions": {
                    "tokens": true
                },
                "autoId": "input",
                "dom": true
            },
            "manager": {
                "settingsToCreate": {
                    "auto_cancel": 90,
                    "preview": true,
                    "runWhenTimeIsUndefined": false
                },
                "settingsOptions": {
                    "tokens": true,
                    "tokenNamespace": "submitted"
                },
                "autoId": "search"
            },
            "eventmanager": {
                "autoId": "evtmanager"
            },
            "event": {
                "autoId": "evt"
            }
        }
    };
});
