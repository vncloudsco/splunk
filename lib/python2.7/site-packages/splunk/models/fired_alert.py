'''
Provides object mapping for fired alerts objects

Example use case:

### saved search  access pattern #### 
   sessionKey = splunk.auth.getSessionKey('admin','changeme')
   s = SavedSearch.get('/servicesNS/admin/search/admin/savedsearch/someAlert')
   alerts = s.get_alerts()
   
   # print them all
   for a in alerts:
       print("%s %s %s" % (a.severity, a.trigger_time, action))

   #now delete the most recent one
   alerts[0].delete()

### most recent alerts access pattern ####

   sessionKey = splunk.auth.getSessionKey('admin','changeme')
   alerts = FiredAlert.all()
   alerts._count_per_req = 30  # fetch 30 at once
   
   # print 30 most recent triggered alerts
   for a in alerts[:30]:
      print("%s %s %s %s" % (a.savedsearch_name, a.severity, a.trigger_time, action))


'''

from splunk.models.base import SplunkQuerySet
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, IntField, EpochField, ListField, BoolField



class FiredAlert(SplunkAppObjModel):
    '''
    Represents a Splunk fired/triggered alert
    '''

    resource = 'alerts/fired_alerts/-'

    actions          = ListField()
    alert_type       = Field()
    savedsearch_name = Field()
    sid              = Field()
    severity         = IntField()
    trigger_time     = EpochField()
    # these are rendered time string in the current user's timezone
    trigger_time_rendered = Field()
    expiration_time_rendered  = Field()
    digest_mode      = BoolField()
    triggered_alerts = IntField()

    def get_savedsearch(self):
        from splunk.models.saved_search import SavedSearch
        return SavedSearch.get(self.entity.getLink('savedsearch'))       

    def get_job(self):
      job_id = self.entity.getLink('job')
      #TODO: return a search job object
      return None

    @classmethod
    def get_alerts(cls, alerts_id):
        '''
        Returns a SplunkQuerySet that can be used to access the alerts fired by the given id.
        The SplunkQuerySet can be modified to include a search, custom ordering etc..

        example alerts_id:
           absolute: https://localhost:8089/servicesNS/nobody/search/aalerts/fired_alerts/AlertTest1
           relative: /servicesNS/nobody/search/alerts/fired_alerts/AlertTest1 
        '''

        k      = SplunkQuerySet(FiredAlert.manager(), 30)
        k._uri = alerts_id
        return k 

    

class FiredAlertSummary(SplunkAppObjModel):
    '''
    Represents a Splunk fired/triggered alert summary
    '''

    resource = 'alerts/fired_alerts'

    triggered_alert_count = IntField()


