import assignIn from 'lodash/assignIn';
import { _ } from '@splunk/ui-utils/i18n';
import { sprintf } from '@splunk/ui-utils/format';
import Main from '@splunk/base-lister/Main';
import { createSearchFilterString } from 'util/splunkd_utils';
import HealthActions from 'views/health_manager/columns/HealthActions';
import HealthModalChangeStatus from 'views/health_manager/modals/HealthChangeStatus';
import EditThresholdsModal from 'views/health_manager/modals/EditThresholds';

const MAX_FILTER_LENGTH = 250;

class HealthReportManager extends Main {
    static propTypes = {
        ...Main.propTypes,
    };

    static defaultProps = {
        ...Main.defaultProps,
        showAppColumn: false,
        showOwnerColumn: false,
        showAppFilter: false,
        showOwnerFilter: false,
        hasRowExpansion: false,
        showSharingColumn: false,
        objectNamePlural: _('Features'),
        objectNameSingular: _('Feature'),
        headerDescription: _(`Set feature thresholds to determine how the splunkd health report
            monitors Splunk components.`),
        ModalEdit: EditThresholdsModal,
        ColumnActions: HealthActions,
        ModalChangeStatus: HealthModalChangeStatus,
          /**
         * Default method returning the fetch data necessary for the collection fetch. Allows for override.
         * @param {Object} state current state of the component
         * @param {Object} newData data that is being passed to handleRefreshListing but not yet saved in the state
         * @returns {Object} an object containing the fetch data necessary for the collection fetch.
         */
        getObjectsCollectionFetchData(state, newData) {
            // 'sort_dir' is used as a query parameter for sortDirection state
            // 'sort_key' is used as a query parameter for sortKey state
            // 'search'   is used as a query parameter for filterString state
            // 'count'    is used as a query parameter for countPerPage state
            const searchFilterString = sprintf('%s AND %s',
                createSearchFilterString('feature:', ['name'], {}),
                createSearchFilterString(state.filterString.substring(0, MAX_FILTER_LENGTH), ['name'], {}));
            return assignIn(
                {},
                {
                    count: state.countPerPage,
                    sort_key: state.sortKey,
                    sort_dir: state.sortDirection,
                    offset: state.offset,
                    search: searchFilterString,
                    output_mode: 'json',
                },
                newData,
            );
        },
        permissions: {
            read: true,
            write: true,
            canChangeStatus: true,
            canCreate: false,
            canClone: false,
            canEditPermissions: false,
            canEditTitleAndDescription: false,
            canBulkChangeStatus: false,
            canBulkEditPermissions: false,
        },
    };

    /**
     * Handles the text filter change event
     * @param {Event} e click event
     * @param {String} value target filter text
     */
    handleTextFilterChange = (e, { value }) => {
        // Reset page to page 1 and offset to 0.
        // Leave the filterString as is for the UI
        this.setState({
            fetchingCollection: true,
            fetchingCount: true,
            filterString: value,
            offset: 0,
            page: 1,
        });

        this.handleRefreshListing({
            offset: 0,
        });
    };
}

export default HealthReportManager;
