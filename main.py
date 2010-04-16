#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

from google.appengine.api import xmpp
from google.appengine.ext.webapp import xmpp_handlers

from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
import oauth
from google.appengine.ext import db

from django.utils import simplejson
from google.appengine.api import urlfetch
_DEBUG = True

class UserAuth(db.Model):
    email = db.StringProperty()
    token = db.StringProperty()
    secret = db.StringProperty()
    created_at = db.DateTimeProperty(auto_now_add=True) 

class BaseRequestHandler(webapp.RequestHandler):
    """Supplies a common template generation function.
    
    When you call generate(), we augment the template variables supplied with
    the current user in the 'user' variable and the current webapp request
    in the 'request' variable.
    """
    def generate(self, template_name, template_values={}):
        values = {
          'request': self.request,
          'user': users.get_current_user(),
          'login_url': users.create_login_url(self.request.uri),
          'logout_url': users.create_logout_url(self.request.uri),
          'application_name': 'AirTweet',
        }
        values.update(template_values)
        directory = os.path.dirname(__file__)
        path = os.path.join(directory, os.path.join('templates', template_name))
        self.response.out.write(template.render(path, values, debug=_DEBUG))
    
    def head(self, *args):
        pass
    
    def get(self, *args):
        pass
      
    def post(self, *args):
        pass
  
class MainHandler(BaseRequestHandler):
    def has_token(self):
        """if the current has auth token"""
        user = users.get_current_user()
        if user and len(UserAuth.gql("WHERE email = :email",email = user.email()).fetch(1)) != 0:
            return True
        else:
            return False
        pass
            
    def get(self):
        user = users.get_current_user()
        self.generate('index.html', {'has_token':self.has_token()})

class AboutHandler(BaseRequestHandler):
    """docstring for HelpHandler"""
    def get(self):
        """docstring for get"""
        self.generate('about.html', {})
                
class HelpHandler(BaseRequestHandler):
    """docstring for HelpHandler"""
    def get(self):
        """docstring for get"""
        self.generate('help.html', {})
        

class ConnectHandler(webapp.RequestHandler):
    def get(self, action=""):
        
        application_key = "6qkQ9J3esg5oT7eFGHwc5g" 
        application_secret = "Pjp3kZQVq48eAPz6vqvWY7WlDa5cKmwzty5lcHiPbo"  
        callback_url = "%s/verify" % self.request.host_url
        
        client = oauth.TwitterClient(application_key, application_secret, 
            callback_url)
        
        if action == "connect":
            return self.redirect(client.get_authorization_url())
        
        if action == "verify":
            auth_token = self.request.get("oauth_token")
            auth_verifier = self.request.get("oauth_verifier")
            user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
            # return self.response.out.write(user_info)
            user_auth = UserAuth()
            user_auth.email = users.get_current_user().email()
            user_auth.token = user_info['token']
            user_auth.secret = user_info['secret']
            user_auth.put()
            return self.redirect('timeline')
        
        if action == "timeline":
            timeline_url = "http://twitter.com/statuses/user_timeline.json"
            user_auth = UserAuth.gql("WHERE email = :email",email = users.get_current_user().email()).fetch(1)[0]
            result = client.make_request(url=timeline_url, token=user_auth.token, 
            secret=user_auth.secret)
            tweets = ""
            for tweet in simplejson.loads(result.content):
                tweets += (tweet['user']['screen_name'] + ' :   ' + tweet['text'] + "<br/>")
                
            return self.response.out.write(tweets)
    
        self.redirect('/')
            
class XMPPHandler(xmpp_handlers.CommandHandler):
    application_key = "6qkQ9J3esg5oT7eFGHwc5g" 
    application_secret = "Pjp3kZQVq48eAPz6vqvWY7WlDa5cKmwzty5lcHiPbo"  
    callback_url = "%s/verify" % "http://airtweet.appspot.com"
    client = oauth.TwitterClient(application_key, application_secret, 
        callback_url)
    def unhandled_command(self, message = None):
        message.reply("unknow command")

    def help_command(self, message = None):
        help_msg = ""
        help_msg += "/home show your and your friend's tweets.\n"
        help_msg += "/user show your tweets. \n"
        help_msg += "/update update your status with a tweet. \n"
        help_msg += "/search  search the tweets with a keyword. \n\n"
        help_msg += "Visit airtweet.appspot.com to read the help. \n"
        help_msg += "Have any questions mail to yanguango@gmail.com."
        message.reply(help_msg)
    
    def user_command(self, message = None):
        """docstring for reply"""
        user_timeline_url = "http://twitter.com/statuses/user_timeline.json"
        email = message.sender.split('/')[0]
        user_auth = UserAuth.gql("WHERE email = :email",email = email).fetch(1)[0]
        
        
        result = XMPPHandler.client.make_request(url=user_timeline_url, token=user_auth.token, 
            secret=user_auth.secret)
        tweets = ""
        for tweet in simplejson.loads(result.content):
            tweets += (tweet['user']['screen_name'] + ' :   ' + tweet['text'] + "\n\n")
        message.reply(tweets)
            
    def home_command(self, message = None):
        """docstring for home_command"""
        home_timeline_url = "http://twitter.com/statuses/home_timeline.json"
        email = message.sender.split('/')[0]
        user_auth = UserAuth.gql("WHERE email = :email",email = email).fetch(1)[0]
        result = XMPPHandler.client.make_request(url=home_timeline_url, token=user_auth.token, 
            secret=user_auth.secret)
        tweets = ""
        for tweet in simplejson.loads(result.content):
            tweets += (tweet['user']['screen_name'] + ' :   ' + tweet['text'] + "\n\n")
        message.reply(tweets)
        
    def update_command(self, message = None):
        """docstring for update_command"""
        update_url = "http://api.twitter.com/version/statuses/update.json"
        email = message.sender.split('/')[0]
        user_auth = UserAuth.gql("WHERE email = :email",email = email).fetch(1)[0]
        XMPPHandler.client.make_request(url=update_url, token=user_auth.token, 
            secret=user_auth.secret,additional_params={'status':message.arg},method=urlfetch.POST)
        message.reply("update successfully")
            
    def search_command(self, message=None):
		search_url = "http://search.twitter.com/search.json?q=%s" % message.arg
		response = urlfetch.fetch(search_url)
		reply_msg = ""
		res_obj = simplejson.loads(response.content)
		
		for tweet_obj in res_obj['results']:
			tweet_txt = tweet_obj['text']
			reply_msg += tweet_txt + "\n\n"
		
		
		message.reply(reply_msg)


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/help', HelpHandler),
                                        ('/about', AboutHandler),
										('/_ah/xmpp/message/chat/',XMPPHandler),
										('/(.*)', ConnectHandler)],
                                       debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
