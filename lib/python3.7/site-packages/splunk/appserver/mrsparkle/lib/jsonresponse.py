# coding=utf-8

from builtins import object
import json
import splunk
import splunk.util


class JsonResponse(object):
    
    def __init__(self):
        self.success  = True
        self.offset   = 0
        self.count    = 0
        self.total    = 0
        self.messages = []
        self.data     = None
        
    def __str__(self):
        return self.toJson()

    def addMessage(self, level, message, **kw):
        # TODO rename 'type' to 'level'
        kw.update({'type': splunk.util.toDefaultStrings(level), 'message': splunk.util.toDefaultStrings(message), 'time': splunk.util.getISOTime()})
        self.messages.append(kw)

    def addFatal(self, message, **kw):
        self.addMessage('FATAL', message, **kw)
    
    def addError(self, message, **kw):
        self.addMessage('ERROR', message, **kw)
    
    def addInfo(self, message, **kw):
        self.addMessage('INFO', message, **kw)
    
    def addWarn(self, message, **kw):
        self.addMessage('WARN', message, **kw)
    
    def addDebug(self, message, **kw):
        self.addMessage('DEBUG', message, **kw)
        
    def toJson(self, **kwargs):
        '''
        return a json encoded string for the response
        '''
        # egregious hack?
        return json.dumps(self.__dict__, **kwargs)

    def parseRESTException(self, e):
        '''
        Inspects a splunk.RESTException object and extracts the messages passed
        over by splunkd into the current jsonresponse object
        '''

        if not isinstance(e, splunk.RESTException):
            self.addError(e)
            return
            
        prefix = _('[Splunkd Error (%s)] ') % e.statusCode
        if e.extendedMessages:
            for item in e.extendedMessages:
                if item['type'] == 'FATAL': self.addFatal(prefix + item['text'])
                elif item['type'] == 'ERROR': self.addError(prefix + item['text'])
                elif item['type'] == 'WARN': self.addWarn(prefix + item['text'])
                elif item['type'] == 'INFO': self.addInfo(prefix + item['text'])
                elif item['type'] == 'DEBUG': self.addDebug(prefix + item['text'])
        else:
            self.addError(prefix + splunk.util.toDefaultStrings(e))
            
            
# Tests
def unit_test():
    j = JsonResponse()
    j.addInfo("captain! there's an iceburg ahead!!")
    j.addWarn("captain! we're about to hit the iceburg!")
    j.addError("captain! our ship is sinking!")
    j.addDebug("fatal error. ship has sunk to bottom of ocean.")
    j.addFatal("fatal error. ship broke.")
    j.addInfo('KivimÃ¤ki2')
    assert j.messages[0] == {'type':'INFO', 'message':"captain! there's an iceburg ahead!!"}
    assert j.messages[1] == {'type':'WARN', 'message':"captain! we're about to hit the iceburg!"}
    assert j.messages[2] == {'type':'ERROR', 'message':"captain! our ship is sinking!"}
    assert j.messages[3] == {'type':'DEBUG', 'message':"fatal error. ship has sunk to bottom of ocean."}
    assert j.messages[4] == {'type':'FATAL', 'message':"fatal error. ship broke."}
    assert isinstance(j.toJson(), str)

if __name__ == '__main__':
    unit_test()
