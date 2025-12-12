# backend/app/services/farmer/feed_service.py

"""
Farmer Social Feed Service (in-memory) — Medium-weight (Feature #292)

Capabilities:
 - Posts (text + optional image URLs/base64), categories, hashtags, location (village/district)
 - Likes, comment threads (one level of nesting + replies list), views
 - Follow/unfollow, follow feed
 - Trending (time-window + engagement score)
 - Simple analytics: views, likes, comments counts, engagement rate
 - Hashtag search, text search (simple substring)
 - Badges (derived from activity) and simple spam detection heuristics
 - Reporting mechanism (in-memory queue)
 - Lightweight caching for trending/top posts
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple
import uuid
import re
import math

_lock = Lock()

# Stores
_posts: Dict[str, Dict[str, Any]] = {}              # post_id -> post
_posts_by_user: Dict[str, List[str]] = {}           # user_id -> [post_id]
_posts_by_location: Dict[str, List[str]] = {}       # "district:village" -> [post_id]
_followers: Dict[str, set] = {}                     # user_id -> set(follower_user_ids)  (who follows user_id)
_following: Dict[str, set] = {}                     # user_id -> set(user_ids they follow)

_comments: Dict[str, Dict[str, Any]] = {}           # comment_id -> comment (supports replies list)
_comments_by_post: Dict[str, List[str]] = {}        # post_id -> [comment_id]

_likes: Dict[str, set] = {}                         # entity_id -> set(user_id) (entity can be post_id or comment_id)
_views: Dict[str, int] = {}                         # post_id -> view_count

_reports: List[Dict[str, Any]] = []                 # reported content queue

_badges: Dict[str, List[str]] = {}                  # user_id -> list of badges

_trending_cache: Dict[str, Any] = {"updated_at": None, "items": []}  # cached trending list

# Basic config
SPAM_KEYWORDS = {"buyfollowers", "freecoins", "clickhere", "cheapfertilizer"}
TREND_WINDOW_HOURS = 72
TREND_TOP_N = 20

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _newid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"

def _location_key(district: Optional[str], village: Optional[str]) -> str:
    return f"{district or 'any'}:{village or 'any'}"

def _extract_hashtags(text: str) -> List[str]:
    # simple hashtag extractor: words starting with #
    return re.findall(r"#(\w+)", text or "")

def _is_spam_text(text: str) -> bool:
    t = (text or "").lower()
    for k in SPAM_KEYWORDS:
        if k in t:
            return True
    # too many links heuristic
    links = re.findall(r"https?://", t)
    if len(links) > 3:
        return True
    return False

def _engagement_score(post: Dict[str, Any]) -> float:
    # score based on weighted likes, comments, views and recency
    pid = post["post_id"]
    likes = len(_likes.get(pid, set()))
    comments = len(_comments_by_post.get(pid, []))
    views = _views.get(pid, 0)
    created = datetime.fromisoformat(post["created_at"])
    age_hours = max(1.0, (datetime.utcnow() - created).total_seconds() / 3600.0)
    score = (likes * 3.0) + (comments * 4.0) + math.log(1 + views)  # engagement
    # recency boost
    recency_boost = max(0.5, 48.0 / age_hours)  # older posts get less weight
    return score * recency_boost

# -------------------------------------------------------------------
# Posts
# -------------------------------------------------------------------
def create_post(
    user_id: str,
    text: str,
    images: Optional[List[str]] = None,
    category: Optional[str] = None,
    district: Optional[str] = None,
    village: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    allow_comments: bool = True,
    visibility: str = "public"  # public | followers | private
) -> Dict[str, Any]:
    """
    Create a post. Basic spam detection runs and a 'flagged_for_review' boolean is set if detected.
    """
    pid = _newid("post")
    hashtags = _extract_hashtags(text)
    is_spam = _is_spam_text(text)
    rec = {
        "post_id": pid,
        "user_id": user_id,
        "text": text,
        "images": images or [],
        "category": category or None,
        "hashtags": hashtags,
        "district": district,
        "village": village,
        "location_key": _location_key(district, village),
        "metadata": metadata or {},
        "visibility": visibility,
        "allow_comments": allow_comments,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "flagged_for_review": is_spam,
        "deleted": False
    }
    with _lock:
        _posts[pid] = rec
        _posts_by_user.setdefault(user_id, []).append(pid)
        _posts_by_location.setdefault(rec["location_key"], []).append(pid)
        _views[pid] = 0
        # init likes/comments lists
        _likes.setdefault(pid, set())
        _comments_by_post.setdefault(pid, [])
    # update trending cache lazily (not here)
    return rec

def edit_post(user_id: str, post_id: str, text: Optional[str] = None, images: Optional[List[str]] = None, category: Optional[str] = None, allow_comments: Optional[bool] = None) -> Dict[str, Any]:
    with _lock:
        p = _posts.get(post_id)
        if not p:
            return {"error": "post_not_found"}
        if p.get("user_id") != user_id:
            return {"error": "permission_denied"}
        if text is not None:
            p["text"] = text
            p["hashtags"] = _extract_hashtags(text)
            p["flagged_for_review"] = _is_spam_text(text)
        if images is not None:
            p["images"] = images
        if category is not None:
            p["category"] = category
        if allow_comments is not None:
            p["allow_comments"] = bool(allow_comments)
        p["updated_at"] = _now_iso()
        _posts[post_id] = p
    return p

def delete_post(user_id: str, post_id: str) -> Dict[str, Any]:
    with _lock:
        p = _posts.get(post_id)
        if not p:
            return {"error": "post_not_found"}
        if p.get("user_id") != user_id:
            return {"error": "permission_denied"}
        p["deleted"] = True
        p["updated_at"] = _now_iso()
        _posts[post_id] = p
    return {"deleted": post_id}

def get_post(post_id: str, viewer_id: Optional[str] = None, mark_view: bool = True) -> Dict[str, Any]:
    p = _posts.get(post_id)
    if not p or p.get("deleted"):
        return {}
    # visibility logic
    if p.get("visibility") == "private" and p.get("user_id") != viewer_id:
        return {}
    if p.get("visibility") == "followers" and viewer_id and viewer_id not in (_followers.get(p.get("user_id"), set())) and p.get("user_id") != viewer_id:
        # viewer doesn't follow author
        return {}
    if mark_view:
        with _lock:
            _views[post_id] = _views.get(post_id, 0) + 1
    # attach aggregated metrics
    metrics = {
        "views": _views.get(post_id, 0),
        "likes": len(_likes.get(post_id, set())),
        "comments": len(_comments_by_post.get(post_id, []))
    }
    out = dict(p)
    out["metrics"] = metrics
    return out

def list_posts_by_user(user_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    ids = _posts_by_user.get(user_id, [])[::-1]  # newest first
    slice_ids = ids[offset: offset + limit]
    return {"count": len(slice_ids), "posts": [get_post(pid, viewer_id=None, mark_view=False) for pid in slice_ids]}

# -------------------------------------------------------------------
# Likes
# -------------------------------------------------------------------
def like_entity(user_id: str, entity_id: str) -> Dict[str, Any]:
    with _lock:
        s = _likes.setdefault(entity_id, set())
        if user_id in s:
            return {"status": "already_liked"}
        s.add(user_id)
        _likes[entity_id] = s
    return {"status": "liked", "entity_id": entity_id, "likes_count": len(s)}

def unlike_entity(user_id: str, entity_id: str) -> Dict[str, Any]:
    with _lock:
        s = _likes.get(entity_id, set())
        if user_id not in s:
            return {"status": "not_liked"}
        s.remove(user_id)
        _likes[entity_id] = s
    return {"status": "unliked", "entity_id": entity_id, "likes_count": len(s)}

# -------------------------------------------------------------------
# Comments (supports replies via `replies` list)
# -------------------------------------------------------------------
def add_comment(user_id: str, post_id: str, text: str, parent_comment_id: Optional[str] = None) -> Dict[str, Any]:
    if post_id not in _posts or _posts[post_id].get("deleted"):
        return {"error": "post_not_found"}
    cid = _newid("c")
    rec = {
        "comment_id": cid,
        "post_id": post_id,
        "user_id": user_id,
        "text": text,
        "parent": parent_comment_id,
        "replies": [],
        "created_at": _now_iso(),
        "deleted": False,
        "flagged_for_review": _is_spam_text(text)
    }
    with _lock:
        _comments[cid] = rec
        if parent_comment_id:
            parent = _comments.get(parent_comment_id)
            if parent:
                parent.setdefault("replies", []).append(cid)
                _comments[parent_comment_id] = parent
        else:
            _comments_by_post.setdefault(post_id, []).append(cid)
    return rec

def edit_comment(user_id: str, comment_id: str, text: str) -> Dict[str, Any]:
    with _lock:
        c = _comments.get(comment_id)
        if not c:
            return {"error": "comment_not_found"}
        if c.get("user_id") != user_id:
            return {"error": "permission_denied"}
        c["text"] = text
        c["flagged_for_review"] = _is_spam_text(text)
        c["updated_at"] = _now_iso()
        _comments[comment_id] = c
    return c

def delete_comment(user_id: str, comment_id: str) -> Dict[str, Any]:
    with _lock:
        c = _comments.get(comment_id)
        if not c:
            return {"error": "comment_not_found"}
        if c.get("user_id") != user_id:
            return {"error": "permission_denied"}
        c["deleted"] = True
        c["updated_at"] = _now_iso()
        _comments[comment_id] = c
    return {"deleted": comment_id}

def list_comments(post_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    cids = _comments_by_post.get(post_id, [])
    slice_ids = cids[offset: offset + limit]
    items = []
    for cid in slice_ids:
        c = _comments.get(cid)
        if c and not c.get("deleted"):
            # include reply objects (not full nested objects, but ids)
            items.append({
                "comment": c,
                "replies": [ _comments.get(r) for r in c.get("replies", []) if _comments.get(r) and not _comments.get(r).get("deleted") ]
            })
    return {"count": len(items), "comments": items}

# -------------------------------------------------------------------
# Followers / Following
# -------------------------------------------------------------------
def follow_user(follower_id: str, followee_id: str) -> Dict[str, Any]:
    if follower_id == followee_id:
        return {"error": "cannot_follow_self"}
    with _lock:
        _following.setdefault(follower_id, set()).add(followee_id)
        _followers.setdefault(followee_id, set()).add(follower_id)
    return {"status": "followed", "followee": followee_id}

def unfollow_user(follower_id: str, followee_id: str) -> Dict[str, Any]:
    with _lock:
        _following.setdefault(follower_id, set()).discard(followee_id)
        _followers.setdefault(followee_id, set()).discard(follower_id)
    return {"status": "unfollowed", "followee": followee_id}

def list_followers(user_id: str) -> List[str]:
    return list(_followers.get(user_id, set()))

def list_following(user_id: str) -> List[str]:
    return list(_following.get(user_id, set()))

# -------------------------------------------------------------------
# Reporting & moderation (in-memory stencil)
# -------------------------------------------------------------------
def report_content(reporter_id: str, entity_type: str, entity_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    rec = {
        "report_id": _newid("r"),
        "reporter_id": reporter_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "reason": reason or "",
        "created_at": _now_iso(),
        "handled": False
    }
    with _lock:
        _reports.append(rec)
    return rec

def list_reports(unhandled_only: bool = True) -> List[Dict[str, Any]]:
    if unhandled_only:
        return [r for r in _reports if not r.get("handled")]
    return list(_reports)

def mark_report_handled(report_id: str, handled_by: str, action: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        for r in _reports:
            if r.get("report_id") == report_id:
                r["handled"] = True
                r["handled_by"] = handled_by
                r["handled_at"] = _now_iso()
                r["action"] = action
                return r
    return {"error": "report_not_found"}

# -------------------------------------------------------------------
# Search & Hashtag support
# -------------------------------------------------------------------
def search_posts(query: Optional[str] = None, hashtag: Optional[str] = None, category: Optional[str] = None, district: Optional[str] = None, village: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    with _lock:
        items = [p for p in _posts.values() if not p.get("deleted")]
    if hashtag:
        items = [p for p in items if hashtag.lower() in [h.lower() for h in p.get("hashtags", [])]]
    if category:
        items = [p for p in items if p.get("category") and p.get("category").lower() == category.lower()]
    if district or village:
        key = _location_key(district, village)
        items = [p for p in items if p.get("location_key") == key]
    if query:
        q = query.lower()
        items = [p for p in items if q in (p.get("text") or "").lower() or any(q in (img or "").lower() for img in p.get("images", []))]
    # sort by created_at desc by default
    items = sorted(items, key=lambda x: x.get("created_at"), reverse=True)
    sliced = items[offset: offset + limit]
    return {"total": len(items), "count": len(sliced), "posts": sliced}

# -------------------------------------------------------------------
# Trending / Analytics
# -------------------------------------------------------------------
def compute_trending(window_hours: int = TREND_WINDOW_HOURS, top_n: int = TREND_TOP_N) -> List[Dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    with _lock:
        candidates = [p for p in _posts.values() if not p.get("deleted") and datetime.fromisoformat(p.get("created_at")) >= cutoff]
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for p in candidates:
        score = _engagement_score(p)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [p for (_, p) in scored[:top_n]]
    with _lock:
        _trending_cache["updated_at"] = _now_iso()
        _trending_cache["items"] = top
    return top

def get_trending(use_cache: bool = True) -> List[Dict[str, Any]]:
    if use_cache and _trending_cache.get("items"):
        # check recency
        updated = _trending_cache.get("updated_at")
        if updated:
            updated_dt = datetime.fromisoformat(updated)
            if (datetime.utcnow() - updated_dt).total_seconds() < 60 * 10:  # 10 minutes freshness
                return _trending_cache.get("items", [])
    return compute_trending()

def post_analytics(post_id: str) -> Dict[str, Any]:
    p = _posts.get(post_id)
    if not p:
        return {"error": "post_not_found"}
    likes = len(_likes.get(post_id, set()))
    comments = len(_comments_by_post.get(post_id, []))
    views = _views.get(post_id, 0)
    engagement_rate = round(((likes + comments) / (views + 1)) * 100, 2)
    return {"post_id": post_id, "likes": likes, "comments": comments, "views": views, "engagement_rate_percent": engagement_rate}

# -------------------------------------------------------------------
# Badges (simple heuristics)
# -------------------------------------------------------------------
def update_badges_for_user(user_id: str) -> List[str]:
    # simple badges: "influencer" (many followers), "helpful" (many accepted answers/comments), "active"
    followers_count = len(_followers.get(user_id, set()))
    posts_count = len(_posts_by_user.get(user_id, []))
    badges = _badges.get(user_id, [])[:]
    if followers_count > 50 and "influencer" not in badges:
        badges.append("influencer")
    if posts_count > 100 and "veteran" not in badges:
        badges.append("veteran")
    # active: posted in last 7 days
    now = datetime.utcnow()
    recent_posts = [p for p in (_posts_by_user.get(user_id, []) or []) if datetime.fromisoformat(_posts.get(p, {}).get("created_at", now.isoformat())) >= (now - timedelta(days=7))]
    if recent_posts and "active" not in badges:
        badges.append("active")
    with _lock:
        _badges[user_id] = badges
    return badges

def get_badges(user_id: str) -> List[str]:
    return _badges.get(user_id, [])

# -------------------------------------------------------------------
# Feed generation
# -------------------------------------------------------------------
def feed_for_user(user_id: str, district: Optional[str] = None, village: Optional[str] = None, only_following: bool = False, limit: int = 50, offset: int = 0, sort_by: str = "time") -> Dict[str, Any]:
    """
    Build a feed for a user:
      - if only_following: include posts only from users they follow
      - otherwise include local posts (district/village) + followees + trending boosters
      - sort_by: "time" | "engagement"
    """
    with _lock:
        all_posts = [p for p in _posts.values() if not p.get("deleted")]
    # filter by visibility
    visible = []
    following_set = _following.get(user_id, set())
    for p in all_posts:
        # location filter
        if district or village:
            if p.get("location_key") != _location_key(district, village):
                continue
        # visibility check
        vis = p.get("visibility", "public")
        if vis == "public":
            pass
        elif vis == "followers" and user_id not in _followers.get(p.get("user_id"), set()) and p.get("user_id") != user_id:
            continue
        elif vis == "private" and p.get("user_id") != user_id:
            continue
        if only_following and p.get("user_id") not in following_set:
            continue
        visible.append(p)
    # scoring/sort
    if sort_by == "engagement":
        visible = sorted(visible, key=lambda x: _engagement_score(x), reverse=True)
    else:
        visible = sorted(visible, key=lambda x: x.get("created_at"), reverse=True)
    # ensure followees appear higher (light boost)
    def follow_boost(p):
        return (1.0 if p.get("user_id") in following_set else 0.0, p.get("created_at"))
    visible = sorted(visible, key=lambda x: (0 if x.get("user_id") in following_set else 1, x.get("created_at")), reverse=True)
    sliced = visible[offset: offset + limit]
    # optionally mark views
    for p in sliced:
        _views[p["post_id"]] = _views.get(p["post_id"], 0) + 1
    # attach metrics
    result = []
    for p in sliced:
        result.append({
            "post": p,
            "metrics": {"views": _views.get(p["post_id"], 0), "likes": len(_likes.get(p["post_id"], set())), "comments": len(_comments_by_post.get(p["post_id"], []))}
        })
    return {"count": len(sliced), "items": result}

# -------------------------------------------------------------------
# Simple moderation utilities that might be called by admin scripts
# -------------------------------------------------------------------
def delete_post_force(post_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        p = _posts.get(post_id)
        if not p:
            return {"error": "post_not_found"}
        p["deleted"] = True
        p["deleted_reason"] = reason
        p["updated_at"] = _now_iso()
        _posts[post_id] = p
    return {"deleted": post_id}

def clear_trending_cache():
    with _lock:
        _trending_cache["updated_at"] = None
        _trending_cache["items"] = []

# End of feed_service.py
