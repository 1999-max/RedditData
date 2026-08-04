"""按关键词搜索 Reddit 公开帖子，并获取每个帖子的全部公开评论。"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import praw
except ImportError:
    praw = None


# ========================= 请求参数（请从这里修改） =========================

# 申请获批并创建 OAuth 应用后填写。不要把真实凭据上传到 GitHub。
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""
REDDIT_USER_AGENT = (
    "windows:personal-public-comment-collector:v1.0 "
    "(by /u/YOUR_REDDIT_USERNAME)"
)

SEARCH_QUERIES = [
    "dog heater",
    # "dog house heater",
    # "pet house heater",
]

# 使用 ["all"] 搜索全部公开社区；也可以指定 ["dogs", "pets"]。
SUBREDDITS = ["all"]
MAX_POSTS_PER_QUERY = 20
POST_SORT = "relevance"       # relevance、hot、top、new、comments
TIME_FILTER = "all"           # all、hour、day、week、month、year
INCLUDE_NSFW = False

FETCH_ALL_COMMENTS = True      # True=展开每篇帖子的全部可用评论
MORE_COMMENTS_LIMIT = None     # None=不限制 MoreComments 展开次数
MAX_COMMENTS_PER_POST: Optional[int] = None  # None=不限制

SKIP_EXISTING_POSTS = True     # True=已有成功帖子不重复请求评论
OUTPUT_FILENAME = "reddit_search_comments.json"

# ===========================================================================


def utc_iso(timestamp: Any) -> str:
    try:
        return datetime.fromtimestamp(
            float(timestamp), tz=timezone.utc
        ).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def unique_strings(values: List[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def validate_config() -> None:
    if praw is None:
        raise ValueError("缺少 praw，请先运行：pip install -r requirements.txt")
    if not REDDIT_CLIENT_ID.strip() or not REDDIT_CLIENT_SECRET.strip():
        raise ValueError(
            "当前是等待 Reddit API 审核的代码原型。获批后请在脚本顶部填写 "
            "REDDIT_CLIENT_ID 和 REDDIT_CLIENT_SECRET。"
        )
    if "YOUR_REDDIT_USERNAME" in REDDIT_USER_AGENT:
        raise ValueError("请把 REDDIT_USER_AGENT 中的用户名改成你的 Reddit 用户名。")
    if not any(query.strip() for query in SEARCH_QUERIES):
        raise ValueError("SEARCH_QUERIES 至少需要一个搜索词。")
    if not any(subreddit.strip() for subreddit in SUBREDDITS):
        raise ValueError("SUBREDDITS 至少需要一个社区名称或 all。")
    if MAX_POSTS_PER_QUERY < 1:
        raise ValueError("MAX_POSTS_PER_QUERY 必须大于 0。")
    if POST_SORT not in {"relevance", "hot", "top", "new", "comments"}:
        raise ValueError("POST_SORT 参数不正确。")
    if TIME_FILTER not in {"all", "hour", "day", "week", "month", "year"}:
        raise ValueError("TIME_FILTER 参数不正确。")


def create_reddit_client() -> Any:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID.strip(),
        client_secret=REDDIT_CLIENT_SECRET.strip(),
        user_agent=REDDIT_USER_AGENT.strip(),
        check_for_async=False,
    )


def subreddit_scope() -> str:
    names = unique_strings(SUBREDDITS)
    if "all" in {name.lower() for name in names}:
        return "all"
    return "+".join(name.removeprefix("r/") for name in names)


def normalize_post(submission: Any, search_query: str) -> Dict[str, Any]:
    permalink = str(getattr(submission, "permalink", ""))
    return {
        "postId": str(getattr(submission, "id", "")),
        "url": f"https://www.reddit.com{permalink}" if permalink else "",
        "title": str(getattr(submission, "title", "")),
        "subreddit": str(getattr(submission, "subreddit", "")),
        "authorDisplayName": (
            str(submission.author) if getattr(submission, "author", None) else "[deleted]"
        ),
        "publishedAt": utc_iso(getattr(submission, "created_utc", None)),
        "score": int(getattr(submission, "score", 0) or 0),
        "upvoteRatio": getattr(submission, "upvote_ratio", None),
        "officialCommentCount": int(getattr(submission, "num_comments", 0) or 0),
        "bodyOriginal": str(getattr(submission, "selftext", "") or ""),
        "matchedSearchQueries": [search_query],
        "comments": [],
        "error": None,
    }


def search_posts(reddit: Any, search_query: str) -> List[Dict[str, Any]]:
    posts: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    listing = reddit.subreddit(subreddit_scope()).search(
        query=search_query,
        sort=POST_SORT,
        time_filter=TIME_FILTER,
        limit=MAX_POSTS_PER_QUERY,
    )
    for submission in listing:
        post_id = str(getattr(submission, "id", ""))
        if not post_id or post_id in seen_ids:
            continue
        if not INCLUDE_NSFW and bool(getattr(submission, "over_18", False)):
            continue
        seen_ids.add(post_id)
        posts.append(normalize_post(submission, search_query))
    return posts


def normalize_comment(comment: Any) -> Dict[str, Any]:
    parent_fullname = str(getattr(comment, "parent_id", ""))
    parent_comment_id = (
        parent_fullname.removeprefix("t1_")
        if parent_fullname.startswith("t1_")
        else None
    )
    edited = getattr(comment, "edited", False)
    return {
        "commentId": str(getattr(comment, "id", "")),
        "parentCommentId": parent_comment_id,
        "depth": int(getattr(comment, "depth", 0) or 0),
        "bodyOriginal": str(getattr(comment, "body", "") or ""),
        "publishedAt": utc_iso(getattr(comment, "created_utc", None)),
        "updatedAt": utc_iso(edited) if edited not in (False, None) else "",
        "score": int(getattr(comment, "score", 0) or 0),
        "authorDisplayName": (
            str(comment.author) if getattr(comment, "author", None) else "[deleted]"
        ),
    }


def deduplicate_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for comment in comments:
        comment_id = str(comment.get("commentId", ""))
        if comment_id and comment_id not in seen_ids:
            seen_ids.add(comment_id)
            result.append(comment)
    return result


def fetch_post_comments(reddit: Any, post_id: str) -> List[Dict[str, Any]]:
    submission = reddit.submission(id=post_id)
    if FETCH_ALL_COMMENTS:
        submission.comments.replace_more(limit=MORE_COMMENTS_LIMIT)
    comments: List[Dict[str, Any]] = []
    for comment in submission.comments.list():
        comments.append(normalize_comment(comment))
        if (
            MAX_COMMENTS_PER_POST is not None
            and len(comments) >= MAX_COMMENTS_PER_POST
        ):
            break
    return deduplicate_comments(comments)


def compact_post(post: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "postId": post.get("postId", ""),
        "url": post.get("url", ""),
        "title": post.get("title", ""),
        "subreddit": post.get("subreddit", ""),
        "authorDisplayName": post.get("authorDisplayName", ""),
        "publishedAt": post.get("publishedAt", ""),
        "score": post.get("score", 0),
        "upvoteRatio": post.get("upvoteRatio"),
        "officialCommentCount": post.get("officialCommentCount", 0),
        "bodyOriginal": post.get("bodyOriginal", ""),
        "matchedSearchQueries": unique_strings(
            list(post.get("matchedSearchQueries", []))
        ),
        "comments": deduplicate_comments(list(post.get("comments", []))),
        "error": post.get("error"),
    }


def merge_posts(saved: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    merged = {**saved, **new}
    merged["matchedSearchQueries"] = unique_strings(
        list(saved.get("matchedSearchQueries", []))
        + list(new.get("matchedSearchQueries", []))
    )
    merged["comments"] = deduplicate_comments(
        list(saved.get("comments", [])) + list(new.get("comments", []))
    )
    return compact_post(merged)


def deduplicate_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for position, post in enumerate(posts):
        post = compact_post(post)
        post_id = str(post.get("postId") or f"__missing_post_id_{position}")
        if post_id not in by_id:
            by_id[post_id] = post
            order.append(post_id)
        else:
            by_id[post_id] = merge_posts(by_id[post_id], post)
    return [by_id[post_id] for post_id in order]


def load_existing_output(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"posts": [], "collectionHistory": []}
    try:
        output = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取已有JSON文件：{exc}") from exc
    if not isinstance(output, dict) or not isinstance(output.get("posts", []), list):
        raise ValueError("已有JSON格式不正确：缺少 posts 数组。")
    output["posts"] = deduplicate_posts(output.get("posts", []))
    if not isinstance(output.get("collectionHistory"), list):
        output["collectionHistory"] = []
    return output


def save_output(path: Path, output: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    try:
        validate_config()
        started_at = datetime.now(timezone.utc).isoformat()
        output_path = Path(__file__).resolve().parent / OUTPUT_FILENAME
        existing = load_existing_output(output_path)
        saved_posts = existing.get("posts", [])
        saved_by_id = {
            str(post.get("postId")): post
            for post in saved_posts
            if post.get("postId")
        }

        reddit = create_reddit_client()
        queries = unique_strings(SEARCH_QUERIES)
        candidates: Dict[str, Dict[str, Any]] = {}
        skipped_ids: set[str] = set()
        raw_result_count = 0

        for index, query in enumerate(queries, start=1):
            print(f"搜索词 [{index}/{len(queries)}]：{query}")
            for post in search_posts(reddit, query):
                raw_result_count += 1
                post_id = str(post["postId"])
                if (
                    SKIP_EXISTING_POSTS
                    and post_id in saved_by_id
                    and not saved_by_id[post_id].get("error")
                ):
                    saved_by_id[post_id]["matchedSearchQueries"] = unique_strings(
                        list(saved_by_id[post_id].get("matchedSearchQueries", []))
                        + [query]
                    )
                    skipped_ids.add(post_id)
                elif post_id in candidates:
                    candidates[post_id]["matchedSearchQueries"] = unique_strings(
                        list(candidates[post_id].get("matchedSearchQueries", []))
                        + [query]
                    )
                else:
                    candidates[post_id] = post

        new_posts: List[Dict[str, Any]] = []
        candidate_posts = list(candidates.values())
        print(
            f"搜索结果 {raw_result_count} 个，去重后新增候选 {len(candidate_posts)} 个；"
            f"跳过已有帖子 {len(skipped_ids)} 个。"
        )

        for index, post in enumerate(candidate_posts, start=1):
            print(f"[{index}/{len(candidate_posts)}] {post['title']}")
            try:
                post["comments"] = fetch_post_comments(reddit, post["postId"])
                post["error"] = None
            except Exception as exc:
                post["comments"] = []
                post["error"] = f"{type(exc).__name__}: {exc}"
            new_posts.append(compact_post(post))

        all_posts = deduplicate_posts(saved_posts + new_posts)
        total_comments = sum(len(post.get("comments", [])) for post in all_posts)
        new_comments = sum(len(post.get("comments", [])) for post in new_posts)
        finished_at = datetime.now(timezone.utc).isoformat()

        history = list(existing.get("collectionHistory", []))
        history.append(
            {
                "startedAt": started_at,
                "finishedAt": finished_at,
                "searchQueries": queries,
                "subreddits": unique_strings(SUBREDDITS),
                "requestedPostCountPerQuery": MAX_POSTS_PER_QUERY,
                "searchResultCount": raw_result_count,
                "newUniquePostCount": len(new_posts),
                "skippedExistingPostCount": len(skipped_ids),
                "newCollectedCommentCount": new_comments,
            }
        )

        output = {
            "searchQueries": unique_strings(
                list(existing.get("searchQueries", [])) + queries
            ),
            "lastFetchedAt": finished_at,
            "subreddits": unique_strings(SUBREDDITS),
            "totalPostCount": len(all_posts),
            "totalCollectedCommentCount": total_comments,
            "collectionHistory": history,
            "posts": all_posts,
        }
        save_output(output_path, output)

        print(f"本次新增：{len(new_posts)} 个帖子、{new_comments} 条评论")
        print(f"累计保存：{len(all_posts)} 个帖子、{total_comments} 条评论")
        print(f"JSON 文件：{output_path}")
        return 0
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
