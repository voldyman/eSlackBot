from launchpadlib.launchpad import Launchpad
from datetime import datetime
from functools import reduce
import requests
from time import sleep
import config

def compose(*func):
    '''
    Compose Function to reduce number of iteration on a list
    '''
    def compose2(f, g):
        return lambda x: f(g(x))
    return reduce(compose2, func)

class MergeProposal:
    def __init__(self, merge_proposal):
        self.mp = merge_proposal
        
        self.requester = self.mp.registrant_link
        self.desc      = self.mp.description
        self.link      = self.mp.web_link

    def get_summary(self):
        if self.desc is None or self.link is None:
            return None

        summary = "New Merge Proposal\n"
        summary += self.desc + "\n"
        summary += self.link + "\n"
        summary += '---------------------\n\n'
        
        return summary

class LaunchpadFetcher:
    def __init__(self, consumer):
        lp = Launchpad.login_anonymously(config.bot_name, 'production', config.cache_dir)
        
        self.elementary_prj = lp.projects[config.project_name]
        self.last_checked = datetime(2014 ,4, 4, 4)

        self.consumer = consumer

        self.funcs = compose(self.send_to_consumer, self.transform)
        
    def fetch_merge_requests(self):
        merge_requests = self.elementary_prj.getMergeProposals(status='Needs review')

        # filter out the requests that we don't need
        merge_requests = filter(self.remove_old, merge_requests)

        # map multiple functions over the collections
        mp_objs = map(self.funcs, merge_requests)
        
    def remove_old(self, mr):
        mr_date_created = mr.date_created.replace(tzinfo=None)
        # only use those proposals that are new
        if mr_date_created > self.last_checked:
            return True
        return False
        
    def send_to_consumer(self, mp_obj):
        # send to the poster coroutine
        self.consumer.send(mp_obj.get_summary())

    def transform(self, merge_proposal):
        return MergeProposal(merge_proposal)

    def update_last_checked(self):
        self.last_checked = datetime.utcnow()

def sender():
    '''
    Function to post the merge request on to slacker
    '''
    
    URL = "https://slack.com/api/chat.postMessage"
    while True:
        txt = yield

        data = {'token':config.slack_token,
                'channel':'#merge_proposals',
                'username':config.slack_bot_name,
                'icon-url':config.slack_bot_icon_url,
                'text': txt}
        requests.post(URL, params=data)
        
if __name__ == '__main__':
    consumer = sender()
    consumer.send(None)
    
    lpf = LaunchpadFetcher(consumer)
    while True:
        lpf.fetch_merge_requests()
        lpf.update_last_checked()

        sleep(config.sleep_time)
