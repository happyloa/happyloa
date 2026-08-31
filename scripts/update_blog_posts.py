from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
import html
import re
import xml.etree.ElementTree as ET

RSS_URL = "https://blog.worksbyaaron.com/rss.xml"
README_PATH = Path("README.md")
START_MARKER = "<!-- BLOG-POST-LIST:START -->"
END_MARKER = "<!-- BLOG-POST-LIST:END -->"
MAX_POSTS = 2


def fetch_rss() -> bytes:
    request = Request(
        RSS_URL,
        headers={
            "User-Agent": "happyloa-github-profile-updater/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read()


def text_of(parent: ET.Element, tag: str) -> str:
    node = parent.find(tag)
    return (node.text or "").strip() if node is not None else ""


def parse_date(value: str) -> datetime:
    if not value:
        return datetime.min

    try:
        return parsedate_to_datetime(value).replace(tzinfo=None)
    except (TypeError, ValueError):
        pass

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def markdown_escape_title(title: str) -> str:
    title = html.unescape(title)
    return title.replace("[", "\\[").replace("]", "\\]")


def get_latest_posts(xml_bytes: bytes) -> list[dict[str, str | datetime]]:
    root = ET.fromstring(xml_bytes)
    items = root.findall("./channel/item")

    posts: list[dict[str, str | datetime]] = []
    for item in items:
        title = text_of(item, "title")
        link = text_of(item, "link")
        pub_date_raw = text_of(item, "pubDate")

        if not title or not link:
            continue

        posts.append(
            {
                "title": markdown_escape_title(title),
                "link": link,
                "published": parse_date(pub_date_raw),
            }
        )

    posts.sort(key=lambda post: post["published"], reverse=True)
    return posts[:MAX_POSTS]


def render(posts: list[dict[str, str | datetime]]) -> str:
    lines: list[str] = []
    for post in posts:
        published = post["published"]
        if isinstance(published, datetime) and published != datetime.min:
            date_text = published.strftime("%Y-%m-%d")
        else:
            date_text = "Latest"

        lines.append(f'- **{date_text}** · [{post["title"]}]({post["link"]})')

    return "\n".join(lines)


def update_readme(rendered_posts: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )

    replacement = f"{START_MARKER}\n{rendered_posts}\n{END_MARKER}"

    if not pattern.search(readme):
        raise RuntimeError("Blog post markers were not found in README.md")

    updated = pattern.sub(replacement, readme)
    README_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    posts = get_latest_posts(fetch_rss())
    if not posts:
        raise RuntimeError("No blog posts found in RSS feed")

    update_readme(render(posts))
    print(f"Updated README with {len(posts)} latest blog posts.")


if __name__ == "__main__":
    main()
