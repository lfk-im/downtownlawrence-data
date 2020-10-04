import click
import frontmatter
import os
import re
import requests
import sys
import yaml

from bs4 import BeautifulSoup
from click_default_group import DefaultGroup
from pathlib import Path
from slugify import slugify
from typesystem.fields import Boolean


Boolean.coerce_values.update({"n": False, "no": False, "y": True, "yes": True})

CUISINE_INITIAL = [
    "American",
    "Asian",
    "Bakeries",
    "Bar & Grill",
    "Barbecue",
    "Bars",
    "Breakfast",
    "Breweries",
    "Burgers",
    "Butcher",
    "Cajun",
    "Chinese",
    "Coffee and Tea",
    "Deli",
    "Desserts",
    "Ethiopian",
    "Fast Food",
    "Fine Dining",
    "Fried Chicken",
    "Greek",
    "Homestyle Cookin'",
    "Ice Cream / Juice",
    "Indian",
    "Italian",
    "Japanese",
    "Korean",
    "Latin American",
    "Mexican",
    "Middle-Eastern",
    "Pizza",
    "Sandwiches/Subs",
    "Seafood",
    "Spanish",
    "Steakhouse",
    "Sushi",
    "Thai",
]

CUISINE_INITIAL_SLUGS = [slugify(cuisine) for cuisine in CUISINE_INITIAL]

# Don't customize these
EXPECTED_ENV_VARS = [
    "LFK_GOOGLE_SHEET_APP_ID",
    "SHEETFU_CONFIG_AUTH_PROVIDER_URL",
    "SHEETFU_CONFIG_AUTH_URI",
    "SHEETFU_CONFIG_CLIENT_CERT_URL",
    "SHEETFU_CONFIG_CLIENT_EMAIL",
    "SHEETFU_CONFIG_CLIENT_ID",
    "SHEETFU_CONFIG_PRIVATE_KEY",
    "SHEETFU_CONFIG_PRIVATE_KEY_ID",
    "SHEETFU_CONFIG_PROJECT_ID",
    "SHEETFU_CONFIG_TOKEN_URI",
    "SHEETFU_CONFIG_TYPE",
]

# Feel free to customie everything below here

SHEETS_BOOL_FIELDS = [
    "active",
    "curbside",
    "delivery",
    "dinein",
    "featured",
    "giftcard",
    "takeout",
]

SHEETS_STRING_FIELDS = [
    "name",
    "address",
    "place_type",
    "cuisine",
    "curbside_instructions",
    "giftcard_notes",
    "hours",
    "locality",
    "neighborhood",
    "notes",
    "region",
    "restaurant_phone",
]

SHEETS_URL_FIELDS = [
    "delivery_service_websites",
    "facebook_url",
    "giftcard_url",
    "instagram_url",
    "twitch_url",
    "twitter_url",
    "website",
]

FOOD_SERVICE_DICT = {
    # "chownow_url": "ChowNow",
    # "doordash_url": "DoorDash",
    # "eatstreet_url": "EatStreet",
    # "grubhub_url": "Grubhub",
    # "postmates_url": "Postmates",
    # "seamless_url": "Seamless",
    # "ubereats_url": "Ubereats",
    "chownow_url": "chownow.com",
    "doordash_url": "doordash.com",
    "eatstreet_url": "eatstreet.com",
    "grubhub_url": "grubhub.com",
    "postmates_url": "postmates.com",
    "seamless_url": "seamless.com",
    "ubereats_url": "ubereats.com",
}

FOOD_SERVICE_URLS = [
    "chownow_url",
    "doordash_url",
    "eatstreet_url",
    "grubhub_url",
    "postmates_url",
    "seamless_url",
    "ubereats_url",
]


def load_aliases():
    if Path("_data", "aliases.yml").exists():
        input_file = Path("_data", "aliases.yml").read_text()
        data = yaml.load(input_file, Loader=yaml.FullLoader)
    else:
        data = dict()
    return data


def aliases_to_cuisine():
    aliases = load_aliases()

    data = {}
    cuisines = aliases["cuisines"]
    for cuisine in cuisines:
        cuisine_aliases = cuisine["aliases"]
        if len(cuisine_aliases):
            for cuisine_alias in cuisine_aliases:
                data[cuisine_alias] = cuisine["name"]
    return data


def string_to_boolean(value):
    validator = Boolean()
    value, error = validator.validate_or_error(value)

    if value is None:
        return False
    else:
        return value


def verify_http(value):
    if not value or value.startswith("http"):
        return value
    return f"https://{value}"


def print_expected_env_variables():
    click.echo(
        """
To use this command, you will need to setup a Google Cloud Project and have
authentication properly setup. To start, check out:

> https://github.com/socialpoint-labs/sheetfu/blob/master/documentation/authentication.rst

Once you have your your seceret JSON file, you'll want to convert the key/value
pairs in this file into ENV variables or SECRETS if you want to run this script
as a GitHub Action.

These are the values that you need to configure for the script to run:
"""
    )

    for var in EXPECTED_ENV_VARS:
        if var not in os.environ or not os.environ.get(var):
            click.echo(f"- {var}")

    click.echo("")


@click.group(cls=DefaultGroup, default="sync-downtownlawrence", default_if_no_args=True)
def cli():
    pass


@cli.command()
def sync_downtownlawrence():
    click.echo("sync-downtownlawrence")

    if not Path("_places").exists():
        Path("_places").mkdir()

    response = requests.get(
        "https://www.downtownlawrence.com/explore-downtown-lawrence/dining/"
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("div", "entry-content")
    rows = table.find_all("p")
    click.secho(f"Businesses found: {len(rows)}", fg="yellow")

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

                click.secho(f"{name} [{place_slug}]", fg="green")

                try:
                    facebook_url = [item.get('href') for item in row.find_all(href=re.compile("facebook"))][0]
                    print(facebook_url)
                except IndexError:
                    facebook_url = None

                url = row.find("a")
                url = url.get("href") if url else None
                if url:
                    if url.startswith("http://"):
                        url = url.replace("http://", "https://")
                    if "facebook.com" in url:
                        url = None
                    click.echo(url)

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
                click.secho(e, fg="red")
                print(row)


if __name__ == "__main__":
    cli()
