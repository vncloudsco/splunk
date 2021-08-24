import SplunkDBaseModel from 'models/SplunkDBase';
import timeUtils from 'util/time';

export default SplunkDBaseModel.extend({
    urlRoot: 'services/shcluster/member/members',
    isCaptain() {
        return this.entry.content.get('is_captain') || false;
    },
    getRoleLabel() {
        return this.entry.content.get('is_captain') ? 'Captain' : 'Member';
    },
    getLastHeartBeatAsLocalTime() {
        return timeUtils.convertToLocalTime(this.entry.content.get('last_heartbeat')) || '';
    },
    getSHMemberStatus() {
        return this.entry.content.get('status') || '';
    },
    getMgmtUri() {
        return this.entry.content.get('mgmt_uri') || '';
    },
    getMemberName() {
        return this.entry.content.get('label') || '';
    },
});