"""
Personal read-only Reddit research tool.

This application uses Reddit's official OAuth Data API through PRAW
to retrieve a limited number of publicly available posts and comments
from specifically selected public subreddits.

The application:
- is read-only;
- does not post, comment, vote, or send messages;
- does not intentionally collect Reddit usernames;
- does not access private Reddit content;
- limits posts and comments to avoid excessive API usage.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    import praw
except ImportError:
    praw = None


# ============================================================
# Reddit OAuth configuration
# ============================================================
#
# Fill these values ONLY after Reddit grants API access.
#
# Never commit real Reddit credentials to GitHub.
#

REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""

REDDIT_USER_AGENT = (
    "windows:personal-read-only-research:v1.0 "
    "(by /u/Careless_Golf_7381)"
)


# ============================================================
# Research configuration
# ============================================================

# Search terms used for personal research.
SEARCH_QUERIES = [
    "dog heater",
]


# IMPORTANT:
# Use only specifically selected public subreddits.
#
# Do NOT use ["all"].
#
# These subreddit names should match the scope described
# in the Reddit Data Access Request.
#
# Replace these examples with the actual subreddits
# included in your application if necessary.
SUBREDDITS = [
    "dogs",
    "pets",
]


# Maximum number of posts retrieved PER QUERY / PER SUBREDDIT.
#
# A deliberately small limit is used to prevent excessive access.
MAX_POSTS_PER_QUERY = 10


# Maximum number of comments stored from each post.
MAX_COMMENTS_PER_POST = 50


# Do not recursively expand unlimited MoreComments objects.
#
# 0 means additional hidden comment branches will not be expanded.
MORE_COMMENTS_LIMIT = 0


# Reddit search settings.
POST_SORT = "relevance"

# Limit results to relatively recent discussions.
TIME_FILTER = "year"


# NSFW content is excluded.
INCLUDE_NSFW = False


# Local output file.
OUTPUT_FILENAME = "reddit_public_research.json"


# ============================================================
# Safety limits
# ============================================================

# These hard limits prevent accidental configuration of the
# application for large-scale collection.

MAX_ALLOWED_SUBREDDITS = 5
MAX_ALLOWED_POSTS_PER_QUERY = 25
MAX_ALLOWED_COMMENTS_PER_POST = 100


def utc_iso(timestamp: Any) -> str:
    """Convert Reddit UTC timestamps into ISO-8601 strings."""

    try:
        return datetime.fromtimestamp(
            float(timestamp),
            tz=timezone.utc,
        ).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def unique_strings(values: List[Any]) -> List[str]:
    """Return unique non-empty strings while preserving order."""

    result: List[str] = []
    seen: set[str] = set()

    for value in values:
        text = str(value).strip()

        if text and text not in seen:
            seen.add(text)
            result.append(text)

    return result


def validate_config() -> None:
    """
    Validate both credentials and responsible-use safeguards.

    The application intentionally rejects broad or unlimited
    configurations.
    """

    if praw is None:
        raise ValueError(
            "PRAW is not installed. Run: pip install -r requirements.txt"
        )

    if not REDDIT_CLIENT_ID.strip():
        raise ValueError(
            "REDDIT_CLIENT_ID is empty. "
            "Add credentials locally only after Reddit approves API access."
        )

    if not REDDIT_CLIENT_SECRET.strip():
        raise ValueError(
            "REDDIT_CLIENT_SECRET is empty. "
            "Add credentials locally only after Reddit approves API access."
        )

    if "YOUR_REDDIT_USERNAME" in REDDIT_USER_AGENT:
        raise ValueError(
            "Replace YOUR_REDDIT_USERNAME in REDDIT_USER_AGENT "
            "with your Reddit username."
        )

    queries = unique_strings(SEARCH_QUERIES)

    if not queries:
        raise ValueError(
            "At least one search query must be configured."
        )

    subreddits = unique_strings(SUBREDDITS)

    if not subreddits:
        raise ValueError(
            "At least one public subreddit must be configured."
        )

    normalized_subreddits = {
        subreddit.removeprefix("r/").lower()
        for subreddit in subreddits
    }

    # Explicitly prevent site-wide /r/all collection.
    if "all" in normalized_subreddits:
        raise ValueError(
            'SUBREDDITS cannot contain "all". '
            "Select specific public subreddits."
        )

    if len(subreddits) > MAX_ALLOWED_SUBREDDITS:
        raise ValueError(
            f"No more than {MAX_ALLOWED_SUBREDDITS} subreddits "
            "may be configured."
        )

    if not 1 <= MAX_POSTS_PER_QUERY <= MAX_ALLOWED_POSTS_PER_QUERY:
        raise ValueError(
            "MAX_POSTS_PER_QUERY must be between "
            f"1 and {MAX_ALLOWED_POSTS_PER_QUERY}."
        )

    if not 1 <= MAX_COMMENTS_PER_POST <= MAX_ALLOWED_COMMENTS_PER_POST:
        raise ValueError(
            "MAX_COMMENTS_PER_POST must be between "
            f"1 and {MAX_ALLOWED_COMMENTS_PER_POST}."
        )

    if MORE_COMMENTS_LIMIT < 0:
        raise ValueError(
            "MORE_COMMENTS_LIMIT cannot be negative."
        )

    if MORE_COMMENTS_LIMIT > 2:
        raise ValueError(
            "MORE_COMMENTS_LIMIT must not exceed 2."
        )

    if POST_SORT not in {
        "relevance",
        "hot",
        "top",
        "new",
        "comments",
    }:
        raise ValueError(
            "Invalid POST_SORT setting."
        )

    if TIME_FILTER not in {
        "hour",
        "day",
        "week",
        "month",
        "year",
        "all",
    }:
        raise ValueError(
            "Invalid TIME_FILTER setting."
        )


def create_reddit_client() -> Any:
    """
    Create an authenticated Reddit client.

    Explicitly configure the client as read-only.
    """

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID.strip(),
        client_secret=REDDIT_CLIENT_SECRET.strip(),
        user_agent=REDDIT_USER_AGENT.strip(),
        check_for_async=False,
    )

    reddit.read_only = True

    return reddit


def normalize_post(
    submission: Any,
    search_query: str,
) -> Dict[str, Any]:
    """
    Convert a Reddit submission into the minimal research structure.

    Reddit usernames are intentionally not collected.
    """

    permalink = str(
        getattr(submission, "permalink", "") or ""
    )

    return {
        "postId": str(
            getattr(submission, "id", "") or ""
        ),

        "url": (
            f"https://www.reddit.com{permalink}"
            if permalink
            else ""
        ),

        "title": str(
            getattr(submission, "title", "") or ""
        ),

        "subreddit": str(
            getattr(submission, "subreddit", "") or ""
        ),

        "publishedAt": utc_iso(
            getattr(submission, "created_utc", None)
        ),

        "score": int(
            getattr(submission, "score", 0) or 0
        ),

        "upvoteRatio": getattr(
            submission,
            "upvote_ratio",
            None,
        ),

        "officialCommentCount": int(
            getattr(submission, "num_comments", 0) or 0
        ),

        "bodyOriginal": str(
            getattr(submission, "selftext", "") or ""
        ),

        "matchedSearchQuery": search_query,

        "comments": [],
    }


def normalize_comment(comment: Any) -> Dict[str, Any]:
    """
    Convert a public Reddit comment into a minimal structure.

    Author usernames are intentionally excluded.
    """

    parent_fullname = str(
        getattr(comment, "parent_id", "") or ""
    )

    if parent_fullname.startswith("t1_"):
        parent_comment_id = parent_fullname.removeprefix("t1_")
    else:
        parent_comment_id = None

    edited = getattr(
        comment,
        "edited",
        False,
    )

    return {
        "commentId": str(
            getattr(comment, "id", "") or ""
        ),

        "parentCommentId": parent_comment_id,

        "depth": int(
            getattr(comment, "depth", 0) or 0
        ),

        "bodyOriginal": str(
            getattr(comment, "body", "") or ""
        ),

        "publishedAt": utc_iso(
            getattr(comment, "created_utc", None)
        ),

        "updatedAt": (
            utc_iso(edited)
            if edited not in (False, None)
            else ""
        ),

        "score": int(
            getattr(comment, "score", 0) or 0
        ),
    }


def deduplicate_comments(
    comments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove duplicate comments by Reddit comment ID."""

    result: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for comment in comments:

        comment_id = str(
            comment.get("commentId", "")
        )

        if not comment_id:
            continue

        if comment_id in seen_ids:
            continue

        seen_ids.add(comment_id)
        result.append(comment)

    return result


def search_posts(
    reddit: Any,
    subreddit_name: str,
    search_query: str,
) -> List[Dict[str, Any]]:
    """
    Search a limited number of public posts from one selected subreddit.
    """

    normalized_name = subreddit_name.removeprefix("r/")

    subreddit = reddit.subreddit(
        normalized_name
    )

    listing = subreddit.search(
        query=search_query,
        sort=POST_SORT,
        time_filter=TIME_FILTER,
        limit=MAX_POSTS_PER_QUERY,
    )

    posts: List[Dict[str, Any]] = []

    seen_ids: set[str] = set()

    for submission in listing:

        post_id = str(
            getattr(submission, "id", "") or ""
        )

        if not post_id:
            continue

        if post_id in seen_ids:
            continue

        if (
            not INCLUDE_NSFW
            and bool(
                getattr(
                    submission,
                    "over_18",
                    False,
                )
            )
        ):
            continue

        seen_ids.add(post_id)

        posts.append(
            normalize_post(
                submission,
                search_query,
            )
        )

    return posts


def fetch_post_comments(
    reddit: Any,
    post_id: str,
) -> List[Dict[str, Any]]:
    """
    Retrieve a limited number of public comments.

    Unlimited comment expansion is intentionally disabled.
    """

    submission = reddit.submission(
        id=post_id
    )

    # Do not recursively expand unlimited comment branches.
    submission.comments.replace_more(
        limit=MORE_COMMENTS_LIMIT
    )

    comments: List[Dict[str, Any]] = []

    for comment in submission.comments.list():

        # Extra defensive check.
        if not hasattr(comment, "body"):
            continue

        comments.append(
            normalize_comment(comment)
        )

        if (
            len(comments)
            >= MAX_COMMENTS_PER_POST
        ):
            break

    return deduplicate_comments(
        comments
    )


def collect_research_data(
    reddit: Any,
) -> Dict[str, Any]:
    """
    Perform the complete limited read-only collection.
    """

    queries = unique_strings(
        SEARCH_QUERIES
    )

    subreddits = [
        name.removeprefix("r/")
        for name in unique_strings(SUBREDDITS)
    ]

    posts_by_id: Dict[
        str,
        Dict[str, Any],
    ] = {}

    for subreddit_index, subreddit_name in enumerate(
        subreddits,
        start=1,
    ):

        print(
            f"Subreddit "
            f"[{subreddit_index}/{len(subreddits)}]: "
            f"r/{subreddit_name}"
        )

        for query_index, query in enumerate(
            queries,
            start=1,
        ):

            print(
                f"  Query "
                f"[{query_index}/{len(queries)}]: "
                f"{query}"
            )

            posts = search_posts(
                reddit,
                subreddit_name,
                query,
            )

            for post in posts:

                post_id = post["postId"]

                # The same post may appear under more than one query.
                # Keep only one copy.
                if post_id in posts_by_id:
                    continue

                try:
                    post["comments"] = (
                        fetch_post_comments(
                            reddit,
                            post_id,
                        )
                    )

                except Exception as exc:

                    print(
                        f"  Warning: unable to retrieve comments "
                        f"for post {post_id}: "
                        f"{type(exc).__name__}"
                    )

                    post["comments"] = []

                posts_by_id[post_id] = post

    posts = list(
        posts_by_id.values()
    )

    total_comments = sum(
        len(
            post.get(
                "comments",
                [],
            )
        )
        for post in posts
    )

    return {
        "purpose": (
            "Personal read-only research using "
            "public Reddit content"
        ),

        "fetchedAt": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "searchQueries": queries,

        "subreddits": subreddits,

        "limits": {
            "maxPostsPerQueryPerSubreddit":
                MAX_POSTS_PER_QUERY,

            "maxCommentsPerPost":
                MAX_COMMENTS_PER_POST,

            "moreCommentsExpansionLimit":
                MORE_COMMENTS_LIMIT,
        },

        "totalPostCount": len(posts),

        "totalCollectedCommentCount":
            total_comments,

        "posts": posts,
    }


def save_output(
    path: Path,
    output: Dict[str, Any],
) -> None:
    """
    Save research data locally.

    Existing output is replaced instead of being accumulated
    indefinitely across runs.
    """

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )


def main() -> int:
    try:

        validate_config()

        reddit = create_reddit_client()

        print(
            "Starting limited read-only Reddit research collection."
        )

        output = collect_research_data(
            reddit
        )

        output_path = (
            Path(__file__).resolve().parent
            / OUTPUT_FILENAME
        )

        save_output(
            output_path,
            output,
        )

        print()
        print(
            f"Saved posts: "
            f"{output['totalPostCount']}"
        )

        print(
            f"Saved comments: "
            f"{output['totalCollectedCommentCount']}"
        )

        print(
            f"Output: {output_path}"
        )

        return 0

    except ValueError as exc:

        print(
            f"Configuration error: {exc}",
            file=sys.stderr,
        )

        return 1

    except Exception as exc:

        print(
            f"Unexpected error: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
