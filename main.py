import frontmatter
import re
import requests
import sys
import typer

from bs4 import BeautifulSoup
from pathlib import Path
from slugify import slugify


URL = "https://www.downtownlawrence.com/explore-downtown-lawrence/dining/"


app = typer.Typer()


@app.command()
def sync_downtownlawrence(mark_inactive: bool = False, use_cache: bool = False):
    if not Path("_places").exists():
        Path("_places").mkdir()

    if mark_inactive:
        filenames = Path("_places").glob("*.md")
        for filename in filenames:
            post = frontmatter.loads(filename.read_text())
            post["active"] = False

            filename.write_text(frontmatter.dumps(post))

    if use_cache:
        cache_filename = f"{slugify(URL)}.html"
        if Path(cache_filename).exists():
            text = Path(cache_filename).read_text()
        else:
            response = requests.get(URL)
            response.raise_for_status()
            text = response.text
            text = Path(cache_filename).write_text(text)
    else:
        response = requests.get(URL)
        response.raise_for_status()
        text = response.text

    soup = BeautifulSoup(text, "html.parser")

    table = soup.find("div", "entry-content")
    rows = table.find_all("p")
    typer.secho(f"Businesses found: {len(rows)}", fg="yellow")

    for row in rows[3:]:
        if len(row.text.strip()):
            try:
                tokens = row.find_all(recursive=False)
                # print(tokens)
                # print(row.text.replace("\xa0", "\n").split("\n"))
                name = tokens[0]
                name = name.text.strip()
                # name, address, services = row.find_all("td")
                place_slug = slugify(name)

                typer.secho(f"{name} [{place_slug}]", fg="green")

                try:
                    facebook_url = [
                        item.get("href")
                        for item in row.find_all(href=re.compile("facebook"))
                    ][0]
                    print(facebook_url)
                except IndexError:
                    facebook_url = ""

                url = row.find("a")
                url = url.get("href") if url else ""
                if url:
                    if url.startswith("http"):
                        if url.startswith("http://"):
                            url = url.replace("http://", "https://")
                    else:
                        url = f"https://{url}"

                    if "facebook.com" in url:
                        url = ""

                    typer.echo(url)

                filename = Path("_places").joinpath(f"{place_slug}.md")
                if filename.exists():
                    post = frontmatter.loads(filename.read_text())
                else:
                    post = frontmatter.loads("")

                post["active"] = False if "Closed" in row.text else True
                # post["address"] = address.text
                post["name"] = name
                post["facebook_url"] = facebook_url
                post["neighborhood"] = "Downtown"
                # post["notes"] = services.text
                post["sitemap"] = False
                post["slug"] = place_slug
                post["url"] = url

                Path("_places").joinpath(f"{place_slug}.md").write_text(
                    frontmatter.dumps(post)
                )
                print("")

            except (IndexError, ValueError) as e:
                typer.secho(e, fg="red")
                print(row)


if __name__ == "__main__":
    app()
