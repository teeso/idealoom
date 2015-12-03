from urlparse import urljoin, urlparse
import urllib

from ..models import Discussion


URL_DISCRIMINANTS = {
    'SOURCE': 'source',
    'NEXT': 'next_view'
}

SOURCE_DISCRIMINANTS = {
    'NOTIFICATION': 'notification',
    'SHARE': 'share'
}

ATTACHMENT_PURPOSES = {
    'EMBED_ATTACHMENT': 'EMBED_ATTACHMENT'
}


class FrontendUrls():
    def __init__(self, discussion):
        assert isinstance(discussion, Discussion)
        self.discussion = discussion

    # Note:  This should match with assembl/static/js/app/router.js
    # Used by home_view, these routes will all give backbone's interface
    frontend_routes = {
        'edition': '/edition',
        'partners': '/partners',
        'settings': '/settings',
        'about': '/about',
        'admin_discussion_preferences': '/discussion_preferences',
        'notifications': '/notifications',
        'user_notifications': '/user/notifications',
        'profile': '/user/profile',
        'account': '/user/account',
        'user_discussion_preferences': '/user/discussion_preferences',
        'sentrytest': '/sentrytest',
        'groupSpec': '/G*remainder',
        'purl_posts': '/posts*remainder',
        'purl_idea': '/idea*remainder',
        'purl_user': '/profile*remainder',
    }

    @classmethod
    def register_frontend_routes(cls, config):
        from assembl.views.backbone.views import home_view
        for name, route in cls.frontend_routes.iteritems():
            config.add_route(name, route)
            config.add_view(
                home_view, route_name=name, request_method='GET',
                http_cache=60)

    # used for route 'purl_posts': '/posts*remainder'
    @staticmethod
    def getRequestedPostId(request):
        if 'remainder' in request.matchdict:
            return '/'.join(i for i in request.matchdict['remainder'])
        return None

    # used for route 'purl_idea': '/idea*remainder'
    @staticmethod
    def getRequestedIdeaId(request):
        if 'remainder' in request.matchdict:
            return '/'.join(i for i in request.matchdict['remainder'])
        return None

    def getDiscussionLogoUrl(self):
        return urljoin(
            self.discussion.get_base_url(), '/static/img/assembl.png')

    def get_discussion_url(self):
        from pyramid.request import Request
        #req = Request.blank('/', base_url=self.discussion.get_base_url())
        #Celery didn't like this.  To revisit once we have virtual hosts
        #return req.route_url('home', discussion_slug=self.discussion.slug)
        return urljoin(self.discussion.get_base_url(), self.discussion.slug)

    def getUserNotificationSubscriptionsConfigurationUrl(self):
        return self.get_discussion_url() + '/user/notifications'

    def getUserNotificationSubscriptionUnsubscribeUrl(self, subscription):
        """ TODO:  Give an actual subscription URL """
        return self.getUserNotificationSubscriptionsConfigurationUrl()

    def get_relative_post_url(self, post):
        return '/posts/' + urllib.quote(post.uri(), '')

    def get_post_url(self, post):
        return self.get_discussion_url() + self.get_relative_post_url(post)

    def get_relative_idea_url(self, idea):
        return '/idea/' + urllib.quote(idea.original_uri, '')

    def get_idea_url(self, idea):
        return self.get_discussion_url() + self.get_relative_idea_url(idea)

    def get_discussion_edition_url(self):
        return self.get_discussion_url() + '/edition'

    def append_query_string(self, url, **kwargs):
        if not url:
            return ''
        if url[-1] is '/':
            url = url[:-1]
        url_base = url + '?'
        f = lambda k, v: "%s=%s" % (k, v)
        qs = [f(k, v) for k, v in kwargs.iteritems() if k]
        return url_base + ('&'.join(qs)) if kwargs else ''

    def get_agentprofile_avatar_url(self, profile, pixelSize):
        return urljoin(
            self.discussion.get_base_url(), profile.external_avatar_url()+str(pixelSize))
