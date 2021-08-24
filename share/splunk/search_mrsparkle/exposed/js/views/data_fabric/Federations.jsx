import React from 'react';
import $ from 'jquery';
import Text from '@splunk/react-ui/Text';
import Paginator from '@splunk/react-ui/Paginator';
import Select from '@splunk/react-ui/Select';
import ReactAdapterBase from 'views/ReactAdapterBase';
import BackboneProvider from 'dashboard/components/shared/BackboneProvider';
import { _ } from '@splunk/ui-utils/i18n';
import BaseModel from 'models/Base';
import { sprintf } from '@splunk/ui-utils/format';
import { getPaginatedItems } from 'util/dfs/TableUtils';
import SetFederationsModal from './SetFederationsModal';
import FederationsTable from './FederationsTable';
import HeaderComp from './DFSPageHeader';

import './DataFabric.pcss';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @constructor
     * @memberOf views
     * @name Federations
     * @extends {views.ReactAdapterBase}
     * @description A page to manage federated providers.
     *
     * @param {Object} options
     */
    initialize(options) {
        this.store = {};

        ReactAdapterBase.prototype.initialize.apply(this, options);

        const providers = this.collection.federations.map(fsh => fsh.entry.get('name'));
        this.model = new BaseModel({ filter: '', providers, page: 1, rowPerPage: 10 });

        this.modalModel = new BaseModel({ open: false, type: 'add', provider: {} });
        this.saveAsDialog = new SetFederationsModal({
            model: {
                state: this.modalModel,
            },
            collection: {
                fshRoles: this.collection.fshRoles,
            },
            checkName: (newName) => {
                const trimmedName = newName.trim();
                if (this.model.get('providers').indexOf(trimmedName) > -1) {
                    return _("This name isn't available. Enter another name.");
                }
                return '';
            },
        });
        this.saveAsDialog.render().appendTo($('body'));
        // update federations after saving
        this.listenTo(this.saveAsDialog, 'federatedProviderSaved', () => {
            this.collection.federations.fetch({
                data: { count: 0 },
                success: () => {
                    this.model.set('providers', this.collection.federations.map(fsh => fsh.entry.get('name')));
                    this.render();
                },
            });
        });

        this.listenTo(this.model, 'change:filter', this.render);
        this.listenTo(this.model, 'change:page', this.render);
        this.listenTo(this.model, 'change:rowPerPage', this.render);

        // functions
        this.handleFilterChange = this.handleFilterChange.bind(this);
        this.handleEditFederation = this.handleEditFederation.bind(this);
        this.handleDeleteFederation = this.handleDeleteFederation.bind(this);
        this.handleChangePage = this.handleChangePage.bind(this);
    },

    handleFilterChange(e, { value }) {
        this.model.set({ filter: value, page: 1 });
    },

    handleEditFederation(federation) {
        this.saveAsDialog.model.savedFederation = federation;
        const providerName = federation.entry.get('name');
        const roles = this.collection.fshRoles.getRolesByProvider(providerName);
        this.saveAsDialog.collection.selectedRoles = roles;

        this.modalModel.set({ type: 'edit', open: true });
    },

    handleChangePage(e, { page, value }) {
        if (page) {
            this.model.set('page', page);
        } else {
            this.model.set({ rowPerPage: value, page: 1 });
        }
    },

    handleDeleteFederation() {
        this.model.set('providers', this.collection.federations.map(fsh => fsh.entry.get('name')));
        this.render();
    },

    renderContent() {
        const noProviders = (
            <h2
                data-test="no-federations-page"
                className="no-federations-page grey-text"
                key="no-federations-header"
            >
                {_('No federated providers')}
            </h2>
        );

        const filterFederations =
            this.model.get('filter').length > 0
                ? this.collection.federations.models.filter(
                      federation => federation.entry.get('name').indexOf(this.model.get('filter')) > -1,
                  )
                : this.collection.federations.models;

        let content;
        if (!this.collection.federations.models) {
            content = noProviders;
        } else {
            const providersAmount = filterFederations.length;
            const providersAmountStr = providersAmount === 1
                ? sprintf(_('%(number)d Federated Provider'), { number: providersAmount })
                : sprintf(_('%(number)d Federated Providers'), { number: providersAmount });

            const totalPage = Math.ceil(filterFederations.length / this.model.get('rowPerPage'));
            const paginatedFederations =
                getPaginatedItems(filterFederations, this.model.get('page'), this.model.get('rowPerPage'));

            const providerTable = filterFederations.length === 0
                ? noProviders
                : (<FederationsTable
                    key="federations-table"
                    federations={paginatedFederations}
                    refreshDfs={this.handleDeleteFederation}
                    edit={this.handleEditFederation}
                    fshRoles={this.collection.fshRoles}
                />);

            content = [
                <div key="federations-content" className="federations-filter-container">
                    <div data-test="providers-count" className="federations-count">{providersAmountStr}</div>
                    <Text
                        data-test="federations-filter"
                        key="federations-filter"
                        placeholder={_('Filter')}
                        value={this.model.get('filter')}
                        onChange={this.handleFilterChange}
                        appearance="search"
                        style={{ maxWidth: '200px' }}
                        aria-label={_('Filter federated providers by Name')}
                    />
                    <div>
                        <Select
                            data-test="row-selector"
                            appearance="pill"
                            value={this.model.get('rowPerPage')}
                            onChange={this.handleChangePage}
                        >
                            {[10, 20, 50, 100].map(rowPerPage => (
                                <Select.Option
                                    key={`${rowPerPage}-rows`}
                                    label={sprintf(_('%(rowPerPage)d per page'), { rowPerPage })}
                                    value={rowPerPage}
                                />
                            ))}
                        </Select>
                        {totalPage > 1 && <Paginator
                            data-test="federations-paginator"
                            onChange={this.handleChangePage}
                            current={this.model.get('page')}
                            alwaysShowLastPageLink
                            totalPages={totalPage}
                        />}
                    </div>
                </div>,
                providerTable,
            ];
        }
        return (
            <div>
                <HeaderComp
                    openModal={() => {
                        this.modalModel.set({ type: 'add', open: true });
                    }}
                />
                <div key="federations" data-test="federations-table" className="federations-table">
                    {content}
                </div>
            </div>
        );
    },

    getComponent() {
        return (
            <BackboneProvider key="federations-page" store={this.store} model={this.model}>
                {this.renderContent()}
            </BackboneProvider>
        );
    },
});
