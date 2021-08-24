import Main from '@splunk/base-lister/Main';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import 'views/roles/Roles.pcss';
import AddEditRoles from './modals/AddEditRoles';
import DeleteRole from './modals/DeleteRole';
import ViewCapabilitiesModal from './modals/ViewCapabilities';
import { MAX_FILTER_LENGTH } from './Utils';

const DEFAULT_USERS = ['admin', 'user', 'power'];

class RolesManager extends Main {
    /**
     * See base-lister/src/Main.jsx for propTypes definition.
     */
    static propTypes = {
        ...Main.propTypes,
        callDeleteRole: PropTypes.func.isRequired,
        callCreateRole: PropTypes.func.isRequired,
        callEditRole: PropTypes.func.isRequired,
        fetchAllCapabilities: PropTypes.func.isRequired,
        fetchAllRoles: PropTypes.func.isRequired,
        apps: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    };

    static defaultProps = {
        ...Main.defaultProps,
        showAppColumn: false,
        showOwnerColumn: false,
        showAppFilter: false,
        showOwnerFilter: false,
        showSharingColumn: false,
        showStatusColumn: false,
        hasRowExpansion: false,
        isSingleRowTableFilter: true,
        objectNamePlural: _('Roles'),
        objectNameSingular: _('Role'),
        ModalNew: AddEditRoles,
        ModalEdit: AddEditRoles,
        ModalClone: AddEditRoles,
        idAttribute: 'name',
        permissions: {
            read: true,
            write: true,
            canChangeStatus: true,
            canCreate: true,
            canClone: true,
        },
        /**  List of custom columns to be displayed on roles listing page. */
        customColumns: [
            {
                key: 'native_capabilities',
                label: _('Native capabilities'),
                content: object => object.content.capabilities.length,
            },
            {
                key: 'imported_capabilities',
                label: _('Inherited capabilities'),
                content: object => object.content.imported_capabilities.length,
            },
            {
                key: 'defaultApp',
                label: _('Default App'),
                sortKey: 'defaultApp',
                content: object => object.content.defaultApp,
            },
        ],
        /** Custom actions on the roles listing page. */
        customActions: [
            {
                key: 'viewCapabilities',
                label: _('View Capabilities'),
                ModalToOpen: ViewCapabilitiesModal,
            },
            {
                key: 'delete_role',
                label: _('Delete'),
                ModalToOpen: DeleteRole,
                isVisible: props => (DEFAULT_USERS.indexOf(props.object.name) === -1),
            },
        ],
        /**
         * Overrriding the default method returning the fetch collection data.
         * roles endpoint doesn't accept filterString, so remove it from the POST data.
         * @param {Object} state current state of the component
         * @param {Object} newData data that is being passed to handleRefreshListing but not
         * yet saved in the state.
         * @returns {Object} an object containing the fetch data necessary for the collection fetch.
         */
        getObjectsCollectionFetchData(state, newData) {
            const data = Object.assign(
                {},
                {
                    count: state.countPerPage,
                    sort_key: state.sortKey,
                    sort_dir: state.sortDirection,
                    offset: state.offset,
                    search: state.filterString ? state.filterString.substring(0, MAX_FILTER_LENGTH) : '',
                    output_mode: 'json',
                },
                newData);
            delete data.filterString;
            return data;
        },
    };
}

export default RolesManager;
