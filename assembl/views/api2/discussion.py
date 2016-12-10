import re
import base64
from cStringIO import StringIO
from os import urandom
from os.path import join, dirname
from collections import defaultdict
import random
from datetime import timedelta

from sqlalchemy import (
    Column,
    Integer,
    UnicodeText,
    DateTime,
    Text,
    String,
    Boolean,
    event,
    ForeignKey,
    func,
    distinct
)


import simplejson as json
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPOk, HTTPBadRequest, HTTPUnauthorized, HTTPNotAcceptable, HTTPFound,
    HTTPServerError)
from pyramid_dogpile_cache import get_region
from pyramid.security import authenticated_userid, Everyone
from pyramid.renderers import JSONP_VALID_CALLBACK
from pyramid.settings import asbool
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
import requests

from assembl.lib.config import get_config
from assembl.lib.parsedatetime import parse_datetime
from assembl.lib.sqla import ObjectNotUniqueError
from assembl.lib.json import DateJSONEncoder
from assembl.auth import (
    P_READ, P_READ_PUBLIC_CIF, P_ADMIN_DISC, P_DISC_STATS, P_SYSADMIN,
    R_ADMINISTRATOR)
from assembl.auth.password import verify_data_token, data_token, Validity
from assembl.auth.util import get_permissions
from assembl.models import (Discussion, Permission)
from assembl.models.auth import create_default_permissions
from ..traversal import InstanceContext, ClassContext
from . import (JSON_HEADER, FORM_HEADER, CreationResponse)
from sqlalchemy.orm.util import aliased
from assembl.semantic.obfuscation import AESObfuscator
from ..api.discussion import etalab_discussions, API_ETALAB_DISCUSSIONS_PREFIX


@view_config(context=InstanceContext, request_method='GET',
             ctx_instance_class=Discussion, permission=P_READ,
             accept="application/json", name="settings",
             renderer='json')
def discussion_settings_get(request):
    return request.context._instance.settings_json


@view_config(context=InstanceContext, request_method='PATCH',
             ctx_instance_class=Discussion, permission=P_ADMIN_DISC,
             header=JSON_HEADER, name="settings")
@view_config(context=InstanceContext, request_method='PUT',
             ctx_instance_class=Discussion, permission=P_ADMIN_DISC,
             header=JSON_HEADER, name="settings")
def discussion_settings_put(request):
    request.context._instance.settings_json = request.json_body
    return HTTPOk()

dogpile_fname = join(
    dirname(dirname(dirname(dirname(__file__)))),
    get_config().get('dogpile_cache.arguments.filename'))

discussion_jsonld_cache = get_region(
    'discussion_jsonld', **{"arguments.filename": dogpile_fname})
userprivate_jsonld_cache = get_region(
    'userprivate_jsonld', **{"arguments.filename": dogpile_fname})


@discussion_jsonld_cache.cache_on_arguments()
def discussion_jsonld(discussion_id):
    d = Discussion.get(discussion_id)
    return json.dumps(d.get_public_graphs_cif())


@userprivate_jsonld_cache.cache_on_arguments()
def userprivate_jsonld(discussion_id):
    d = Discussion.get(discussion_id)
    return json.dumps(d.get_private_graphs_cif())


def read_user_token(request):
    salt = None
    user_id = authenticated_userid(request) or Everyone
    discussion_id = request.context.get_discussion_id()
    permissions = get_permissions(user_id, discussion_id)
    if P_READ in permissions:
        permissions.append(P_READ_PUBLIC_CIF)

    if 'token' in request.GET:
        token = request.GET['token'].encode('ascii')
        data, valid = verify_data_token(token, max_age=timedelta(hours=1))
        if valid != Validity.VALID:
            raise HTTPBadRequest("Invalid token")
        try:
            data, salt = data.split('.', 1)
            salt = base64.urlsafe_b64decode(salt)
            data = [int(i) for i in data.split(',')]
            t_user_id, t_discussion_id = data[:2]
            req_permissions = data[2:]
            if len(req_permissions):
                req_permissions = [x for (x,) in Permission.default_db.query(
                    Permission.name).filter(
                    Permission.id.in_(req_permissions)).all()]
        except (ValueError, IndexError):
            raise HTTPBadRequest("Invalid token")
        if discussion_id is not None and t_discussion_id != discussion_id:
            raise HTTPUnauthorized("Token for another discussion")
        if user_id == Everyone:
            permissions = get_permissions(t_user_id, discussion_id)
            if P_READ in permissions:
                permissions.append(P_READ_PUBLIC_CIF)
        elif t_user_id != user_id:
            raise HTTPUnauthorized("Token for another user")
        user_id = t_user_id
        permissions = set(permissions).intersection(set(req_permissions))
    return user_id, permissions, salt


def handle_jsonp(callback_fn, json):
    # TODO: Use an augmented JSONP renderer with ld content-type
    if not JSONP_VALID_CALLBACK.match(callback_fn):
        raise HTTPBadRequest("invalid callback name")
    return "/**/{0}({1});".format(callback_fn.encode('ascii'), json)


def permission_token(
        user_id, discussion_id, req_permissions, random_str=None):
    random_str = random_str or urandom(8)
    if isinstance(req_permissions, list):
        req_permissions = set(req_permissions)
    else:
        req_permissions = set((req_permissions,))
    permissions = get_permissions(user_id, discussion_id)
    if not req_permissions:
        req_permissions = permissions
    elif P_SYSADMIN not in permissions:
        req_permissions = req_permissions.intersection(set(permissions))
    req_permissions = list(req_permissions)
    user_id = 0 if user_id == Everyone else user_id
    data = [str(user_id), str(discussion_id)]
    data.extend([str(x) for (x,) in Permission.default_db.query(
            Permission.id).filter(Permission.name.in_(req_permissions)).all()])
    data = ','.join(data) + '.' + base64.urlsafe_b64encode(random_str)
    return data_token(data)


@view_config(context=InstanceContext, name="perm_token",
             ctx_instance_class=Discussion, request_method='GET',
             accept="application/ld+json", renderer="json")
def get_token(request):
    user_id = authenticated_userid(request)
    if not user_id:
        raise HTTPUnauthorized()
    discussion_id = request.context.get_discussion_id()
    permission_sets = request.GET.getall('permissions')
    if permission_sets:
        permission_sets = [s.split(',') for s in permission_sets]
        for permissions in permission_sets:
            if P_READ in permissions:
                permissions.append(P_READ_PUBLIC_CIF)
        permission_sets = [sorted(set(permissions))
                           for permissions in permission_sets]
    else:
        permission_sets = [[P_READ, P_READ_PUBLIC_CIF]]
    random_str = urandom(8)
    data = {','.join(permissions): permission_token(
        user_id, discussion_id, permissions, random_str)
        for permissions in permission_sets}
    user_ids = request.GET.getall("user_id")
    if user_ids:
        obfuscator = AESObfuscator(random_str)
        user_ids = "\n".join(user_ids)
        data["user_ids"] = obfuscator.obfuscate(user_ids).split("\n")
    return data


@view_config(context=InstanceContext, name="jsonld",
             ctx_instance_class=Discussion, request_method='GET',
             accept="application/ld+json")
@view_config(context=InstanceContext,
             ctx_instance_class=Discussion, request_method='GET',
             accept="application/ld+json")
def discussion_instance_view_jsonld(request):
    discussion = request.context._instance
    user_id, permissions, salt = read_user_token(request)
    if not (P_READ in permissions or P_READ_PUBLIC_CIF in permissions):
        raise HTTPUnauthorized()
    if not salt and P_ADMIN_DISC not in permissions:
        salt = base64.urlsafe_b64encode(urandom(6))

    jdata = discussion_jsonld(discussion.id)
    if salt:
        obfuscator = AESObfuscator(salt)
        jdata = obfuscator.obfuscate(jdata)
    # TODO: Add age
    if "callback" in request.GET:
        jdata = handle_jsonp(request.GET['callback'], jdata)
        content_type = "application/json-p"
    else:
        content_type = "application/ld+json"
    return Response(body=jdata, content_type=content_type)


@view_config(context=InstanceContext, name="private_jsonld",
             ctx_instance_class=Discussion, request_method='GET',
             accept="application/ld+json")
def user_private_view_jsonld(request):
    if request.scheme == "http" and asbool(request.registry.settings.get(
            'accept_secure_connection', False)):
        return HTTPFound("https://" + request.host + request.path_qs)
    discussion_id = request.context.get_discussion_id()
    user_id, permissions, salt = read_user_token(request)
    if P_READ not in permissions:
        raise HTTPUnauthorized()
    if not salt and P_ADMIN_DISC not in permissions:
        salt = base64.urlsafe_b64encode(urandom(6))

    jdata = userprivate_jsonld(discussion_id)
    if salt:
        obfuscator = AESObfuscator(salt)
        jdata = obfuscator.obfuscate(jdata)
    if "callback" in request.GET:
        jdata = handle_jsonp(request.GET['callback'], jdata)
        content_type = "application/json-p"
    else:
        content_type = "application/ld+json"
    return Response(body=jdata, content_type=content_type)


JSON_MIMETYPE = 'application/json'
CSV_MIMETYPE = 'text/csv'
XSL_MIMETYPE = 'application/vnd.ms-excel'
XSLX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

stats_formats = {
    'json': JSON_MIMETYPE,
    'csv': CSV_MIMETYPE,
    'xlsx': XSLX_MIMETYPE,
    # 'xls': XSL_MIMETYPE,
}


def get_format(request, stats_formats):
    format = request.GET.get('format', None)
    if format:
        format = stats_formats.get(format, None)
        if not format:
            raise HTTPBadRequest("format: use one of "+", ".join(stats_formats.keys()))
    else:
        # Trick: application/json is first in sorted order, so we get json default.
        format = request.accept.best_match(sorted(stats_formats.values()))
        if not format:
            raise HTTPNotAcceptable("Use one of "+", ".join(stats_formats.values()))
    return format



@view_config(context=InstanceContext, name="time_series_analytics",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_time_series_analytics(request):
    import isodate
    from datetime import datetime
    start = request.GET.get("start", None)
    end = request.GET.get("end", None)
    interval = request.GET.get("interval", None)
    discussion = request.context._instance
    user_id = authenticated_userid(request) or Everyone
    try:
        if start:
            start = parse_datetime(start)
        if end:
            end = parse_datetime(end)
        if interval:
            interval = isodate.parse_duration(interval)
    except isodate.ISO8601Error as e:
        raise HTTPBadRequest(e)
    if interval and not start:
        raise HTTPBadRequest("You cannot define an interval and no start")
    if interval and not end:
        end = datetime.now()
    format = get_format(request, stats_formats)
    results = []

    from sqlalchemy import Table, MetaData, and_, or_, case, cast, Float
    from sqlalchemy.exc import ProgrammingError
    from sqlalchemy.orm import with_polymorphic
    import pprint
    import transaction
    with transaction.manager:
        metadata = MetaData(discussion.db.get_bind())  # make sure we are using the same connexion

        intervals_table = Table('temp_table_intervals_' + str(user_id), metadata,
            Column('interval_id', Integer, primary_key=True),
            Column('interval_start', DateTime, nullable=False),
            Column('interval_end', DateTime, nullable=False),
            prefixes=None if discussion.using_virtuoso else ['TEMPORARY']
        )
        try:
            intervals_table.drop()  # In case there is a leftover from a previous crash
        except ProgrammingError:
            pass
        intervals_table.create()
        interval_start = start
        intervals = []
        if interval:
            while interval_start < end:
                interval_end = min(interval_start + interval, end)
                intervals.append({'interval_start': interval_start, 'interval_end': interval_end})
                interval_start = interval_start + interval
            #pprint.pprint(intervals)
            discussion.db.execute(intervals_table.insert(), intervals)
        else:
            raise HTTPBadRequest("Please specify an interval")

        from assembl.models import (
            Post, AgentProfile, AgentStatusInDiscussion, ViewPost, Idea,
            AbstractIdeaVote, Action, ActionOnPost, ActionOnIdea, Content)

        # The posters
        post_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(Post.id)).label('count_posts'),
            func.count(distinct(Post.creator_id)).label('count_post_authors'),
            # func.DB.DBA.BAG_AGG(Post.creator_id).label('post_authors'),
            # func.DB.DBA.BAG_AGG(Post.id).label('post_ids'),
            )
        post_subquery = post_subquery.outerjoin(Post, and_(Post.creation_date >= intervals_table.c.interval_start, Post.creation_date < intervals_table.c.interval_end, Post.discussion_id == discussion.id))
        post_subquery = post_subquery.group_by(intervals_table.c.interval_id)
        post_subquery = post_subquery.subquery()

        # The cumulative posters
        cumulative_posts_aliased = aliased(Post)
        cumulative_posts_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(cumulative_posts_aliased.id)).label('count_cumulative_posts'),
            func.count(distinct(cumulative_posts_aliased.creator_id)).label('count_cumulative_post_authors')
            # func.DB.DBA.BAG_AGG(cumulative_posts_aliased.id).label('cumulative_post_ids')
            )
        cumulative_posts_subquery = cumulative_posts_subquery.outerjoin(cumulative_posts_aliased, and_(cumulative_posts_aliased.creation_date < intervals_table.c.interval_end, cumulative_posts_aliased.discussion_id == discussion.id))
        cumulative_posts_subquery = cumulative_posts_subquery.group_by(intervals_table.c.interval_id)
        cumulative_posts_subquery = cumulative_posts_subquery.subquery()

        # The post viewers
        postViewers = aliased(ViewPost)
        viewedPosts = aliased(Post)
        post_viewers_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(postViewers.actor_id)).label('UNRELIABLE_count_post_viewers')
            )
        post_viewers_subquery = post_viewers_subquery.outerjoin(postViewers, and_(postViewers.creation_date >= intervals_table.c.interval_start, postViewers.creation_date < intervals_table.c.interval_end)).\
                        join(viewedPosts, and_(postViewers.post_id == viewedPosts.id, viewedPosts.discussion_id == discussion.id))
        post_viewers_subquery = post_viewers_subquery.group_by(intervals_table.c.interval_id)
        post_viewers_subquery = post_viewers_subquery.subquery()

        # The visitors
        firstTimeVisitorAgent = aliased(AgentStatusInDiscussion)
        visitors_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(firstTimeVisitorAgent.id).label('count_first_time_logged_in_visitors'),
            # func.DB.DBA.BAG_AGG(firstTimeVisitorAgent.id).label('first_time_visitors')
            )
        visitors_subquery = visitors_subquery.outerjoin(firstTimeVisitorAgent, and_(firstTimeVisitorAgent.first_visit >= intervals_table.c.interval_start, firstTimeVisitorAgent.first_visit < intervals_table.c.interval_end, firstTimeVisitorAgent.discussion_id == discussion.id))
        visitors_subquery = visitors_subquery.group_by(intervals_table.c.interval_id)
        visitors_subquery = visitors_subquery.subquery()

        # The cumulative visitors
        cumulativeVisitorAgent = aliased(AgentStatusInDiscussion)
        cumulative_visitors_query = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(cumulativeVisitorAgent.id)).label('count_cumulative_logged_in_visitors'),
            # func.DB.DBA.BAG_AGG(cumulativeVisitorAgent.id).label('first_time_visitors')
            )
        cumulative_visitors_query = cumulative_visitors_query.outerjoin(cumulativeVisitorAgent, and_(cumulativeVisitorAgent.first_visit < intervals_table.c.interval_end, cumulativeVisitorAgent.discussion_id == discussion.id))
        cumulative_visitors_query = cumulative_visitors_query.group_by(intervals_table.c.interval_id)
        cumulative_visitors_subquery = cumulative_visitors_query.subquery()
        # query = cumulative_visitors_query

        # The members (can go up and down...)  Assumes that first_subscribed is available
        memberAgentStatus = aliased(AgentStatusInDiscussion)
        members_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(memberAgentStatus.id).label('count_approximate_members')
            )
        members_subquery = members_subquery.outerjoin(memberAgentStatus, ((memberAgentStatus.last_unsubscribed >= intervals_table.c.interval_end) | (memberAgentStatus.last_unsubscribed.is_(None))) & ((memberAgentStatus.first_subscribed < intervals_table.c.interval_end) | (memberAgentStatus.first_subscribed.is_(None))) & (memberAgentStatus.discussion_id==discussion.id))
        members_subquery = members_subquery.group_by(intervals_table.c.interval_id)
        members_subquery = members_subquery.subquery()

        subscribersAgentStatus = aliased(AgentStatusInDiscussion)
        subscribers_query = discussion.db.query(intervals_table.c.interval_id,
                                                func.sum(
                                                    case([
                                                          (subscribersAgentStatus.last_visit == None, 0),
                                                          (and_(subscribersAgentStatus.last_visit < intervals_table.c.interval_end, subscribersAgentStatus.last_visit >= intervals_table.c.interval_start), 1)
                                                          ], else_=0)
                                                         ).label('retention_count_last_visit_in_period'),
                                                func.sum(
                                                    case([
                                                          (subscribersAgentStatus.first_visit == None, 0),
                                                          (and_(subscribersAgentStatus.first_visit < intervals_table.c.interval_end, subscribersAgentStatus.first_visit >= intervals_table.c.interval_start), 1)
                                                          ], else_=0)
                                                         ).label('recruitment_count_first_visit_in_period'),
                                                func.sum(
                                                    case([
                                                          (subscribersAgentStatus.first_subscribed == None, 0),
                                                          (and_(subscribersAgentStatus.first_subscribed < intervals_table.c.interval_end, subscribersAgentStatus.first_subscribed >= intervals_table.c.interval_start), 1)
                                                          ], else_=0)
                                                         ).label('UNRELIABLE_recruitment_count_first_subscribed_in_period'),
                                                func.sum(
                                                    case([
                                                          (subscribersAgentStatus.last_unsubscribed == None, 0),
                                                          (and_(subscribersAgentStatus.last_unsubscribed < intervals_table.c.interval_end, subscribersAgentStatus.last_unsubscribed >= intervals_table.c.interval_start), 1)
                                                          ], else_=0)
                                                         ).label('UNRELIABLE_retention_count_first_subscribed_in_period'),
                                            )
        subscribers_query = subscribers_query.outerjoin(subscribersAgentStatus, subscribersAgentStatus.discussion_id==discussion.id)
        subscribers_query = subscribers_query.group_by(intervals_table.c.interval_id)
        subscribers_subquery = subscribers_query.subquery()
        #query = subscribers_query

        # The votes
        votes_aliased = aliased(AbstractIdeaVote)
        votes_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(votes_aliased.id)).label('count_votes'),
            func.count(distinct(votes_aliased.voter_id)).label('count_voters'),
            )
        votes_subquery = votes_subquery.outerjoin(Idea, Idea.discussion_id == discussion.id)
        votes_subquery = votes_subquery.outerjoin(votes_aliased, and_(votes_aliased.vote_date >= intervals_table.c.interval_start, votes_aliased.vote_date < intervals_table.c.interval_end, votes_aliased.idea_id == Idea.id))
        votes_subquery = votes_subquery.group_by(intervals_table.c.interval_id)
        votes_subquery = votes_subquery.subquery()

        # The cumulative posters
        cumulative_votes_aliased = aliased(AbstractIdeaVote)
        cumulative_votes_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(cumulative_votes_aliased.id).label('count_cumulative_votes'),
            func.count(distinct(cumulative_votes_aliased.voter_id)).label('count_cumulative_voters')
            )
        cumulative_votes_subquery = cumulative_votes_subquery.outerjoin(Idea, Idea.discussion_id == discussion.id)
        cumulative_votes_subquery = cumulative_votes_subquery.outerjoin(cumulative_votes_aliased, and_(cumulative_votes_aliased.vote_date < intervals_table.c.interval_end, cumulative_votes_aliased.idea_id == Idea.id))
        cumulative_votes_subquery = cumulative_votes_subquery.group_by(intervals_table.c.interval_id)
        cumulative_votes_subquery = cumulative_votes_subquery.subquery()

        content = with_polymorphic(
                    Content, [], Content.__table__,
                    aliased=False, flat=True)

        # The actions
        actions_on_post = discussion.db.query(
            intervals_table.c.interval_id.label('interval_id'), ActionOnPost.actor_id.label('actor_id'))
        actions_on_post = actions_on_post.join(content, content.discussion_id == discussion.id)
        actions_on_post = actions_on_post.join(ActionOnPost, and_(
            ActionOnPost.post_id == content.id,
            ActionOnPost.creation_date >= intervals_table.c.interval_start,
            ActionOnPost.creation_date < intervals_table.c.interval_end
            ))

        actions_on_idea = discussion.db.query(
            intervals_table.c.interval_id.label('interval_id'), ActionOnIdea.actor_id.label('actor_id'))
        actions_on_idea = actions_on_idea.join(Idea, Idea.discussion_id == discussion.id)
        actions_on_idea = actions_on_idea.join(ActionOnIdea, and_(
            ActionOnIdea.idea_id == Idea.id,
            ActionOnIdea.creation_date >= intervals_table.c.interval_start,
            ActionOnIdea.creation_date < intervals_table.c.interval_end
            ))

        actions_union_subquery = actions_on_post.union(actions_on_idea).subquery()
        actions_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(actions_union_subquery.c.actor_id)).label('count_actors')
            ).outerjoin(actions_union_subquery, actions_union_subquery.c.interval_id == intervals_table.c.interval_id
            ).group_by(intervals_table.c.interval_id).subquery()

        # The actions
        cumulative_actions_on_post = discussion.db.query(
            intervals_table.c.interval_id.label('interval_id'), ActionOnPost.actor_id.label('actor_id'))
        cumulative_actions_on_post = cumulative_actions_on_post.join(content, content.discussion_id == discussion.id)
        cumulative_actions_on_post = cumulative_actions_on_post.join(ActionOnPost, and_(
            ActionOnPost.post_id == content.id,
            ActionOnPost.creation_date < intervals_table.c.interval_end
            ))

        cumulative_actions_on_idea = discussion.db.query(
            intervals_table.c.interval_id.label('interval_id'), ActionOnIdea.actor_id.label('actor_id'))
        cumulative_actions_on_idea = cumulative_actions_on_idea.join(Idea, Idea.discussion_id == discussion.id)
        cumulative_actions_on_idea = cumulative_actions_on_idea.join(ActionOnIdea, and_(
            ActionOnIdea.idea_id == Idea.id,
            ActionOnIdea.creation_date < intervals_table.c.interval_end
            ))

        cumulative_actions_union_subquery = cumulative_actions_on_post.union(cumulative_actions_on_idea).subquery()
        cumulative_actions_subquery = discussion.db.query(intervals_table.c.interval_id,
            func.count(distinct(cumulative_actions_union_subquery.c.actor_id)).label('count_cumulative_actors')
            ).outerjoin(cumulative_actions_union_subquery, cumulative_actions_union_subquery.c.interval_id == intervals_table.c.interval_id
            ).group_by(intervals_table.c.interval_id).subquery()


        combined_query = discussion.db.query(intervals_table,
                                             post_subquery,
                                             cumulative_posts_subquery,
                                             post_viewers_subquery,
                                             visitors_subquery,
                                             cumulative_visitors_subquery,
                                             votes_subquery,
                                             cumulative_votes_subquery,
                                             members_subquery,
                                             actions_subquery,
                                             cumulative_actions_subquery,
                                             case([
                                                   (cumulative_posts_subquery.c.count_cumulative_post_authors == 0, None),
                                                   (cumulative_posts_subquery.c.count_cumulative_post_authors != 0, (cast(post_subquery.c.count_post_authors, Float) / cast(cumulative_posts_subquery.c.count_cumulative_post_authors, Float)))
                                                   ]).label('fraction_cumulative_authors_who_posted_in_period'),
                                             case([
                                                   (cumulative_visitors_subquery.c.count_cumulative_logged_in_visitors == 0, None),
                                                   (cumulative_visitors_subquery.c.count_cumulative_logged_in_visitors != 0, (cast(post_subquery.c.count_post_authors, Float) / cast(cumulative_visitors_subquery.c.count_cumulative_logged_in_visitors, Float)))
                                                   ]).label('fraction_cumulative_logged_in_visitors_who_posted_in_period'),
                                             subscribers_subquery,
                                             )
        combined_query = combined_query.join(post_subquery, post_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(post_viewers_subquery, post_viewers_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(visitors_subquery, visitors_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(cumulative_visitors_subquery, cumulative_visitors_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(members_subquery, members_subquery.c.interval_id==intervals_table.c.interval_id)
        combined_query = combined_query.join(subscribers_subquery, subscribers_subquery.c.interval_id==intervals_table.c.interval_id)
        combined_query = combined_query.join(cumulative_posts_subquery, cumulative_posts_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(votes_subquery, votes_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(cumulative_votes_subquery, cumulative_votes_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(actions_subquery, actions_subquery.c.interval_id == intervals_table.c.interval_id)
        combined_query = combined_query.join(cumulative_actions_subquery, cumulative_actions_subquery.c.interval_id == intervals_table.c.interval_id)

        query = combined_query
        query = query.order_by(intervals_table.c.interval_id)
        results = query.all()

        # pprint.pprint(results)
        # end of transaction

    intervals_table.drop()
    if format == JSON_MIMETYPE:
            # json default
        return Response(json.dumps(results, cls=DateJSONEncoder),
                        content_type='application/json')

    fieldnames = [
        "interval_id",
        "interval_start",
        "interval_end",
        "count_posts",
        "count_cumulative_posts",
        "count_post_authors",
        "count_cumulative_post_authors",
        "fraction_cumulative_authors_who_posted_in_period",

        "count_votes",
        "count_cumulative_votes",
        "count_voters",
        "count_cumulative_voters",
        "count_actors",
        "count_cumulative_actors",

        "count_approximate_members",
        "count_first_time_logged_in_visitors",
        "count_cumulative_logged_in_visitors",
        "fraction_cumulative_logged_in_visitors_who_posted_in_period",
        "recruitment_count_first_visit_in_period",
        "UNRELIABLE_recruitment_count_first_subscribed_in_period",
        "retention_count_last_visit_in_period",
        "UNRELIABLE_retention_count_first_subscribed_in_period",
        "UNRELIABLE_count_post_viewers",
    ]
    # otherwise assume csv
    return csv_response([r._asdict() for r in results], format, fieldnames)


def csv_response(results, format, fieldnames=None):
    output = StringIO()

    if format == CSV_MIMETYPE:
        from csv import writer
        csv = writer(output, dialect='excel', delimiter=';')
        writerow =  csv.writerow
        empty = ''
    elif format == XSLX_MIMETYPE:
        from zipfile import ZipFile, ZIP_DEFLATED
        from openpyxl.workbook import Workbook
        workbook = Workbook(True)
        archive = ZipFile(output, 'w', ZIP_DEFLATED, allowZip64=True)
        worksheet = workbook.create_sheet()
        writerow = worksheet.append
        empty = None

    if fieldnames:
        writerow(fieldnames)
        for r in results:
            writerow([r.get(f, empty) for f in fieldnames])
    else:
        for r in results:
            writerow(r)

    if format == XSLX_MIMETYPE:
        from openpyxl.writer.excel import ExcelWriter
        writer = ExcelWriter(workbook, archive)
        writer.save('')

    output.seek(0)
    return Response(body_file=output, content_type=format)


@view_config(context=InstanceContext, name="contribution_count",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_contribution_count(request):
    import isodate
    from datetime import datetime
    start = request.GET.get("start", None)
    end = request.GET.get("end", None)
    interval = request.GET.get("interval", None)
    format = get_format(request, stats_formats)
    discussion = request.context._instance
    try:
        if start:
            start = parse_datetime(start)
        if end:
            end = parse_datetime(end)
        if interval:
            interval = isodate.parse_duration(interval)
    except isodate.ISO8601Error as e:
        raise HTTPBadRequest(e)
    if interval and not start:
        raise HTTPBadRequest("You cannot define an interval and no start")
    if interval and not end:
        end = datetime.now()
    results = []
    if interval:
        while start < end:
            this_end = min(start+interval, end)
            results.append(dict(
                start=start.isoformat(), end=this_end.isoformat(),
                count=discussion.count_contributions_per_agent(
                    start, this_end)))
            start = this_end
    else:
        r = dict(count=discussion.count_contributions_per_agent(start, end))
        if not start:
            from assembl.models import Post
            from sqlalchemy import func
            (start,) = discussion.db.query(
                func.min(Post.creation_date)).filter_by(
                discussion_id=discussion.id).first()
        r["start"] = start.isoformat()
        if not end:
            end = datetime.now()
        r["end"] = end.isoformat()
        results.append(r)
    if format == JSON_MIMETYPE:
        # json default
        for v in results:
            v['count'] = {agent.display_name(): count
                          for (agent, count) in v['count']}
        return Response(json.dumps(results, cls=DateJSONEncoder),
            content_type='application/json')

    total_count = defaultdict(int)
    agents = {}
    for v in results:
        as_dict = {}
        for (agent, count) in v['count']:
            total_count[agent.id] += count
            as_dict[agent.id] = count
            agents[agent.id] = agent
        v['count'] = as_dict
    count_list = total_count.items()
    count_list.sort(key=lambda (a, c): c, reverse=True)
    rows = []
    rows.append(['Start']+[
        x['start'] for x in results] + ['Total'])
    rows.append(['End']+[
        x['end'] for x in results] + [''])
    for agent_id, total_count in count_list:
        agent = agents[agent_id]
        agent_name = (
            agent.display_name() or agent.real_name() or
            agent.get_preferred_email())
        rows.append([agent_name.encode('utf-8')] + [
            x['count'].get(agent_id, '') for x in results] + [total_count])
    return csv_response(rows, format)


@view_config(context=InstanceContext, name="visit_count",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_visit_count(request):
    import isodate
    from datetime import datetime
    start = request.GET.get("start", None)
    end = request.GET.get("end", None)
    interval = request.GET.get("interval", None)
    format = get_format(request, stats_formats)
    discussion = request.context._instance
    try:
        if start:
            start = parse_datetime(start)
        if end:
            end = parse_datetime(end)
        if interval:
            interval = isodate.parse_duration(interval)
    except isodate.ISO8601Error as e:
        raise HTTPBadRequest(e)
    if interval and not start:
        raise HTTPBadRequest("You cannot define an interval and no start")
    if interval and not end:
        end = datetime.now()
    results = []
    if interval:
        while start < end:
            this_end = min(start+interval, end)
            results.append(dict(
                start=start.isoformat(), end=this_end.isoformat(),
                readers=discussion.count_post_viewers(
                    start, this_end),
                first_visitors=discussion.count_new_visitors(
                    start, this_end)))
            start = this_end
    else:
        r = dict(
            readers=discussion.count_post_viewers(start, end),
            first_visitors=discussion.count_new_visitors(start, end))
        if not start:
            from assembl.models import AgentStatusInDiscussion
            from sqlalchemy import func
            (start,) = discussion.db.query(
                func.min(AgentStatusInDiscussion.first_visit)).filter_by(
                discussion_id=discussion.id).first()
        r["start"] = start.isoformat()
        if not end:
            end = datetime.now()
        r["end"] = end.isoformat()
        results.append(r)
    if format == JSON_MIMETYPE:
        # json default
        return Response(json.dumps(results, cls=DateJSONEncoder),
            content_type='application/json')
    # otherwise assume csv
    fieldnames=['start', 'end', 'first_visitors', 'readers']
    return csv_response(results, format, fieldnames)


@view_config(context=InstanceContext, name="visitors",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_visitors(request):
    discussion = request.context._instance
    use_first = asbool(request.GET.get("first", False))
    attribute = "first_visit" if use_first else "last_visit"
    visitors = [
        (getattr(st, attribute), st.agent_profile.name,
            st.agent_profile.get_preferred_email())
        for st in discussion.agent_status_in_discussion
        if getattr(st, attribute, None)]
    visitors.sort()
    visitors.reverse()
    body = "\n".join(("%s: %s <%s>" % (x[0].isoformat(), x[1], x[2])
                      for x in visitors))
    return Response(body=body, content_type='text/text')


pygraphviz_formats = {
    'text/vnd.graphviz': 'dot',
    'image/gif': 'gif',
    'application/vnd.hp-hpgl': 'hpgl',
    'image/jpeg': 'jpeg',
    'application/vnd.mif': 'mif',
    'application/vnd.hp-pcl': 'pcl',
    'application/pdf': 'pdf',
    'image/x-pict': 'pic',
    'image/png': 'png',
    'application/postscript': 'ps',
    'image/svg+xml': 'svg',
    'model/vrml': 'vrml',
}


@view_config(context=InstanceContext, name="mindmap",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_READ)
def as_mind_map(request):
    """Provide a mind-map like representation of the table of ideas"""
    for mimetype in request.GET.getall('mimetype'):
        mimetype = mimetype.encode('utf-8')
        if mimetype in pygraphviz_formats:
            break
    else:
        mimetype = request.accept.best_match(pygraphviz_formats.keys())
        if not mimetype:
            raise HTTPNotAcceptable("Not known to pygraphviz: "+mimetype)
    discussion = request.context._instance
    G = discussion.as_mind_map()
    G.layout(prog='twopi')
    io = StringIO()
    G.draw(io, format=pygraphviz_formats[mimetype])
    io.seek(0)
    return Response(body_file=io, content_type=mimetype)


def get_analytics_alerts(discussion, user_id, types, all_users=False):
    settings = get_config()
    metrics_server_endpoint = settings.get(
        'metrics_server_endpoint',
        'https://discussions.bluenove.com/analytics/accept')
    verify_metrics = False  # weird SNI bug on some platforms
    protocol = 'https' if asbool(settings.get(
        'accept_secure_connection', False)) else 'http'
    host = settings.get('public_hostname')
    if settings.get('public_port', 80) != 80:
        # TODO: public_secure_port?
        host += ':'+str(settings.get('public_port'))
    seed = urandom(8)
    obfuscator = AESObfuscator(seed)
    token = permission_token(user_id, discussion.id, [P_READ_PUBLIC_CIF], seed)
    metrics_requests = [{
        "metric": "alerts",
        "types": types}]
    if user_id != Everyone and not all_users:
        obfuscated_userid = "local:AgentProfile/" + obfuscator.encrypt(
            str(user_id))
        metrics_requests[0]['users'] = [obfuscated_userid]
    mapurl = '%s://%s/data/Discussion/%d/jsonld?token=%s' % (
        protocol,
        host,
        discussion.id,
        token
        )
    alerts = requests.post(metrics_server_endpoint, data=dict(
        mapurl=mapurl, requests=json.dumps(metrics_requests), recency=60),
        verify=verify_metrics)
    obfuscator.deobfuscate(alerts.text)
    # AgentAccount is a pseudo for AgentProfile
    result = re.sub(r'local:AgentAccount\\/', r'local:AgentProfile\\/', result)
    return result


@view_config(context=InstanceContext, name="activity_alerts",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_activity_alerts(request):
    discussion = request.context._instance
    user_id = authenticated_userid(request) or Everyone
    result = get_analytics_alerts(
        discussion, user_id,
        ["lurking_user", "inactive_user", "user_gone_inactive"],
        True)
    return Response(body=result, content_type='application/json')


@view_config(context=InstanceContext, name="interest_alerts",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_interest_alerts(request):
    discussion = request.context._instance
    user_id = authenticated_userid(request) or Everyone
    result = get_analytics_alerts(
        discussion, user_id,
        ["interesting_to_me"],
        True)
    return Response(body=result, content_type='application/json')


@view_config(context=InstanceContext, name="clusters",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def show_cluster(request):
    discussion = request.context._instance
    output = StringIO()
    from assembl.nlp.clusters import SKLearnClusteringSemanticAnalysis
    analysis = SKLearnClusteringSemanticAnalysis(discussion)
    analysis.as_html(output)
    output.seek(0)
    return Response(body_file=output, content_type='text/html')


@view_config(context=InstanceContext, name="optics",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_READ)
def show_optics_cluster(request):
    discussion = request.context._instance
    eps = float(request.GET.get("eps", "0.02"))
    min_samples = int(request.GET.get("min_samples", "3"))
    test_code = request.GET.get("test_code", None)
    suggestions = request.GET.get("suggestions", True)
    discussion = request.context._instance
    output = StringIO()
    user_id = authenticated_userid(request) or Everyone
    from assembl.nlp.clusters import (
        OpticsSemanticsAnalysis, OpticsSemanticsAnalysisWithSuggestions)
    if asbool(suggestions):
        analysis = OpticsSemanticsAnalysisWithSuggestions(
            discussion, min_samples=min_samples, eps=eps,
            user_id=user_id, test_code=test_code)
    else:
        analysis = OpticsSemanticsAnalysis(
            discussion, min_samples=min_samples, eps=eps,
            user_id=user_id, test_code=test_code)
    from pyramid_jinja2 import IJinja2Environment
    jinja_env = request.registry.queryUtility(
        IJinja2Environment, name='.jinja2')
    analysis.as_html(output, jinja_env)
    output.seek(0)
    return Response(body_file=output, content_type='text/html')


@view_config(context=InstanceContext, name="suggestions_test",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_READ)
def show_suggestions_test(request):
    discussion = request.context._instance
    user_id = authenticated_userid(request)
    if not user_id:
        from urllib import quote
        raise HTTPFound(location="/login?next="+quote(request.path))
    discussion = request.context._instance
    output = StringIO()
    from assembl.nlp.clusters import OpticsSemanticsAnalysisWithSuggestions
    analysis = OpticsSemanticsAnalysisWithSuggestions(
        discussion, user_id=user_id, min_samples=3, test_code=str(user_id))
    from pyramid_jinja2 import IJinja2Environment
    jinja_env = request.registry.queryUtility(
        IJinja2Environment, name='.jinja2')
    analysis.as_html(output, jinja_env)
    output.seek(0)
    return Response(body_file=output, content_type='text/html')


@view_config(context=InstanceContext, name="test_results",
             ctx_instance_class=Discussion, request_method='POST',
             header=FORM_HEADER, permission=P_READ)
def test_results(request):
    mailer = get_mailer(request)
    config = get_config()
    message = Message(
        subject="test_results",
        sender=config.get('assembl.admin_email'),
        recipients=["maparent@acm.org"],
        body=json.dumps(request.POST.dict_of_lists()))
    mailer.send(message)
    return Response(body="Thank you!", content_type="text/text")


@view_config(context=InstanceContext, name="test_sentry",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_READ)
def test_sentry(request):
    raise RuntimeError("Let's test sentry")


@etalab_discussions.post(permission=P_SYSADMIN)
@view_config(context=ClassContext, ctx_class=Discussion,
             request_method='POST', header=JSON_HEADER, permission=P_SYSADMIN)
def post_discussion(request):
    from assembl.models import EmailAccount, User, LocalUserRole, Role, AbstractAgentAccount
    ctx = request.context
    json = request.json_body
    user_id = authenticated_userid(request) or Everyone
    permissions = get_permissions(user_id, None)
    is_etalab_request = (request.matched_route and request.matched_route.name == 'etalab_discussions')
    if is_etalab_request:
        # The Etalab specification says that the API call representing the instance creation request must contain the following fields:
        # - requestIdentifier
        # - name: the title of the discussion (discussion.topic)
        # - slug
        # - adminName
        # - adminEmail
        default_view = 'etalab'
        # Fake an APIv2 context
        from ..traversal import Api2Context
        ctx = Api2Context(ctx)
        ctx = ClassContext(ctx, Discussion)
        json['topic'] = json.get('name', json.get('slug', ''))
    else:
        default_view = 'default'
    cls = ctx.get_class(json.get('@type', None))
    typename = cls.external_typename()
    # special case: find the user first.
    creator_email = json.get("adminEmail", None)
    db = Discussion.default_db
    if creator_email:
        account = db.query(AbstractAgentAccount).filter_by(
            email=creator_email, verified=True).first()
        if account:
            user = account.profile
        else:
            user = User(name=json.get("adminName", None), verified=True)
            account = EmailAccount(profile=user, email=creator_email, verified=True)
            db.add(user)
            db.flush()
        json['creator'] = user.uri()
    else:
        user = None
    try:
        instances = ctx.create_object(typename, json, user_id)
        discussion = instances[0]
        # Hackish. Discussion API? Generic post-init method?
        discussion.preferences.name = (
            'discussion_' + json.get('slug', str(discussion.id)))
        create_default_permissions(discussion)
        if user is not None:
            role = db.query(Role).filter_by(name=R_ADMINISTRATOR).first()
            local_role = LocalUserRole(discussion=discussion, user=user, role=role)
            instances.append(local_role)
        discussion.invoke_callbacks_after_creation()
    except ObjectNotUniqueError as e:
        raise HTTPBadRequest(e)
    except Exception as e:
        raise HTTPServerError(e)
    if instances:
        first = instances[0]
        db = first.db
        for instance in instances:
            db.add(instance)
        db.flush()
        view = request.GET.get('view', None) or default_view
        uri = "/".join((API_ETALAB_DISCUSSIONS_PREFIX, str(first.id))) if is_etalab_request else None
        return CreationResponse(first, user_id, permissions, view, uri=uri)


class defaultdict_of_dict(defaultdict):
    """A defaultdict of dicts."""
    def __init__(self):
        super(defaultdict_of_dict, self).__init__(dict)



@view_config(context=InstanceContext, name="participant_time_series_analytics",
             ctx_instance_class=Discussion, request_method='GET',
             permission=P_DISC_STATS)
def get_participant_time_series_analytics(request):
    import isodate
    from datetime import datetime
    start = request.GET.get("start", None)
    end = request.GET.get("end", None)
    interval = request.GET.get("interval", None)
    data_descriptors = request.GET.getall("data")
    discussion = request.context._instance
    user_id = authenticated_userid(request) or Everyone
    try:
        if start:
            start = parse_datetime(start)
        if end:
            end = parse_datetime(end)
        if interval:
            interval = isodate.parse_duration(interval)
    except isodate.ISO8601Error as e:
        raise HTTPBadRequest(e)
    if interval and not start:
        raise HTTPBadRequest("You cannot define an interval and no start")
    if interval and not end:
        end = datetime.now()
    format = get_format(request, stats_formats)
    results = []

    default_data_descriptors = [
        "posts",
        "cumulative_posts",
        "liking",
        "cumulative_liking",
        "liked",
        "cumulative_liked",
        "replies_received",
        "cumulative_replies_received",
    ]
    data_descriptors = data_descriptors or default_data_descriptors
    # Impose data_descriptors order
    data_descriptors = [s for s in default_data_descriptors if s in data_descriptors]
    if not data_descriptors:
        raise HTTPBadRequest("No valid data descriptor given")

    from sqlalchemy import Table, MetaData, and_, or_, case, cast, Float
    from sqlalchemy.exc import ProgrammingError
    from sqlalchemy.orm import with_polymorphic
    from sqlalchemy.sql.expression import literal
    import pprint
    import transaction
    with transaction.manager:
        metadata = MetaData(discussion.db.get_bind())  # make sure we are using the same connexion

        intervals_table = Table('temp_table_intervals_' + str(user_id), metadata,
            Column('interval_id', Integer, primary_key=True),
            Column('interval_start', DateTime, nullable=False),
            Column('interval_end', DateTime, nullable=False),
            prefixes=None if discussion.using_virtuoso else ['TEMPORARY']
        )
        try:
            intervals_table.drop()  # In case there is a leftover from a previous crash
        except ProgrammingError:
            pass
        intervals_table.create()
        interval_start = start
        intervals = []
        if interval:
            while interval_start < end:
                interval_end = min(interval_start + interval, end)
                intervals.append({'interval_start': interval_start, 'interval_end': interval_end})
                interval_start = interval_start + interval
            #pprint.pprint(intervals)
            discussion.db.execute(intervals_table.insert(), intervals)
        else:
            raise HTTPBadRequest("Please specify an interval")

        from assembl.models import (
            Post, AgentProfile, AgentStatusInDiscussion, ViewPost, Idea,
            AbstractIdeaVote, Action, ActionOnPost, ActionOnIdea, Content,
            PublicationStates, LikedPost)

        # content = with_polymorphic(
        #             Content, [], Content.__table__,
        #             aliased=False, flat=True)
        # post = with_polymorphic(Post, [])

        query_components = []

        if 'posts' in data_descriptors:
            # The posters
            post_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('posts').label('key'),
                func.count(distinct(Post.id)).label('value'),
                )
            post_query = post_query.join(Post, and_(Post.creation_date >= intervals_table.c.interval_start, Post.creation_date < intervals_table.c.interval_end, Post.discussion_id == discussion.id))
            post_query = post_query.join(AgentProfile, Post.creator_id == AgentProfile.id)
            post_query = post_query.group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(post_query)

        if 'cumulative_posts' in data_descriptors:
            # Cumulative posters
            cumulative_post_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('cumulative_posts').label('key'),
                func.count(distinct(Post.id)).label('value'),
                )
            cumulative_post_query = cumulative_post_query.join(Post, and_(
                Post.creation_date < intervals_table.c.interval_end,
                Post.publication_state == PublicationStates.PUBLISHED,
                Post.discussion_id == discussion.id))
            cumulative_post_query = cumulative_post_query.join(AgentProfile, Post.creator_id == AgentProfile.id)
            cumulative_post_query = cumulative_post_query.group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(cumulative_post_query)

        if 'liking' in data_descriptors:
            # The likes made
            liking_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('liking').label('key'),
                func.count(distinct(LikedPost.id)).label('value'),
                )
            liking_query = liking_query.join(Post, Post.discussion_id == discussion.id)
            liking_query = liking_query.join(LikedPost, and_(
                LikedPost.creation_date >= intervals_table.c.interval_start,
                LikedPost.creation_date < intervals_table.c.interval_end,
                LikedPost.post_id == Post.id))
            liking_query = liking_query.join(AgentProfile, LikedPost.actor_id == AgentProfile.id)
            liking_query = liking_query.group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(liking_query)

        if 'cumulative_liking' in data_descriptors:
            # The cumulative active likes made
            cumulative_liking_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('cumulative_liking').label('key'),
                func.count(distinct(LikedPost.id)).label('value'),
                )
            cumulative_liking_query = cumulative_liking_query.join(Post, Post.discussion_id == discussion.id)
            cumulative_liking_query = cumulative_liking_query.join(LikedPost, and_(
                LikedPost.tombstone_date == None,
                LikedPost.creation_date < intervals_table.c.interval_end,
                LikedPost.post_id == Post.id))
            cumulative_liking_query = cumulative_liking_query.join(AgentProfile, LikedPost.actor_id == AgentProfile.id)
            cumulative_liking_query = cumulative_liking_query.group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(cumulative_liking_query)

        if 'liked' in data_descriptors:
            # The likes received
            liked_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('liked').label('key'),
                func.count(distinct(LikedPost.id)).label('value'),
                )
            liked_query = liked_query.join(Post, Post.discussion_id == discussion.id)
            liked_query = liked_query.join(LikedPost, and_(
                LikedPost.creation_date >= intervals_table.c.interval_start,
                LikedPost.creation_date < intervals_table.c.interval_end,
                LikedPost.post_id == Post.id))
            liked_query = liked_query.join(AgentProfile, Post.creator_id == AgentProfile.id)
            liked_query = liked_query.group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(liked_query)

        if 'cumulative_liked' in data_descriptors:
            # The cumulative active likes received
            cumulative_liked_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('cumulative_liked').label('key'),
                func.count(distinct(LikedPost.id)).label('value'),
                )
            cumulative_liked_query = cumulative_liked_query.outerjoin(Post, Post.discussion_id == discussion.id)
            cumulative_liked_query = cumulative_liked_query.outerjoin(LikedPost, and_(
                LikedPost.tombstone_date == None,
                LikedPost.creation_date < intervals_table.c.interval_end,
                LikedPost.post_id == Post.id))
            cumulative_liked_query = cumulative_liked_query.outerjoin(AgentProfile, Post.creator_id == AgentProfile.id)
            cumulative_liked_query = cumulative_liked_query.group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(cumulative_liked_query)

        if 'replies_received' in data_descriptors:
            # The posters
            reply_post = aliased(Post)
            original_post = aliased(Post)
            reply_post_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('replies_received').label('key'),
                func.count(distinct(reply_post.id)).label('value'),
                ).join(reply_post, and_(
                    reply_post.creation_date >= intervals_table.c.interval_start,
                    reply_post.creation_date < intervals_table.c.interval_end,
                    reply_post.discussion_id == discussion.id)
                ).join(original_post, original_post.id == reply_post.parent_id
                ).join(AgentProfile, original_post.creator_id == AgentProfile.id
                ).group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(reply_post_query)

        if 'cumulative_replies_received' in data_descriptors:
            # The posters
            reply_post = aliased(Post)
            original_post = aliased(Post)
            cumulative_reply_post_query = discussion.db.query(
                intervals_table.c.interval_id.label('interval_id'),
                AgentProfile.id.label('participant_id'),
                AgentProfile.name.label('participant'),
                literal('cumulative_replies_received').label('key'),
                func.count(distinct(reply_post.id)).label('value'),
                ).join(reply_post, and_(
                    reply_post.creation_date < intervals_table.c.interval_end,
                    reply_post.publication_state == PublicationStates.PUBLISHED,
                    reply_post.discussion_id == discussion.id)
                ).join(original_post, and_(
                    original_post.id == reply_post.parent_id,
                    original_post.publication_state == PublicationStates.PUBLISHED)
                ).join(AgentProfile, original_post.creator_id == AgentProfile.id
                ).group_by(intervals_table.c.interval_id, AgentProfile.id)
            query_components.append(cumulative_reply_post_query)

        combined_subquery = query_components.pop(0)
        if query_components:
            combined_subquery = combined_subquery.union(*query_components)
        combined_subquery = combined_subquery.subquery('combined')
        query = discussion.db.query(intervals_table, combined_subquery).outerjoin(
            combined_subquery, combined_subquery.c.interval_id == intervals_table.c.interval_id
            ).order_by(intervals_table.c.interval_id)
        results = query.all()

        # pprint.pprint(results)
        # end of transaction

    # intervals_table.drop()  # temporary is dropped implicitly

    if format == JSON_MIMETYPE:
        from assembl.lib.json import DateJSONEncoder
        combined = []
        interval_id = None
        interval_data = None
        interval_elements = {'interval_id', 'interval_start', 'interval_end'}
        # We have fragmented interval+participant+key=>value.
        # Structure we're going for: List of intervals,
        # each data interval has list of combined participant info,
        # each in key=>value format.
        for element in results:
            element = element._asdict()
            if element['interval_id'] != interval_id:
                interval_data = {
                    k: element[k] for k in interval_elements
                }
                interval_data['data'] = interval_datalist = defaultdict(dict)
                combined.append(interval_data)
                interval_id = element['interval_id']
            participant_id = element['participant_id']
            if participant_id is not None:
                if element['value'] != 0:
                    data = interval_datalist[participant_id]
                    data[element['key']] = element['value']
                    data['participant'] = element['participant']
                    data['participant_id'] = participant_id
        for interval_data in combined:
            interval_data['data'] = interval_data['data'].values()
        return Response(json.dumps(combined, cls=DateJSONEncoder),
                        content_type=format)

    by_participant = defaultdict(defaultdict_of_dict)
    interval_ids = set()
    interval_starts = {}
    interval_ends = {}
    participant_names = {}

    for element in results:
        element = element._asdict()
        interval_id = element['interval_id']
        interval_ids.add(interval_id)
        interval_starts[interval_id] = element['interval_start']
        interval_ends[interval_id] = element['interval_end']
        pid = element['participant_id']
        value = element['value']
        if pid is not None and value != 0:
            participant_names[pid] = element['participant']
            key = element['key']
            by_participant[pid][interval_id][key] = value
    interval_ids = list(interval_ids)
    interval_ids.sort()
    num_cols = 2 + len(interval_ids)*len(data_descriptors)
    interval_starts = [interval_starts[id] for id in interval_ids]
    interval_ends = [interval_ends[id] for id in interval_ids]
    rows = []
    row = ['Participant id', 'Participant']
    for data_descriptor in data_descriptors:
        row += [data_descriptor] * len(interval_ids)
    rows.append(row)
    rows.append(['', 'Interval id'] + interval_ids * len(data_descriptors))
    rows.append(['', 'Interval start'] + interval_starts * len(data_descriptors))
    rows.append(['', 'Interval end'] + interval_ends * len(data_descriptors))
    for participant_id, interval_data in by_participant.iteritems():
        row = [participant_id, participant_names[participant_id].encode('utf-8')]
        for data_descriptor in data_descriptors:
            row_part = [''] * len(interval_ids)
            for interval_id, data in interval_data.iteritems():
                row_part[interval_id - 1] = data.get(data_descriptor, '')
            row += row_part
        rows.append(row)

    return csv_response(rows, format)


def includeme(config):
    # Make sure that the cornice view is registered
    pass
