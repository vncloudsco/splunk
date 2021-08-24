# This file contains possible attribute/value pairs for configuring the Metrics Workspace

# workspace.conf is used for:
# * Enabling/Disabling feature flags
# * Limiting the amount of metric names and dimensions the app loads.
# * Modifying the amount of time to look back for metrics. 


[metadata]
earliest = <string>
* Sets how far back to query the metrics catalog.
* Shortening this could speed up the catalog query.
* Default: -2d

max_metrics = <int>
* Sets the maximum number of metric names to be fetched from the catalog
* Providing a value of -1 will load all available metric names but could have a performance impact
* Default: 20000

max_dimensions = <int>
* Limits the number of dimension that are fetched
* Default: -1

[features]
data-alerts = <bool>
* Disables/enables the data source for the alert.
* Default: 1

data-alerts-scheduled = <bool>
* Disables/enables the scheduled alert service.
* Default: 1

data-alerts-streaming = <bool>
* Disables/enables the streaming alert service.
* Default: 0

analysis-related-events = <bool>
* Toggle the related events functionality
* Default: 1

analysis-open-in-search = <bool>
* Toggles the "open in search" functionality.
* Default: 1

analysis-save-to-dashboard = <bool>
* Toggles the "save as dashboard" functionality.
* Default: 1

analysis-save-to-report = <bool>
* Toggles the "save as report" functionality.
* Default: 1

analysis-create-alert = <bool>
* Toggles the alert creation functionality.
* Default: 1

analysis-export-png = <bool>
* Toggles the panel png export functionality.
* Default: 1

analysis-export-csv = <bool>
* Toggles the panel csv export functionality.
* Default: 1

span-limit-description = <bool>
* Enables/disables span limit description functionality.
* Default: 0

state-restore = <bool>
* Enables/disables state restore, to bring back the previous session
* Default: 1

chart-blocking-load = <bool>
* Enables/disables chart loading body on data refresh
* Default: 0

reference-lines = <bool>
* Enables/disables reference lines on charts
* Default: 0

category-charts = <bool>
* Enables/disables category chart modes in chart settings panel
* Default: 0

data-datasets = <bool>
* Disables/enables the data source for the dataset.
* Default: 1
