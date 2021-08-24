import sys
from xml.sax import ContentHandler, parse
from optparse import OptionParser

class PeerBucketFlags:
    def __init__(self):
        self.primary = False
        self.searchable = False

class Bucket:
    def __init__(self):
        self.peer_flags = {}  # key is peer guid
        self.frozen = False
        
class BucketHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)
        self.buckets = {}
        self.in_entry = False
        self.in_peers = False
        self.save_title = False
        self.save_frozen = False
        self.peer_nesting = 0
        self.current_peer_flags = {}
        self.current_guid = None
        self.current_frozen_flag = ''
        self.current_peer_field = None
        self.current_peer_field_value = ''
        self.current_bucket = ''

    def getBuckets(self):
        return self.buckets
            
    def startDocument(self):
        pass

    def endDocument(self):
        pass
        
    def startElement(self, name, attrs):
        if name == 'entry':
            self.in_entry = True
        elif self.in_entry and name == 'title':
            self.save_title = True
        elif self.in_entry and name == 's:key' and attrs.get('name') == 'frozen':
            self.save_frozen = True
        elif name == 's:key' and attrs.get('name') == 'peers':
            self.in_peers = True
        elif self.in_peers and name == 's:key':
            self.peer_nesting += 1
            if self.peer_nesting == 1:
                self.current_peer_flags = PeerBucketFlags()
                self.current_guid = attrs.get('name').encode('ascii')
            elif self.peer_nesting == 2:
                self.current_peer_field = attrs.get('name').encode('ascii')
                self.current_peer_field_value = ''

    def endElement(self,name):
        if name == 'entry':
            self.in_entry = False
            self.current_bucket=''
        elif self.save_title:
            try:
                (idx, local_id, origin_guid) = self.current_bucket.split('~')
            except ValueError as e:
                print("Invalid? %u" % self._locator.getLineNumber())
                print(self.current_bucket)
                print(e)
                raise
            self.buckets[self.current_bucket] = Bucket()
            self.save_title = False
        elif self.save_frozen:
            if self.current_frozen_flag in [1, '1', 'True', 'true']:
                 self.buckets[self.current_bucket].frozen = True
            self.current_frozen_flag = ''
            self.save_frozen = False
        elif self.peer_nesting == 2 and name == 's:key':
            if self.current_peer_field == 'bucket_flags':
                self.current_peer_flags.primary = (self.current_peer_field_value == '0xffffffffffffffff')
            elif self.current_peer_field == 'search_state':
                self.current_peer_flags.searchable = self.current_peer_field_value == 'Searchable'
            # Nesting level goes down in either case.
            self.peer_nesting -= 1
        elif self.peer_nesting == 1 and name == 's:key':
            self.buckets[self.current_bucket].peer_flags[self.current_guid] = self.current_peer_flags
            self.peer_nesting -= 1
        elif self.in_peers and self.peer_nesting == 0 and name == 's:key':
            self.in_peers = False
            
    def characters(self, content):
        if self.save_title:
            self.current_bucket += content.encode('ascii').strip()
        elif self.save_frozen:
            self.current_frozen_flag += content.encode('ascii').strip()
        if self.peer_nesting > 0:
            s = content.encode('ascii').strip()
            if s:
                self.current_peer_field_value += s
