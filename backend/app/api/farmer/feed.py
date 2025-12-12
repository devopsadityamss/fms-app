# backend/app/api/farmer/feed.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.farmer.feed_service import (
    create_post,
    edit_post,
    delete_post,
    get_post,
    list_posts_by_user,
    like_entity,
    unlike_entity,
    add_comment,
    edit_comment,
    delete_comment,
    list_comments,
    follow_user,
    unfollow_user,
    list_followers,
    list_following,
    report_content,
    list_reports,
    mark_report_handled,
    search_posts,
    compute_trending,
    get_trending,
    post_analytics,
    update_badges_for_user,
    get_badges,
    feed_for_user,
    set_availability  # not a feed function but available if needed; harmless here
)

router = APIRouter()

# ----------------------------
# Pydantic models
# ----------------------------
class PostPayload(BaseModel):
    user_id: str
    text: str
    images: Optional[List[str]] = None
    category: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    allow_comments: Optional[bool] = True
    visibility: Optional[str] = "public"

class EditPostPayload(BaseModel):
    user_id: str
    text: Optional[str] = None
    images: Optional[List[str]] = None
    category: Optional[str] = None
    allow_comments: Optional[bool] = None

class LikePayload(BaseModel):
    user_id: str
    entity_id: str

class CommentPayload(BaseModel):
    user_id: str
    post_id: str
    text: str
    parent_comment_id: Optional[str] = None

class FollowPayload(BaseModel):
    follower_id: str
    followee_id: str

class ReportPayload(BaseModel):
    reporter_id: str
    entity_type: str
    entity_id: str
    reason: Optional[str] = None

# ----------------------------
# Post endpoints
# ----------------------------
@router.post("/farmer/feed/post")
def api_create_post(req: PostPayload):
    return create_post(
        user_id=req.user_id,
        text=req.text,
        images=req.images,
        category=req.category,
        district=req.district,
        village=req.village,
        metadata=req.metadata,
        allow_comments=req.allow_comments,
        visibility=req.visibility
    )

@router.post("/farmer/feed/post/{post_id}/edit")
def api_edit_post(post_id: str, req: EditPostPayload):
    res = edit_post(req.user_id, post_id, text=req.text, images=req.images, category=req.category, allow_comments=req.allow_comments)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/feed/post/{post_id}/delete")
def api_delete_post(post_id: str, user_id: str):
    res = delete_post(user_id, post_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/feed/post/{post_id}")
def api_get_post(post_id: str, viewer_id: Optional[str] = None):
    p = get_post(post_id, viewer_id=viewer_id)
    if not p:
        raise HTTPException(status_code=404, detail="post_not_found_or_inaccessible")
    return p

@router.get("/farmer/feed/user/{user_id}")
def api_user_posts(user_id: str, limit: int = 50, offset: int = 0):
    return list_posts_by_user(user_id, limit=limit, offset=offset)

# ----------------------------
# Likes
# ----------------------------
@router.post("/farmer/feed/like")
def api_like(req: LikePayload):
    return like_entity(req.user_id, req.entity_id)

@router.post("/farmer/feed/unlike")
def api_unlike(req: LikePayload):
    return unlike_entity(req.user_id, req.entity_id)

# ----------------------------
# Comments
# ----------------------------
@router.post("/farmer/feed/comment")
def api_add_comment(req: CommentPayload):
    res = add_comment(req.user_id, req.post_id, req.text, parent_comment_id=req.parent_comment_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/feed/comment/{comment_id}/edit")
def api_edit_comment(comment_id: str, user_id: str, text: str):
    res = edit_comment(user_id, comment_id, text)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/feed/comment/{comment_id}/delete")
def api_delete_comment(comment_id: str, user_id: str):
    res = delete_comment(user_id, comment_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.get("/farmer/feed/comments/{post_id}")
def api_list_comments(post_id: str, limit: int = 50, offset: int = 0):
    return list_comments(post_id, limit=limit, offset=offset)

# ----------------------------
# Follow / Unfollow
# ----------------------------
@router.post("/farmer/feed/follow")
def api_follow(req: FollowPayload):
    res = follow_user(req.follower_id, req.followee_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/farmer/feed/unfollow")
def api_unfollow(req: FollowPayload):
    return unfollow_user(req.follower_id, req.followee_id)

@router.get("/farmer/feed/followers/{user_id}")
def api_followers(user_id: str):
    return {"followers": list_followers(user_id)}

@router.get("/farmer/feed/following/{user_id}")
def api_following(user_id: str):
    return {"following": list_following(user_id)}

# ----------------------------
# Reporting & moderation
# ----------------------------
@router.post("/farmer/feed/report")
def api_report(req: ReportPayload):
    return report_content(req.reporter_id, req.entity_type, req.entity_id, req.reason)

@router.get("/farmer/feed/reports")
def api_list_reports(unhandled_only: bool = True):
    return {"reports": list_reports(unhandled_only=unhandled_only)}

@router.post("/farmer/feed/report/{report_id}/handle")
def api_handle_report(report_id: str, handled_by: str, action: Optional[str] = None):
    res = mark_report_handled(report_id, handled_by, action=action)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

# ----------------------------
# Search, trending, analytics
# ----------------------------
@router.get("/farmer/feed/search")
def api_search(query: Optional[str] = None, hashtag: Optional[str] = None, category: Optional[str] = None, district: Optional[str] = None, village: Optional[str] = None, limit: int = 50, offset: int = 0):
    return search_posts(query=query, hashtag=hashtag, category=category, district=district, village=village, limit=limit, offset=offset)

@router.get("/farmer/feed/trending")
def api_trending():
    return {"trending": get_trending()}

@router.get("/farmer/feed/compute_trending")
def api_compute_trending():
    return {"trending": compute_trending()}

@router.get("/farmer/feed/analytics/{post_id}")
def api_post_analytics(post_id: str):
    res = post_analytics(post_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

# ----------------------------
# Badges & feed
# ----------------------------
@router.post("/farmer/feed/badges/update/{user_id}")
def api_update_badges(user_id: str):
    return {"badges": update_badges_for_user(user_id)}

@router.get("/farmer/feed/badges/{user_id}")
def api_get_badges(user_id: str):
    return {"badges": get_badges(user_id)}

@router.get("/farmer/feed/home/{user_id}")
def api_home_feed(user_id: str, district: Optional[str] = None, village: Optional[str] = None, only_following: Optional[bool] = False, limit: int = 50, offset: int = 0, sort_by: Optional[str] = "time"):
    return feed_for_user(user_id, district=district, village=village, only_following=bool(only_following), limit=limit, offset=offset, sort_by=sort_by)
