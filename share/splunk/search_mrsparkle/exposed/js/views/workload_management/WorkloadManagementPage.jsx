import { createTestHook } from 'util/test_support';
import _ from 'underscore';
import React from 'react';
import PropTypes from 'prop-types';
import Switch from '@splunk/react-ui/Switch';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import HeaderSection from './HeaderSection';
import CategoryCards from './CategoryCards';
import CategoriesTable from './CategoriesTable';
import PoolsTable from './PoolsTable';
import RulesTable from './RulesTable';
import CategoryUpdateModal from './CategoryUpdateModal';
import PoolUpdateModal from './PoolUpdateModal';
import PoolDeleteModal from './PoolDeleteModal';
import RuleUpdateModal from './RuleUpdateModal';
import RuleDeleteModal from './RuleDeleteModal';
import PreflightChecks from './PreflightChecks';
import MessageModal from './MessageModal';
import css from './WorkloadManagement.pcssm';

const WorkloadManagementPage = (props) => {
    const {
        title,
        description,
        learnMore,
        isEnabled,
        enableSettingsViewBtn,
        categoryUpdateModalOpen,
        categoryUpdateModalState,
        handleCategoryUpdateModalClose,
        handleCategoryUpdateModalTextChange,
        handleCategoryUpdateModalSubmit,
        handleCategoryUpdateModalOpenEdit,
        handleCategoryClick,
        handleCategoryRowNameClick,
        categoryCardState,
        categories,
        handleReRunPreflightCheck,
        handleShowSettingsView,
        handleShowPreFlightCheckView,
        allPreflightChecksPass,
        showPreFlightCheckView,
        isPreflightCheckLoading,
        checks,
        statusErrorMessage,
        missingTablesMessage,
        getDefaultSearchPool,
        getDefaultIngestPool,
        getSearchPools,
        getIngestPools,
        getMiscPools,
        isSearchCategoryAllocated,
        isIngestCategoryAllocated,
        isMiscCategoryAllocated,
        pools,
        rules,
        canEditWorkloadPools,
        canEditWorkloadRules,
        poolUpdateModalOpen,
        poolUpdateModalState,
        handleEnableDisableClick,
        handlePoolUpdateModalOpen,
        handlePoolUpdateModalClose,
        handlePoolUpdateModalOpenEdit,
        handlePoolUpdateModalTextChange,
        handlePoolUpdateModalCheckbox,
        handlePoolUpdateModalSubmit,
        poolDeleteModalOpen,
        poolDeleteModalState,
        handlePoolDeleteModalOpen,
        handlePoolDeleteModalClose,
        handlePoolDeleteModalSubmit,
        ruleUpdateModalOpen,
        ruleUpdateModalState,
        handleRuleUpdateModalOpen,
        handleRuleUpdateModalClose,
        handleRuleUpdateModalOpenEdit,
        handleRuleUpdateModalTextChange,
        handleRuleUpdateModalMultiSelectChange,
        handleRuleUpdateModalSubmit,
        ruleDeleteModalOpen,
        ruleDeleteModalState,
        handleRuleDeleteModalOpen,
        handleRuleDeleteModalClose,
        handleRuleDeleteModalSubmit,
        messageModalState,
        handleMessageModalClose,
        handleTabBarChange,
        tabBarState,
    } = props;

    const headerSectionProps = {
        title,
        description,
        learnMore,
        handleTabBarChange,
        tabBarState,
    };

    const categoryCardsSectionProps = {
        canEditWorkloadPools,
        handleCategoryUpdateModalOpenEdit,
        handleCategoryClick,
        categoryCardState,
        categories,
    };

    const categoryUpdateModalProps = {
        categoryUpdateModalOpen,
        categoryUpdateModalState,
        handleCategoryUpdateModalClose,
        handleCategoryUpdateModalTextChange,
        handleCategoryUpdateModalSubmit,
    };

    const categoriesTableProps = {
        categoryCardState,
        handleCategoryRowNameClick,
        categories,
        canEditWorkloadPools,
        handleCategoryUpdateModalOpenEdit,
    };

    const poolsTableProps = {
        pools,
        canEditWorkloadPools,
        handlePoolUpdateModalOpenEdit,
        handlePoolDeleteModalOpen,
        categoryCardState,
    };

    const rulesTableProps = {
        rules,
        ruleUpdateModalState,
        canEditWorkloadRules,
        handleRuleUpdateModalOpenEdit,
        handleRuleDeleteModalOpen,
    };

    const poolUpdateModalProps = {
        poolUpdateModalOpen,
        poolUpdateModalState,
        handlePoolUpdateModalClose,
        handlePoolUpdateModalTextChange,
        handlePoolUpdateModalCheckbox,
        handlePoolUpdateModalSubmit,
    };

    const poolDeleteModalProps = {
        poolDeleteModalOpen,
        poolDeleteModalState,
        handlePoolDeleteModalClose,
        handlePoolDeleteModalSubmit,
    };

    const ruleUpdateModalProps = {
        ruleUpdateModalOpen,
        ruleUpdateModalState,
        handleRuleUpdateModalClose,
        handleRuleUpdateModalTextChange,
        handleRuleUpdateModalMultiSelectChange,
        handleRuleUpdateModalSubmit,
    };

    const ruleDeleteModalProps = {
        ruleDeleteModalOpen,
        ruleDeleteModalState,
        handleRuleDeleteModalClose,
        handleRuleDeleteModalSubmit,
    };

    const messageModalProps = {
        messageModalState,
        handleMessageModalClose,
    };

    const preflightChecksProps = {
        enableSettingsViewBtn,
        handleReRunPreflightCheck,
        handleShowSettingsView,
        isPreflightCheckLoading,
        checks,
    };

    const mainSectionClassName = `workload-main-section ${css.mainSection}`;
    const isPoolTableEmpty = (pools.length === 0);
    const isRuleTableEmpty = (rules.length === 0);
    const settingsView = (showPreFlightCheckView ? `${css.displayNone}` : '');
    const preFlightCheckView = (showPreFlightCheckView ? '' : `${css.displayNone}`);
    const preflightChecksFail = (allPreflightChecksPass ? `${css.displayNone}` : '');
    const eligibleToEnable = canEditWorkloadPools && !_.isEmpty(getDefaultSearchPool) &&
        !_.isEmpty(getDefaultIngestPool);

    let requiredSearchPoolMessage = '';
    let requiredIngestPoolMessage = '';
    if (!isEnabled && canEditWorkloadPools && _.isEmpty(getDefaultSearchPool)) {
        requiredSearchPoolMessage = _('You must create a default search pool ' +
            'before enabling workload management.').t();
    }

    if (!isEnabled && canEditWorkloadPools && _.isEmpty(getDefaultIngestPool)) {
        requiredIngestPoolMessage = _('You must create a default ingest pool ' +
            'before enabling workload management.').t();
    }

    let searchCategoryUnderUtilized = '';
    if (_.isEmpty(getSearchPools) && isSearchCategoryAllocated) {
        searchCategoryUnderUtilized = _('You must create a workload pool in the search category to ' +
            'allocate resources available in the search category.').t();
    }

    let ingestCategoryUnderUtilized = '';
    if (_.isEmpty(getIngestPools) && isIngestCategoryAllocated) {
        ingestCategoryUnderUtilized = _('You must create a workload pool in the ingest category to ' +
            'allocate resources available in the ingest category.').t();
    }

    let miscCategoryUnderUtilized = '';
    if (_.isEmpty(getMiscPools) && isMiscCategoryAllocated) {
        miscCategoryUnderUtilized = _('You must create a workload pool in the misc category to ' +
            'allocate resources available in the misc category.').t();
    }

    return (
        <div {...createTestHook(module.id)}>
            <HeaderSection {...headerSectionProps}>
                { canEditWorkloadPools || canEditWorkloadRules ?
                    <div className={`buttons-wrapper ${settingsView}`}>
                        { canEditWorkloadRules ?
                            <Button
                                style={{ float: 'right', marginLeft: '10px' }}
                                disabled={_.isEmpty(getSearchPools)}
                                label={_('Add Workload Rule').t()}
                                onClick={handleRuleUpdateModalOpen}
                            /> : null
                        }
                        { canEditWorkloadPools ?
                            <Button
                                style={{ float: 'right', marginLeft: '10px' }}
                                label={_('Add Workload Pool').t()}
                                onClick={handlePoolUpdateModalOpen}
                            /> : null
                        }
                        <Switch
                            style={{ float: 'right' }}
                            disabled={!eligibleToEnable}
                            selected={isEnabled}
                            value={isEnabled}
                            appearance="toggle"
                            onClick={handleEnableDisableClick}
                        >
                            { isEnabled ? _('Enabled').t() : _('Disabled').t() }
                        </Switch>
                    </div> : null
                }
            </HeaderSection>
            <div className={`${mainSectionClassName} ${settingsView}`}>
                { !isEnabled && eligibleToEnable ?
                    <Message type="info">{_('To activate workload management, ' +
                        'set the switch to Enabled.').t()}</Message>
                    : null
                }

                <div className={`${css.preFlightCheckSettingsPageMsg} ${preflightChecksFail}`}>
                    <Message type="error">
                        {_('Preflight checks failed.').t()} &nbsp;
                    </Message>
                    <Button
                        label={_('View preflight checks').t()}
                        appearance="pill"
                        onClick={handleShowPreFlightCheckView}
                        classNamePrivate={css.link}
                    />
                </div>

                { !_.isEmpty(statusErrorMessage) && isEnabled && (canEditWorkloadPools || canEditWorkloadRules) ?
                    <Message type="error">{statusErrorMessage}</Message>
                    : null
                }

                { !_.isEmpty(missingTablesMessage) ?
                    <Message type="info">{missingTablesMessage}</Message>
                    : null
                }

                { !_.isEmpty(requiredSearchPoolMessage) ?
                    <Message type="info">{requiredSearchPoolMessage}</Message>
                    : null
                }

                { !_.isEmpty(requiredIngestPoolMessage) ?
                    <Message type="info">{requiredIngestPoolMessage}</Message>
                    : null
                }

                { !_.isEmpty(searchCategoryUnderUtilized) ?
                    <Message type="info">{searchCategoryUnderUtilized}</Message>
                    : null
                }

                { !_.isEmpty(ingestCategoryUnderUtilized) ?
                    <Message type="info">{ingestCategoryUnderUtilized}</Message>
                    : null
                }

                { !_.isEmpty(miscCategoryUnderUtilized) ?
                    <Message type="info">{miscCategoryUnderUtilized}</Message>
                    : null
                }

                <div style={{ display: tabBarState === 'pools' ? 'block' : 'none' }}>
                    <CategoryCards {...categoryCardsSectionProps} />
                    <CategoriesTable {...categoriesTableProps} />
                    { isPoolTableEmpty ? null : <PoolsTable {...poolsTableProps} /> }
                </div>

                <div style={{ display: tabBarState === 'pools' ? 'none' : 'block' }}>
                    { isRuleTableEmpty ? null : <RulesTable {...rulesTableProps} /> }
                </div>

                <CategoryUpdateModal {...categoryUpdateModalProps} />
                <PoolUpdateModal {...poolUpdateModalProps} />
                <PoolDeleteModal {...poolDeleteModalProps} />
                <RuleUpdateModal {...ruleUpdateModalProps} />
                <RuleDeleteModal {...ruleDeleteModalProps} />
                <MessageModal {...messageModalProps} />
            </div>

            <div className={`${mainSectionClassName} ${preFlightCheckView}`}>
                <PreflightChecks {...preflightChecksProps} />
            </div>
        </div>
    );
};

WorkloadManagementPage.propTypes = {
    title: PropTypes.string,
    description: PropTypes.string,
    learnMore: PropTypes.shape({}).isRequired,
    isEnabled: PropTypes.bool.isRequired,
    enableSettingsViewBtn: PropTypes.bool.isRequired,
    categoryUpdateModalOpen: PropTypes.bool.isRequired,
    categoryUpdateModalState: PropTypes.shape({}).isRequired,
    handleCategoryUpdateModalClose: PropTypes.func.isRequired,
    handleCategoryUpdateModalTextChange: PropTypes.func.isRequired,
    handleCategoryUpdateModalSubmit: PropTypes.func.isRequired,
    handleCategoryUpdateModalOpenEdit: PropTypes.func.isRequired,
    handleCategoryClick: PropTypes.func.isRequired,
    handleCategoryRowNameClick: PropTypes.func.isRequired,
    categoryCardState: PropTypes.shape({}).isRequired,
    categories: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    handleReRunPreflightCheck: PropTypes.func.isRequired,
    handleShowSettingsView: PropTypes.func.isRequired,
    handleShowPreFlightCheckView: PropTypes.func.isRequired,
    allPreflightChecksPass: PropTypes.bool.isRequired,
    showPreFlightCheckView: PropTypes.bool.isRequired,
    isPreflightCheckLoading: PropTypes.bool.isRequired,
    checks: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    statusErrorMessage: PropTypes.string.isRequired,
    missingTablesMessage: PropTypes.string.isRequired,
    getDefaultSearchPool: PropTypes.shape({}),
    getDefaultIngestPool: PropTypes.shape({}),
    getSearchPools: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    getIngestPools: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    getMiscPools: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    isSearchCategoryAllocated: PropTypes.bool.isRequired,
    isIngestCategoryAllocated: PropTypes.bool.isRequired,
    isMiscCategoryAllocated: PropTypes.bool.isRequired,
    pools: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    rules: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
    canEditWorkloadPools: PropTypes.bool.isRequired,
    canEditWorkloadRules: PropTypes.bool.isRequired,
    poolUpdateModalOpen: PropTypes.bool,
    poolUpdateModalState: PropTypes.shape({}).isRequired,
    handleEnableDisableClick: PropTypes.func.isRequired,
    handlePoolUpdateModalOpen: PropTypes.func.isRequired,
    handlePoolUpdateModalClose: PropTypes.func.isRequired,
    handlePoolUpdateModalOpenEdit: PropTypes.func.isRequired,
    handlePoolUpdateModalTextChange: PropTypes.func.isRequired,
    handlePoolUpdateModalCheckbox: PropTypes.func.isRequired,
    handlePoolUpdateModalSubmit: PropTypes.func.isRequired,
    poolDeleteModalOpen: PropTypes.bool,
    poolDeleteModalState: PropTypes.shape({}).isRequired,
    handlePoolDeleteModalOpen: PropTypes.func.isRequired,
    handlePoolDeleteModalClose: PropTypes.func.isRequired,
    handlePoolDeleteModalSubmit: PropTypes.func.isRequired,
    ruleUpdateModalOpen: PropTypes.bool,
    ruleUpdateModalState: PropTypes.shape({}).isRequired,
    handleRuleUpdateModalOpen: PropTypes.func.isRequired,
    handleRuleUpdateModalClose: PropTypes.func.isRequired,
    handleRuleUpdateModalOpenEdit: PropTypes.func.isRequired,
    handleRuleUpdateModalTextChange: PropTypes.func.isRequired,
    handleRuleUpdateModalMultiSelectChange: PropTypes.func.isRequired,
    handleRuleUpdateModalSubmit: PropTypes.func.isRequired,
    ruleDeleteModalOpen: PropTypes.bool,
    ruleDeleteModalState: PropTypes.shape({}).isRequired,
    handleRuleDeleteModalOpen: PropTypes.func.isRequired,
    handleRuleDeleteModalClose: PropTypes.func.isRequired,
    handleRuleDeleteModalSubmit: PropTypes.func.isRequired,
    messageModalState: PropTypes.shape({}).isRequired,
    handleMessageModalClose: PropTypes.func.isRequired,
    handleTabBarChange: PropTypes.func.isRequired,
    tabBarState: PropTypes.string.isRequired,
};

WorkloadManagementPage.defaultProps = {
    title: '',
    description: '',
    poolUpdateModalOpen: false,
    poolDeleteModalOpen: false,
    ruleUpdateModalOpen: false,
    ruleDeleteModalOpen: false,
    getDefaultSearchPool: {},
    getDefaultIngestPool: {},
};

export default WorkloadManagementPage;
