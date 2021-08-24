import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import Modal from 'views/shared/Modal';
import FlashMessagesView from 'views/shared/FlashMessages';
import ControlGroup from 'views/shared/controls/ControlGroup';
import splunkDUtils from 'util/splunkd_utils';
import route from 'uri/route';
import SearchableSwitchView from './components/RollingDialog/Master';
import './RollingRestartDialog.pcss';

export default Modal.extend({
    moduleId: module.id,
    className: `${Modal.CLASS_NAME}`,
    /**
     * @param {Object} options {
     *     model: {
     *         restartCluster: <models.services.cluster.master> To call the rolling restart endpoint.
     *         clusterConfig: <models.services.cluster.Config> Check the config of the index cluster.
     *         masterInfo: <models.services.cluster.master.info> Information about cluster master.
     *         application: <models.Application> required for constructing the doc link.
     *     },
     * }
     */
    initialize(options, ...rest) {
        Modal.prototype.initialize.call(this, options, ...rest);

        // The working model is used to store site order preferences and searchability flags
        this.workingModel = new Backbone.Model({
            enableSiteOrder: false,
            searchable: false,
            force: false,
        });

        this.children.flashMessages = new FlashMessagesView({
            model: {
                clusterConfig: this.model.clusterConfig,
                restartCluster: this.model.restartCluster,
            },
        });

        this.children.percentPeers = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                modelAttribute: 'percent_peers_to_restart',
                model: this.model.clusterConfig.entry.content,
            },
            controlClass: 'percent-peer-text',
            additionalClassNames: 'form-horizontal percent-peer-control',
            label: _('Peer percent').t(),
            help: _('Specify percentage of peers to restart, default is 10.').t(),
        });

        this.workingModel.on('change:searchable', () => {
            this.togglePercentPeerView();
        });

        this.children.searchableSwitchView = new SearchableSwitchView({
            model: this.workingModel,
        });

        if (this.model.masterInfo.isMultiSite()) {
            this.children.siteOrderLabel = new ControlGroup({
                controlType: 'SyntheticCheckbox',
                controlOptions: {
                    modelAttribute: 'enableSiteOrder',
                    model: this.workingModel,
                },
                label: _('Site Order').t(),
                controlClass: 'site-order-checkbox',
                additionalClassNames: 'form-horizontal site-order-control',
            });
            this.constructSitesDropdown();

            this.workingModel.on('change:enableSiteOrder', () => {
                _.each(this.rowKeys, (key) => {
                    if (this.workingModel.get('enableSiteOrder')) {
                        this.children[key].$el.show();
                    } else {
                        this.children[key].$el.hide();
                    }
                });
            });
        }
    },

    togglePercentPeerView() {
        if (this.workingModel.get('searchable')) {
            this.children.percentPeers.$el.hide();
        } else {
            this.children.percentPeers.$el.show();
        }
    },

    /**
     * Construct select dropdown for each site returned by the availableSites in masterInfo and
     * add to the children hash of this view.
     */
    constructSitesDropdown() {
        const sites = this.model.masterInfo.getAvailableSites();

        for (let i = 0; i < sites.length; i += 1) {
            const rowId = `row${i}`;
            this.workingModel.set(rowId, sites[i]);
            this.children[rowId] = new ControlGroup({
                label: `${i + 1} . `,
                className: 'control-group',
                controlType: 'SyntheticSelect',
                controlClass: 'sites-dropdown',
                additionalClassNames: 'site-menu form-horizontal',
                controlOptions: {
                    additionalClassNames: 'view-count',
                    model: this.workingModel,
                    modelAttribute: rowId,
                    toggleClassName: 'btn',
                    popdownOptions: {
                        attachDialogTo: '.modal:visible',
                        scrollContainer: '.modal:visible .modal-body:visible',
                    },
                    items: sites.map((site) => {
                        const obj = {
                            label: site,
                            value: site,
                        };
                        return obj;
                    }),
                },
            });
        }
    },

    events: $.extend({}, Modal.prototype.events, {
        'click a.modal-btn-primary': function onClick(e) {
            e.preventDefault();
            if (this.workingModel.get('enableSiteOrder') && this.model.masterInfo.isMultiSite()) {
                const siteOrder = this.rowKeys.reduce((order, key) => {
                    const o = `${order}${this.workingModel.get(key)},`;
                    return o;
                }, '');
                this.model.clusterConfig.save({
                    percent_peers_to_restart: this.model.clusterConfig.entry.content.get('percent_peers_to_restart'),
                    wait: true,
                }, {
                    patch: true,
                }).done(() => {
                    this.model.restartCluster.save({
                        // replace the last comma and any whitespace after comma in the site order string.
                        'site-order': siteOrder.replace(/,(\s+)?$/, ''),
                        searchable: this.workingModel.get('searchable'),
                        force: this.workingModel.get('force'),
                    }, {
                        success: () => {
                            this.hide();
                        },
                    });
                });
            } else {
                this.model.clusterConfig.save({
                    percent_peers_to_restart: this.model.clusterConfig.entry.content.get('percent_peers_to_restart'),
                    wait: true,
                }, {
                    patch: true,
                }).done(() => {
                    this.model.restartCluster.save({
                        searchable: this.workingModel.get('searchable'),
                        force: this.workingModel.get('force'),
                    }, {
                        success: () => {
                            this.hide();
                        },
                    });
                });
            }
        },
    }),

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Index Cluster Rolling Restart').t());
        const root = this.model.application.get('root');
        const locale = this.model.application.get('locale');
        const docLink = route.docHelp(root, locale, 'learnmore.idxc.rollingrestart');
        const errMessage = `${_('Are you sure you want to initiate a rolling restart? ' +
            'This action puts the cluster into maintenance mode. ').t()} <a href=${docLink} class="external"
            target="_blank"> ${_('Learn more.').t()}</a>`;

        this.children.flashMessages.flashMsgHelper
            .addGeneralMessage('cluster_rolling_restart',
            {
                type: splunkDUtils.WARNING,
                html: errMessage,
            });
        this.$(Modal.BODY_SELECTOR).append(this.children.flashMessages.render().$el);
        this.$(Modal.BODY_SELECTOR).append(this.children.searchableSwitchView.activate({ deep: true }).render().$el);
        this.$(Modal.BODY_SELECTOR).append(this.children.percentPeers.render().$el);
        this.togglePercentPeerView();
        this.$(Modal.BODY_SELECTOR).find('.percent-peer-text .control')
            .append('<span class="add-on">%</span>');
        if (this.children.siteOrderLabel) {
            this.$(Modal.BODY_SELECTOR).append(this.children.siteOrderLabel.render().$el);
            this.rowKeys = Object.keys(this.children).filter(key => key.includes('row'));
            _.each(this.rowKeys, (key) => {
                this.$(Modal.BODY_SELECTOR).append(this.children[key].render().$el);
                if (this.workingModel.get('enableSiteOrder')) {
                    this.children[key].$el.show();
                } else {
                    this.children[key].$el.hide();
                }
            });
        }
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
        this.$(Modal.FOOTER_SELECTOR).append(`
            <a href="#" class="btn btn-primary modal-btn-primary pull-right">
                ${_('Begin Rolling Restart').t()}
            </a>`);
        return this;
    },
});

