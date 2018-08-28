import requests
import json
import six
import sys
import platform
from .exceptions import SlackClientError
from .version import __version__


class SlackRequest(object):
    def __init__(self, proxies=None, domain = None, access_token = None, refresh_token = None, client_id = None, client_secret = None, refresh_callback = None):
        # Construct the user-agent header with the package info, Python version and OS version.
        self.default_user_agent = {
            # __name__ returns 'slackclient.slackrequest', we only want 'slackclient'
            "client": "{0}/{1}".format(__name__.split('.')[0], __version__),
            "python": "Python/{v.major}.{v.minor}.{v.micro}".format(v=sys.version_info),
            "system": "{0}/{1}".format(platform.system(), platform.release())
        }

        # HTTP configs
        self.custom_user_agent = None
        self.proxies = proxies
        self.domain = domain

        # Slack application configs
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_callback = refresh_callback
        self.token = access_token
        self.token_expires_at = None

    def get_user_agent(self):
        # Check for custom user-agent and append if found
        if self.custom_user_agent:
            custom_ua_list = ["/".join(client_info) for client_info in self.custom_user_agent]
            custom_ua_string = " ".join(custom_ua_list)
            self.default_user_agent['custom'] = custom_ua_string

        # Concatenate and format the user-agent string to be passed into request headers
        ua_string = []
        for key, val in self.default_user_agent.items():
            ua_string.append(val)

        user_agent_string = " ".join(ua_string)
        return user_agent_string

    def append_user_agent(self, name, version):
        if self.custom_user_agent:
            self.custom_user_agent.append([name.replace("/", ":"), version.replace("/", ":")])
        else:
            self.custom_user_agent = [[name, version]]

    def do(self, token, request="?", post_data=None, domain="slack.com", timeout=None):
        """
        Perform a POST request to the Slack Web API

        Args:
            token (str): your authentication token
            request (str): the method to call from the Slack API. For example: 'channels.list'
            timeout (float): stop waiting for a response after a given number of seconds
            post_data (dict): key/value arguments to pass for the request. For example:
                {'channel': 'CABC12345'}
            domain (str): if for some reason you want to send your request to something other
                than slack.com
        """

        # if token is None and "refresh_token" in post_data:
        #     token = post_data['refresh_token']

        # Override token header if `token` is passed in post_data
        if post_data is not None and "token" in post_data:
            token = post_data['token']

        # Set user-agent and auth headers
        headers = {
            'user-agent': self.get_user_agent(),
            'Authorization': 'Bearer {}'.format(token)
        }

        # Pull file out so it isn't JSON encoded like normal fields.
        # Only do this for requests that are UPLOADING files; downloading files
        # use the 'file' argument to point to a File ID.
        post_data = post_data or {}

        # Move singular file objects into `files`
        upload_requests = ['files.upload']

        # Move file content into requests' `files` param
        files = None
        if request in upload_requests:
            files = {'file': post_data.pop('file')} if 'file' in post_data else None

        # Check for plural fields and convert them to comma-separated strings if needed
        for field in {'channels', 'users', 'types'} & set(post_data.keys()):
            if isinstance(post_data[field], list):
                post_data[field] = ",".join(post_data[field])

        # Convert any params which are list-like to JSON strings
        # Example: `attachments` is a dict, and needs to be passed as JSON
        for k, v in six.iteritems(post_data):
            if isinstance(v, (list, dict)):
                post_data[k] = json.dumps(v)

        # Submit the request
        res = requests.post(
            'https://{0}/api/{1}'.format(domain, request),
            headers=headers,
            data=post_data,
            files=files,
            timeout=timeout,
            proxies=self.proxies
        )

        refresh_data = json.loads(res.content)
        if (not refresh_data['ok']):
            # raise SlackClientError(refresh_data['error'])
            self.request_opts['refresh_callback'](refresh_data)
        else:
            return res
