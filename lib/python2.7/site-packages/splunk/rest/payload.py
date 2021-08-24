import json

JSON = """
{
   "links":{
   },
   "generator":{
   },
   "entry":[
      {
         "links":{
         },
         "acl":{
            "perms":{
               "read":[],
               "write":[]
            }
         },
         "fields":{
            "required":[],
            "optional":[],
            "wildcard":[]
         },
         "content":{
         }
      }
   ],
   "messages":[]
}
"""

def scaffold():
    return json.loads(JSON)
