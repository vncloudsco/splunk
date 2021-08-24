import _ from 'underscore';
import Backbone from 'backbone';
import React from 'react';
import PropTypes from 'prop-types';
import splunkUtil from 'splunk.util';
import WorkloadManagementPage from 'views/workload_management/WorkloadManagementPage';
import { createDocsURL } from '@splunk/splunk-utils/url';
import Link from '@splunk/react-ui/Link';

class WorkloadManagementPageContainer extends React.Component {
    constructor(props) {
        super(props);

        this.state = this.getDefaultState();
        this.props.category.on('sync', this.updateCategories);
        this.props.pools.on('sync', this.updatePoolsTable);
        this.props.rules.on('sync', this.updateRulesTable);
        this.props.status.on('sync', this.updateStatus);
    }

    getDefaultState = () => ({
        title: _('Workload Management').t(),
        description: _('View, edit, and apply configurations for workload management.').t(),
        learnMore: this.getLearnMoreLink(),
        categoryUpdateModalOpen: false,
        categoryUpdateModalState: this.getDefaultCategoryUpdateModalState(),
        handleCategoryUpdateModalClose: this.handleCategoryUpdateModalClose,
        handleCategoryUpdateModalTextChange: this.handleCategoryUpdateModalTextChange,
        handleCategoryUpdateModalSubmit: this.handleCategoryUpdateModalSubmit,
        handleCategoryUpdateModalOpenEdit: this.handleCategoryUpdateModalOpenEdit,
        handleCategoryClick: this.handleCategoryClick,
        handleCategoryRowNameClick: this.handleCategoryRowNameClick,
        categoryCardState: this.getDefaultCategoryCardState(),
        categories: this.props.category.prepareCategories(),
        allPools: this.props.pools.preparePools('all'),
        pools: this.props.pools.preparePools('search'),
        rules: this.props.rules.prepareRules(),
        canEditWorkloadPools: this.props.user.hasCapability('edit_workload_pools'),
        canEditWorkloadRules: this.props.user.hasCapability('edit_workload_rules'),
        isEnabled: this.props.status.isEnabled(),
        enableSettingsViewBtn: this.enableSettingsViewBtn(),
        handleReRunPreflightCheck: this.handleReRunPreflightCheck,
        handleShowSettingsView: this.handleShowSettingsView,
        handleShowPreFlightCheckView: this.handleShowPreFlightCheckView,
        allPreflightChecksPass: this.props.checks.allPreflightChecksPass(),
        showPreFlightCheckView: !this.props.status.isEnabled() && !this.props.checks.allPreflightChecksPass(),
        isPreflightCheckLoading: false,
        checks: this.props.checks.getPreflightChecks(),
        statusErrorMessage: this.props.status.getShortErrorMessage(),
        missingTablesMessage: this.getMissingTablesMessage(),
        getDefaultSearchPool: this.props.pools.getDefaultPool('search'),
        getDefaultIngestPool: this.props.pools.getDefaultPool('ingest'),
        getSearchPools: this.props.pools.getPoolsByCategory('search'),
        getIngestPools: this.props.pools.getPoolsByCategory('ingest'),
        getMiscPools: this.props.pools.getPoolsByCategory('misc'),
        isSearchCategoryAllocated: this.props.category.isCategoryAllocated('search'),
        isIngestCategoryAllocated: this.props.category.isCategoryAllocated('ingest'),
        isMiscCategoryAllocated: this.props.category.isCategoryAllocated('misc'),
        poolUpdateModalOpen: false,
        poolUpdateModalState: this.getDefaultPoolUpdateModalState(),
        handleEnableDisableClick: this.handleEnableDisableClick,
        handlePoolUpdateModalOpen: this.handlePoolUpdateModalOpen,
        handlePoolUpdateModalClose: this.handlePoolUpdateModalClose,
        handlePoolUpdateModalOpenEdit: this.handlePoolUpdateModalOpenEdit,
        handlePoolUpdateModalCheckbox: this.handlePoolUpdateModalCheckbox,
        handlePoolUpdateModalTextChange: this.handlePoolUpdateModalTextChange,
        handlePoolUpdateModalSubmit: this.handlePoolUpdateModalSubmit,
        poolDeleteModalOpen: false,
        poolDeleteModalState: this.getDefaultPoolDeleteModalState(),
        handlePoolDeleteModalOpen: this.handlePoolDeleteModalOpen,
        handlePoolDeleteModalClose: this.handlePoolDeleteModalClose,
        handlePoolDeleteModalSubmit: this.handlePoolDeleteModalSubmit,
        ruleUpdateModalOpen: false,
        ruleUpdateModalState: this.getDefaultRuleUpdateModalState(),
        handleRuleUpdateModalOpen: this.handleRuleUpdateModalOpen,
        handleRuleUpdateModalClose: this.handleRuleUpdateModalClose,
        handleRuleUpdateModalOpenEdit: this.handleRuleUpdateModalOpenEdit,
        handleRuleUpdateModalTextChange: this.handleRuleUpdateModalTextChange,
        handleRuleUpdateModalMultiSelectChange: this.handleRuleUpdateModalMultiSelectChange,
        handleRuleUpdateModalSubmit: this.handleRuleUpdateModalSubmit,
        ruleDeleteModalOpen: false,
        ruleDeleteModalState: this.getDefaultRuleDeleteModalState(),
        handleRuleDeleteModalOpen: this.handleRuleDeleteModalOpen,
        handleRuleDeleteModalClose: this.handleRuleDeleteModalClose,
        handleRuleDeleteModalSubmit: this.handleRuleDeleteModalSubmit,
        messageModalState: this.getDefaultMessageModalState(),
        handleMessageModalClose: this.handleMessageModalClose,
        handleTabBarChange: this.handleTabBarChange,
        tabBarState: 'pools',
    })

    getLearnMoreLink = () => (
        <Link to={createDocsURL('learnmore.workload_management')} openInNewContext>
            {_('Learn more').t()}
        </Link>
    )

    getMissingTablesMessage = () => {
        let missingTables = '';
        let addButtons = '';
        let newTables = '';
        const noPools = (_.size(this.props.pools.preparePools('all')) === 0);
        const noRules = (_.size(this.props.rules) === 0);
        const canEditWorkloadPools = this.props.user.hasCapability('edit_workload_pools');
        const canEditWorkloadRules = this.props.user.hasCapability('edit_workload_rules');

        if (noPools && noRules) {
            missingTables = _('workload pools or workload rules').t();
        } else if (noPools) {
            missingTables = _('workload pools').t();
        } else if (noRules) {
            missingTables = _('workload rules').t();
        }

        if (noPools && noRules && canEditWorkloadPools && canEditWorkloadRules) {
            addButtons = _('Add buttons').t();
            newTables = _('workload pools and workload rules').t();
        } else if (noPools && !noRules && canEditWorkloadPools) {
            addButtons = _('Add Workload Pool button').t();
            newTables = _('workload pools').t();
        } else if (noRules && !noPools && canEditWorkloadRules) {
            addButtons = _('Add Workload Rule button').t();
            newTables = _('workload rules').t();
        }
        const status = _.isEmpty(missingTables) ? '' : splunkUtil.sprintf(_('There are no %s. ').t(), missingTables);
        const action = (_.isEmpty(addButtons) || _.isEmpty(newTables)) ? '' :
        splunkUtil.sprintf(_(' Use the %s to create new %s.').t(), addButtons, newTables);

        return status + action;
    }

    getDefaultCategoryCardState = () => ({
        selected: 'search',
    })

    getDefaultCategoryUpdateModalState = () => ({
        cpu_weight: 0,
        mem_weight: 0,
        allocated_cpu: 0,
        allocated_mem: 0,
        changed: false,
        backendErrorMsg: '',
    })

    getDefaultPoolUpdateModalState = () => ({
        category: 'search',
        name: '',
        title: '',
        cpu_weight: 0,
        mem_weight: 0,
        allocated_cpu: 0,
        allocated_mem: 0,
        default_category_pool: false,
        changed: false,
        backendErrorMsg: '',
    })

    getDefaultPoolDeleteModalState = () => ({
        poolModel: undefined,
        backendErrorMsg: '',
    })

    getDefaultRuleUpdateModalState = () => ({
        name: '',
        title: '',
        predicate: '',
        action: '',
        workload_pool: '',
        available_pools: [],
        schedule: '',
        start_date: new Date().toISOString().substring(0, 10),
        end_date: new Date().toISOString().substring(0, 10),
        start_time: '0:00',
        end_time: '0:00',
        timeItems: this.getTimeItems(),
        getRuleActions: this.props.rules.getRuleActions(),
        changed: false,
        backendErrorMsg: '',
    })

    getDefaultRuleDeleteModalState = () => ({
        ruleModel: undefined,
        backendErrorMsg: '',
    })

    getDefaultMessageModalState = () => ({
        open: false,
        title: '',
        message: '',
        type: 'error',
        closeable: true,
    })

    getTimeItems = () => {
        if (!_.isEmpty(this.state) && !_.isEmpty(this.state.ruleUpdateModalState.timeItems)) {
            return this.state.ruleUpdateModalState.timeItems;
        }
        const items = [];
        for (let index = 0; index < 25; index += 1) {
            items.push(`${index}:00`);
        }
        return items;
    }

    setWaitView = (modalStateName) => {
        const newModalState = {};
        newModalState[modalStateName] = {
            ...this.state[modalStateName],
            wait: true,
        };
        this.setState(newModalState);
    }

    updateCategories = () => {
        this.setState({
            categories: this.props.category.prepareCategories(),
            isSearchCategoryAllocated: this.props.category.isCategoryAllocated('search'),
            isIngestCategoryAllocated: this.props.category.isCategoryAllocated('ingest'),
            isMiscCategoryAllocated: this.props.category.isCategoryAllocated('misc'),
            getSearchPools: this.props.pools.getPoolsByCategory('search'),
            getIngestPools: this.props.pools.getPoolsByCategory('ingest'),
            getMiscPools: this.props.pools.getPoolsByCategory('misc'),
        });
    }

    updatePoolsTable = () => {
        this.props.category.fetch().done(() => {
            this.setState({
                allPools: this.props.pools.preparePools('all'),
                pools: this.props.pools.preparePools(this.state.categoryCardState.selected),
                getDefaultSearchPool: this.props.pools.getDefaultPool('search'),
                getDefaultIngestPool: this.props.pools.getDefaultPool('ingest'),
                isSearchCategoryAllocated: this.props.category.isCategoryAllocated('search'),
                isIngestCategoryAllocated: this.props.category.isCategoryAllocated('ingest'),
                isMiscCategoryAllocated: this.props.category.isCategoryAllocated('misc'),
                getSearchPools: this.props.pools.getPoolsByCategory('search'),
                getIngestPools: this.props.pools.getPoolsByCategory('ingest'),
                getMiscPools: this.props.pools.getPoolsByCategory('misc'),
                missingTablesMessage: this.getMissingTablesMessage(this.state.categoryCardState.selected),
            });
        });
    }

    updateRulesTable = () => {
        this.setState({
            rules: this.props.rules.prepareRules(),
            missingTablesMessage: this.getMissingTablesMessage(this.state.categoryCardState.selected),
        });
    }

    updateStatus = () => {
        if (this.state.isEnabled !== this.props.status.isEnabled()) {
            this.setState({
                isEnabled: this.props.status.isEnabled(),
            });
        }
        if (this.state.statusErrorMessage !== this.props.status.getShortErrorMessage()) {
            this.setState({
                statusErrorMessage: this.props.status.getShortErrorMessage(),
            });
        }
    }

    enableSettingsViewBtn = () => (this.props.checks.allPreflightChecksPass() || this.props.status.isEnabled());

    handleTabBarChange = (e, { selectedTabId }) => {
        if (selectedTabId === 'pools') {
            this.setState({
                tabBarState: 'pools',
            });
        } else {
            this.setState({
                tabBarState: 'rules',
            });
        }
    }

    handleCategoryClick = (e, { value }) => {
        this.setState({
            pools: this.props.pools.preparePools(value),
            categoryCardState: {
                selected: value,
            },
        });
    }

    handleCategoryRowNameClick = (e, data) => {
        const value = data.getName();
        this.setState({
            pools: this.props.pools.preparePools(value),
            categoryCardState: {
                selected: value,
            },
        });
    }

    handleReRunPreflightCheck = () => {
        this.setState({
            isPreflightCheckLoading: true,
        });
        this.props.checks.fetch().done(() => {
            this.setState({
                isPreflightCheckLoading: false,
                checks: this.props.checks.getPreflightChecks(),
                enableSettingsViewBtn: this.enableSettingsViewBtn(),
            });
        });
    }

    handleShowSettingsView = () => {
        // Show settings view when enabled.
        // If preflight check fails show error to go back to preflight check
        this.setState({
            enableSettingsViewBtn: this.enableSettingsViewBtn(),
            showPreFlightCheckView: false,
            allPreflightChecksPass: this.props.checks.allPreflightChecksPass(),
        });
    }

    handleShowPreFlightCheckView = () => {
        this.setState({
            enableSettingsViewBtn: this.enableSettingsViewBtn(),
            showPreFlightCheckView: true,
        });
    }

    handleEnableDisableClick = (e, { value }) => {
        if (value === true) {
            this.handleDisable();
        } else {
            this.handleEnable();
        }
    }

    handleEnable = () => {
        const modalTitle = _('Enabling Workload Management').t();
        this.props.enable.save().done(() => {
            this.props.status.fetch().done(() => {
                this.setState({
                    isEnabled: this.props.status.isEnabled(),
                });
                if (this.props.status.isEnabled()) {
                    this.handleMessageModalOpen(
                        modalTitle,
                        _('Successfully enabled workload management.').t(),
                        'success',
                        true,
                    );
                } else {
                    this.handleMessageModalOpen(
                        modalTitle,
                        this.props.status.getShortErrorMessage(),
                        'error',
                        true,
                    );
                }
            });
        }).fail((response) => {
            let modalErrorMsg = _('Error enabling workload management.').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                modalErrorMsg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.handleMessageModalOpen(
                modalTitle,
                modalErrorMsg,
                'error',
                true,
            );
        });
    }

    handleDisable = () => {
        const modalTitle = _('Disabling Workload Management').t();
        this.props.disable.save().done(() => {
            this.props.status.fetch().done(() => {
                this.setState({
                    isEnabled: this.props.status.isEnabled(),
                });
                this.handleMessageModalOpen(
                    modalTitle,
                    _('Successfully disabled workload management').t(),
                    'success',
                    true,
                );
            });
        }).fail((response) => {
            let modalErrorMsg = _('Error disabling workload management').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                modalErrorMsg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.handleMessageModalOpen(
                modalTitle,
                modalErrorMsg,
                'error',
                true,
            );
        });
    }

    handleCategoryUpdateModalOpenEdit = (e, { value }) => {
        const cagegoryModel = value;
        const obj = {
            model: cagegoryModel,
            edit: true,
            title: splunkUtil.sprintf(_('Edit Category: %s').t(), cagegoryModel.getName()),
            cpu_weight: cagegoryModel.getCpuWeight(),
            mem_weight: cagegoryModel.getMemWeight(),
            allocated_cpu: this.props.category.getDynamicAllocatedCpu(
                cagegoryModel.getCpuWeight(),
                cagegoryModel.getName(),
            ),
            allocated_mem: cagegoryModel.getMemAllocatedPercent(),
        };
        this.setState({
            categoryUpdateModalOpen: true,
            categoryUpdateModalState: obj,
        });
    }

    handleCategoryUpdateModalTextChange = (e, { value, name }) => {
        if ((name === 'cpu_weight') && !_.isUndefined(value)) {
            const categoryName = this.state.categoryUpdateModalState.model.entry.get('name');
            this.validateFields([{
                name,
                value,
            }, {
                name: 'allocated_cpu',
                value: this.props.category.getDynamicAllocatedCpu(
                    value,
                    categoryName,
                ),
            }], this.state.categoryUpdateModalState);
        } else if (name === 'mem_weight') {
            this.validateFields([{
                name,
                value,
            }, {
                name: 'allocated_mem',
                value: this.props.category.getDynamicMemAllocatedPercent(value),
            }], this.state.categoryUpdateModalState);
        } else {
            this.validateFields([{
                name,
                value,
            }], this.state.categoryUpdateModalState);
        }
    }

    handleCategoryUpdateModalClose = () => {
        this.setState({
            categoryUpdateModalOpen: false,
            categoryUpdateModalState: this.getDefaultCategoryUpdateModalState(),
        });
    }

    handleCategoryUpdateModalSubmit = () => {
        // form validation
        this.validateFields([{
            name: 'cpu_weight',
            value: this.state.categoryUpdateModalState.cpu_weight,
        }, {
            name: 'mem_weight',
            value: this.state.categoryUpdateModalState.mem_weight,
        }], this.state.categoryUpdateModalState);

        if (this.state.categoryUpdateModalState.cpuWeightError ||
            this.state.categoryUpdateModalState.memWeightError) {
            return;
        }

        this.setWaitView('categoryUpdateModalState');
        const data = {
            cpu_weight: this.state.categoryUpdateModalState.cpu_weight,
            mem_weight: this.state.categoryUpdateModalState.mem_weight,
        };

        let model;
        if (this.state.categoryUpdateModalState.edit) {
            model = this.state.categoryUpdateModalState.model;
        }

        this.props.category.updateCategory(model, data).done(() => {
            this.props.category.fetch();
            this.props.pools.fetch();
            this.props.status.fetch();
            this.handleCategoryUpdateModalClose();
        }).fail((response) => {
            let msg = _('Encountered errors in updating category').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                msg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.props.category.fetch();
            this.validateFields([{
                name: 'backendErrorMsg',
                value: msg,
            }, {
                name: 'wait',
                value: false,
            }], this.state.categoryUpdateModalState);
        });
    }

    handlePoolUpdateModalOpen = () => {
        const obj = {
            title: _('New Workload Pool').t(),
        };
        this.setState({
            poolUpdateModalOpen: true,
            poolUpdateModalState: _.extend(this.getDefaultPoolUpdateModalState(), obj),
        });
    }

    handlePoolUpdateModalClose = () => {
        this.setState({
            poolUpdateModalOpen: false,
            poolUpdateModalState: this.getDefaultPoolUpdateModalState(),
        });
    }

    handlePoolUpdateModalOpenEdit = (e, { value }) => {
        const poolModel = value;
        const obj = {
            model: poolModel,
            edit: true,
            title: splunkUtil.sprintf(_('Edit Workload Pool: %s').t(), poolModel.getName()),
            category: poolModel.getPoolCategory(),
            name: poolModel.getName(),
            cpu_weight: poolModel.getPoolCategory() === 'ingest' || poolModel.getPoolCategory() === 'misc' ?
                100 : poolModel.getCpuWeight(),
            mem_weight: poolModel.getPoolCategory() === 'ingest' || poolModel.getPoolCategory() === 'misc' ?
                100 : poolModel.getMemWeight(),
            default_category_pool: poolModel.getPoolCategory() === 'ingest' || poolModel.getPoolCategory() === 'misc' ?
                1 : poolModel.isDefaultPool(),
        };
        obj.allocated_cpu = this.props.pools.getDynamicAllocatedCpu(
            poolModel.getCpuWeight(),
            obj,
            this.props.category,
        );
        obj.allocated_mem = this.props.pools.getDynamicAllocatedMem(
            obj,
            this.props.category,
        );
        this.setState({
            poolUpdateModalOpen: true,
            poolUpdateModalState: obj,
        });
    }

    handlePoolUpdateModalTextChange = (e, { value, name }) => {
        if (_.isEmpty(value) && name === 'category') {
            // fixes issue when clicking static txt below misc category
            return;
        }

        // When user is creating a new pool not editing
        // ingest and misc category by default have cpu and mem to 100 and are default
        if (name === 'category' && (value === 'ingest' || value === 'misc')) {
            this.validateFields([{
                name: 'cpu_weight',
                value: 100,
            }, {
                name: 'mem_weight',
                value: 100,
            }, {
                name: 'default_category_pool',
                value: 1,
            }], this.state.poolUpdateModalState);
        }

        // When user is creating a new pool not editing
        // Set cpu and mem to least allowable value and set default_category_pool back to default
        if (name === 'category' && value === 'search') {
            this.validateFields([{
                name: 'cpu_weight',
                value: 1,
            }, {
                name: 'mem_weight',
                value: 1,
            }, {
                name: 'default_category_pool',
                value: false,
            }], this.state.poolUpdateModalState);
        }

        this.state.poolUpdateModalState.field = name;
        this.state.poolUpdateModalState.fieldValue = value;
        this.validateFields([{
            name,
            value,
        }], this.state.poolUpdateModalState);
        if ((name === 'cpu_weight' || name === 'category') && !_.isUndefined(value)) {
            this.validateFields([{
                name: 'allocated_cpu',
                value: this.props.pools.getDynamicAllocatedCpu(
                    value,
                    this.state.poolUpdateModalState,
                    this.props.category,
                ),
            }], this.state.poolUpdateModalState);
        }
        if ((name === 'mem_weight' || name === 'category') && !_.isUndefined(value)) {
            this.validateFields([{
                name: 'allocated_mem',
                value: this.props.pools.getDynamicAllocatedMem(
                    this.state.poolUpdateModalState,
                    this.props.category,
                ),
            }], this.state.poolUpdateModalState);
        }
    }

    // called when field looses focus & on submit
    validateFields = (fields, stateObj) => {
        const obj = stateObj;
        let minCpuMem = 1;
        if (obj.model) { // obj.model is undefined when creating new pools
            minCpuMem = (obj.model.getType() === 'category' && obj.model.getName() === 'misc') ? 0 : 1;
        }
        obj.changed = true;

        _.each(fields, (field) => {
            obj[field.name] = field.value;
            switch (field.name) {
                case 'category':
                    if (_.isEmpty(field.value)) {
                        obj.categoryErrorMsg = _('Category must be selected.').t();
                    } else {
                        delete obj.categoryErrorMsg;
                    }
                    break;
                case 'name':
                    if (_.isEmpty(field.value)) {
                        obj.nameErrorMsg = _('Name must be entered.').t();
                    } else if (field.value === 'general') {
                        obj.nameErrorMsg = _('general is a reserved keyword.').t();
                    } else if (field.value.indexOf(' ') >= 0) {
                        obj.nameErrorMsg = _('Name cannot have spaces.').t();
                    } else if (field.value.indexOf(':') >= 0) {
                        // SPL-158200
                        obj.nameErrorMsg = _('Name cannot have colons.').t();
                    } else {
                        delete obj.nameErrorMsg;
                    }
                    break;
                case 'cpu_weight':
                    if (!Number.isInteger(field.value)) {
                        obj.cpuWeightErrorMsg = _('CPU weight must be a positive integer.').t();
                    } else if (field.value < minCpuMem || field.value > 100) {
                        obj.cpuWeightErrorMsg = splunkUtil.sprintf(
                            _('CPU weight must be between %s - 100.').t(), minCpuMem,
                            );
                    } else {
                        delete obj.cpuWeightErrorMsg;
                    }
                    break;
                case 'mem_weight':
                    if (!Number.isInteger(field.value)) {
                        obj.memWeightErrorMsg = _('Memory weight must be a positive integer.').t();
                    } else if (field.value < minCpuMem || field.value > 100) {
                        obj.memWeightErrorMsg = splunkUtil.sprintf(
                            _('Memory weight must be between %s - 100.').t(), minCpuMem,
                            );
                    } else {
                        delete obj.memWeightErrorMsg;
                    }
                    break;
                default:
                    break;
            }
        });
        obj.categoryError = !_.isEmpty(obj.categoryErrorMsg);
        obj.nameError = !_.isEmpty(obj.nameErrorMsg);
        obj.cpuWeightError = !_.isEmpty(obj.cpuWeightErrorMsg);
        obj.memWeightError = !_.isEmpty(obj.memWeightErrorMsg);

        this.setState({
            stateObj: obj,
        });
    }

    handlePoolUpdateModalCheckbox = (e, { value }) => {
        const obj = this.state.poolUpdateModalState;
        obj.default_category_pool = obj[value];

        obj[value] = !obj[value];
        obj.changed = true;
        this.setState({
            poolUpdateModalState: obj,
        });
    }

    handlePoolUpdateModalSubmit = () => {
        // form validation
        this.validateFields([{
            name: 'category',
            value: this.state.poolUpdateModalState.category,
        }, {
            name: 'cpu_weight',
            value: this.state.poolUpdateModalState.cpu_weight,
        }, {
            name: 'mem_weight',
            value: this.state.poolUpdateModalState.mem_weight,
        }], this.state.poolUpdateModalState);

        if (!this.state.poolUpdateModalState.edit) {
            this.validateFields([{
                name: 'name',
                value: this.state.poolUpdateModalState.name,
            }], this.state.poolUpdateModalState);
        }

        if (this.state.poolUpdateModalState.categoryError ||
            this.state.poolUpdateModalState.nameError ||
            this.state.poolUpdateModalState.cpuWeightError ||
            this.state.poolUpdateModalState.memWeightError) {
            return;
        }

        // send request to backend
        this.setWaitView('poolUpdateModalState');
        const data = {
            category: this.state.poolUpdateModalState.category,
            name: this.state.poolUpdateModalState.name,
            cpu_weight: this.state.poolUpdateModalState.cpu_weight,
            mem_weight: this.state.poolUpdateModalState.mem_weight,
            default_category_pool: this.state.poolUpdateModalState.default_category_pool,
        };

        let model;
        if (this.state.poolUpdateModalState.edit) {
            model = this.state.poolUpdateModalState.model;
        }

        this.props.pools.updatePool(model, data).done(() => {
            this.props.pools.fetch();
            this.props.status.fetch();
            this.handlePoolUpdateModalClose();
        }).fail((response) => {
            let msg = _('Encountered errors in updating pool').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                msg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.props.pools.fetch();
            this.validateFields([{
                name: 'backendErrorMsg',
                value: msg,
            }, {
                name: 'wait',
                value: false,
            }], this.state.poolUpdateModalState);
        });
    }

    handlePoolDeleteModalOpen = (e, { value }) => {
        const obj = {
            poolModel: value,
            title: splunkUtil.sprintf(_('Delete Workload Pool: %s').t(), value.getName()),
        };
        this.setState({
            poolDeleteModalOpen: true,
            poolDeleteModalState: obj,
        });
    }

    handlePoolDeleteModalClose = () => {
        this.setState({
            poolDeleteModalOpen: false,
            poolDeleteModalState: this.getDefaultPoolDeleteModalState(),
        });
    }

    handlePoolDeleteModalSubmit = () => {
        this.setWaitView('poolDeleteModalState');
        this.props.pools.deletePool(this.state.poolDeleteModalState.poolModel).done(() => {
            this.props.pools.fetch();
            this.props.status.fetch();
            this.handlePoolDeleteModalClose();
        }).fail((response) => {
            let msg = _('Encountered errors while deleting pool').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                msg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.props.pools.fetch();
            this.validateFields([{
                name: 'backendErrorMsg',
                value: msg,
            }, {
                name: 'wait',
                value: false,
            }], this.state.poolDeleteModalState);
        });
    }

    handleRuleUpdateModalOpen = () => {
        const obj = {
            title: _('New Workload Rule').t(),
            available_pools: this.props.pools.filterOutIngestMisc(),
        };
        this.setState({
            ruleUpdateModalOpen: true,
            ruleUpdateModalState: _.extend(this.getDefaultRuleUpdateModalState(), obj),
        });
    }

    handleRuleUpdateModalOpenEdit = (e, { value }) => {
        const ruleModel = value;
        const obj = {
            model: ruleModel,
            edit: true,
            title: splunkUtil.sprintf(_('Edit Workload Rule: %s').t(), ruleModel.getRuleName()),
            order: ruleModel.getOrder().toString(),
            name: ruleModel.getRuleName(),
            predicate: ruleModel.getPredicate(),
            action: ruleModel.getAction(),
            schedule: ruleModel.getSchedule(),
            workload_pool: ruleModel.getWorkloadPool(),
            start_date: ruleModel.getStartDate(),
            end_date: ruleModel.getEndDate(),
            start_time: ruleModel.getStartTime(),
            end_time: ruleModel.getEndTime(),
            every_week_days: ruleModel.getEveryWeekDays(),
            every_month_days: ruleModel.getEveryMonthDays(),
            timeItems: this.getTimeItems(),
            getRuleActions: this.props.rules.getRuleActions(),
            available_pools: this.props.pools.filterOutIngestMisc(),
        };
        this.setState({
            ruleUpdateModalOpen: true,
            ruleUpdateModalState: obj,
        });
    }

    handleRuleUpdateModalTextChange = (e, { value, name }) => {
        this.validateRuleFields([{
            name,
            value,
        }], this.state.ruleUpdateModalState);
    }

    handleRuleUpdateModalMultiSelectChange = (e, component) => {
        const name = component.name;
        const value = component.values;
        this.validateRuleFields([{
            name,
            value,
        }], this.state.ruleUpdateModalState);
    }

    validateRuleFields = (fields, stateObj) => {
        const obj = stateObj;
        obj.changed = true;
        _.each(fields, (field) => {
            obj[field.name] = field.value;
            switch (field.name) {
                case 'name':
                    if (_.isEmpty(field.value)) {
                        obj.nameErrorMsg = _('Name must be entered.').t();
                    } else if (field.value.indexOf(' ') >= 0) {
                        obj.nameErrorMsg = _('Name cannot have spaces.').t();
                    } else {
                        delete obj.nameErrorMsg;
                    }
                    break;
                case 'predicate':
                    if (_.isEmpty(field.value)) {
                        obj.predicateErrorMsg = _('Condition must be entered.').t();
                    } else {
                        delete obj.predicateErrorMsg;
                    }
                    break;
                case 'order':
                    if (_.isEmpty(field.value.match(/^[0-9]+$/)) || field.value === '0') {
                        obj.orderErrorMsg = _('Order must be a positive integer.').t();
                    } else if (parseInt(field.value, 10) > _.size(this.props.rules)) {
                        obj.orderErrorMsg = _('Order cannot be larger than the total number of rules.').t();
                    } else {
                        delete obj.orderErrorMsg;
                    }
                    break;
                case 'workload_pool':
                    if (_.isEmpty(field.value) && (obj.action === 'move' || obj.action === '')) {
                        obj.poolErrorMsg = _('Workload Pool must be selected.').t();
                    } else {
                        delete obj.poolErrorMsg;
                    }
                    break;
                default:
                    break;
            }
        });
        obj.nameError = !_.isEmpty(obj.nameErrorMsg);
        obj.predicateError = !_.isEmpty(obj.predicateErrorMsg);
        obj.orderError = !_.isEmpty(obj.orderErrorMsg);
        obj.actionError = !_.isEmpty(obj.actionErrorMsg);
        obj.poolError = !_.isEmpty(obj.poolErrorMsg);

        this.setState({
            stateObj: obj,
        });
    }

    handleRuleUpdateModalSubmit = () => {
        // do form validation
        this.validateRuleFields([{
            name: 'predicate',
            value: this.state.ruleUpdateModalState.predicate,
        }, {
            name: 'workload_pool',
            value: this.state.ruleUpdateModalState.workload_pool,
        }, {
            name: 'action',
            value: this.state.ruleUpdateModalState.action,
        }], this.state.ruleUpdateModalState);

        if (this.state.ruleUpdateModalState.edit) {
            this.validateRuleFields([{
                name: 'order',
                value: this.state.ruleUpdateModalState.order,
            }], this.state.ruleUpdateModalState);
        } else {
            this.validateRuleFields([{
                name: 'name',
                value: this.state.ruleUpdateModalState.name,
            }], this.state.ruleUpdateModalState);
        }

        if (this.state.ruleUpdateModalState.nameError ||
            this.state.ruleUpdateModalState.predicateError ||
            this.state.ruleUpdateModalState.orderError ||
            this.state.ruleUpdateModalState.actionError ||
            this.state.ruleUpdateModalState.poolError) {
            return;
        }

        // send request to backend
        this.setWaitView('ruleUpdateModalState');
        const data = {
            name: this.state.ruleUpdateModalState.name,
            predicate: this.state.ruleUpdateModalState.predicate,
            schedule: this.state.ruleUpdateModalState.schedule,
            action: this.state.ruleUpdateModalState.action,
        };

        if (!_.isEmpty(this.state.ruleUpdateModalState.schedule)) {
            data.start_time = this.state.ruleUpdateModalState.start_time;
            data.end_time = this.state.ruleUpdateModalState.end_time;
        }
        if (this.state.ruleUpdateModalState.schedule === 'time_range') {
            data.start_date = this.state.ruleUpdateModalState.start_date;
            data.end_date = this.state.ruleUpdateModalState.end_date;
        }
        if (this.state.ruleUpdateModalState.schedule === 'every_week') {
            const everyWeekDays = (this.state.ruleUpdateModalState.every_week_days) ?
            this.state.ruleUpdateModalState.every_week_days.toString() : null;
            data.every_week_days = everyWeekDays;
        }
        if (this.state.ruleUpdateModalState.schedule === 'every_month') {
            const everyMonthDays = (this.state.ruleUpdateModalState.every_month_days) ?
                this.state.ruleUpdateModalState.every_month_days.toString() : null;
            data.every_month_days = everyMonthDays;
        }
        if (_.isEmpty(this.state.ruleUpdateModalState.action) || this.state.ruleUpdateModalState.action === 'move') {
            data.workload_pool = this.state.ruleUpdateModalState.workload_pool;
        }

        // massage data for edit mode
        let model;
        if (this.state.ruleUpdateModalState.edit) {
            model = this.state.ruleUpdateModalState.model;
            data.order = parseInt(this.state.ruleUpdateModalState.order, 10);
        }

        this.props.rules.updateRule(model, data).done(() => {
            this.props.rules.fetch();
            this.props.status.fetch();
            this.handleRuleUpdateModalClose();
        }).fail((response) => {
            let msg = _('Encountered errors in updating rule').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                msg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.props.rules.fetch();
            this.validateRuleFields([{
                name: 'backendErrorMsg',
                value: msg,
            }, {
                name: 'wait',
                value: false,
            }], this.state.ruleUpdateModalState);
        });
    }


    handleRuleUpdateModalClose = () => {
        this.setState({
            ruleUpdateModalOpen: false,
            ruleUpdateModalState: this.getDefaultRuleUpdateModalState(),
        });
    }

    handleRuleDeleteModalOpen = (e, { value }) => {
        const obj = {
            ruleModel: value,
            title: splunkUtil.sprintf(_('Delete Workload Rule: %s').t(), value.getRuleName()),
        };
        this.setState({
            ruleDeleteModalOpen: true,
            ruleDeleteModalState: obj,
        });
    }

    handleRuleDeleteModalClose = () => {
        this.setState({
            ruleDeleteModalOpen: false,
            ruleDeleteModalState: this.getDefaultRuleDeleteModalState(),
        });
    }

    handleRuleDeleteModalSubmit = () => {
        this.setWaitView('ruleDeleteModalState');
        this.props.rules.deleteRule(this.state.ruleDeleteModalState.ruleModel).done(() => {
            this.props.rules.fetch();
            this.props.status.fetch();
            this.handleRuleDeleteModalClose();
        }).fail((response) => {
            let msg = _('Encountered errors in deleting rule').t();
            if (response.responseJSON.messages && response.responseJSON.messages.length > 0) {
                const messageObj = response.responseJSON.messages[0];
                msg = splunkUtil.sprintf(_('%s: %s').t(), messageObj.type, messageObj.text);
            }
            this.props.rules.fetch();
            this.validateRuleFields([{
                name: 'backendErrorMsg',
                value: msg,
            }, {
                name: 'wait',
                value: false,
            }], this.state.ruleDeleteModalState);
        });
    }

    handleMessageModalOpen = (title, message, type, closeable = true) => {
        const obj = {
            title,
            message,
            type,
            closeable,
            open: true,
        };
        this.setState({
            messageModalState: obj,
        });
    }

    handleMessageModalClose = () => {
        this.setState({
            messageModalState: this.getDefaultMessageModalState(),
        });
    }

    render() {
        return <WorkloadManagementPage {...this.state} />;
    }
}

WorkloadManagementPageContainer.propTypes = {
    category: PropTypes.shape({
        on: PropTypes.func,
        getDefaultSearchPool: PropTypes.arrayOf(PropTypes.shape({})),
        getDefaultIngestPool: PropTypes.arrayOf(PropTypes.shape({})),
        isCategoryAllocated: PropTypes.func,
        models: PropTypes.arrayOf(PropTypes.shape({})),
        prepareCategories: PropTypes.func,
        updateCategory: PropTypes.func,
        fetch: PropTypes.func,
        getDynamicAllocatedCpu: PropTypes.func,
        getDynamicMemAllocatedPercent: PropTypes.func,
    }).isRequired,
    pools: PropTypes.shape({
        models: PropTypes.arrayOf(PropTypes.shape({})),
        on: PropTypes.func,
        fetch: PropTypes.func,
        preparePools: PropTypes.func,
        getDefaultPool: PropTypes.func,
        filterOutIngestMisc: PropTypes.func,
        updatePool: PropTypes.func,
        deletePool: PropTypes.func,
        getDynamicAllocatedCpu: PropTypes.func,
        getDynamicAllocatedMem: PropTypes.func,
        getPoolsByCategory: PropTypes.func,
    }).isRequired,
    rules: PropTypes.shape({
        models: PropTypes.arrayOf(PropTypes.shape({})),
        on: PropTypes.func,
        fetch: PropTypes.func,
        prepareRules: PropTypes.func,
        getRuleActions: PropTypes.func,
        updateRule: PropTypes.func,
        deleteRule: PropTypes.func,
    }).isRequired,
    status: PropTypes.shape({
        on: PropTypes.func,
        isEnabled: PropTypes.func,
        fetch: PropTypes.func,
        getShortErrorMessage: PropTypes.func,
    }).isRequired,
    checks: PropTypes.shape({
        allPreflightChecksPass: PropTypes.func,
        getPreflightChecks: PropTypes.func,
        fetch: PropTypes.func,
    }).isRequired,
    user: PropTypes.shape({
        hasCapability: PropTypes.func,
    }).isRequired,
    enable: PropTypes.instanceOf(Backbone.Model).isRequired,
    disable: PropTypes.instanceOf(Backbone.Model).isRequired,
};

export default WorkloadManagementPageContainer;
