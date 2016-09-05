import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from bokeh.charts import output_file, Chord
from bokeh.io import show
import logging as lg


def get_links():
    """Get all links from main page."""
    lg.info("Getting links ...")

    # Scrape link info from main url using Requests/BeautifulSoup
    url = "https://www.govtrack.us/data/congress/113/bills/s/"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    tags = soup.findAll('a', href=True)

    links = list()

    # Get link by tag 'href' that starts with 's' (indicates senate record) and append to scrape list
    for tag in tags:
        x = tag.get("href", None)
        if x.startswith('s'):
            links.append(x)

    # Get single vote data for each of the first 10 links
    # NOTE: Truncated to first ten links for demo, assumed you wouldn't want to wait for 3,020 links to scrape
    votes = [get_single_vote(link) for link in links[:10]]

    return votes


def get_single_vote(vote_href):
    """Scrape one link's JSON data."""
    # Url to scrape
    url = "http://www.govtrack.us/data/congress/113/bills/s/{}data.json".format(vote_href)

    # Get page text
    page = requests.get(url).text
    lg.info("Scraping data from: {}".format(url))

    # Return loaded into json
    return json.loads(page)


def filter_json_to_frame(rows):
    """Turn JSON file into DataFrame."""
    lg.info("Converting Jsons to DataFrame ...")

    # Convert json to a Pandas DataFrame, listing main sponsor, all co-sponsors, and the bill id number
    df = pd.DataFrame.from_records(
        ((r["sponsor"]["name"],
         [r["cosponsors"][i]["name"] for i in range(len(r["cosponsors"]))], r["bill_id"]) for r in rows),
        columns=["Sponsor", "Cosponsor", "Bill"])
    return df


def create_vertex_and_chord_lists(d_frame):
    """Create vertex and chord data from DataFrame."""
    lg.info("Creating vertex and edge lists ...")
    li = list()
    for en in d_frame["Cosponsor"]:
        li.extend(en)

    # Partition all sponsor entries in DataFrame and sorts them into a list
    y_labels = sorted(set(d_frame["Sponsor"]), key=lambda item: (int(item.partition(' ')[0])
                      if item[0].isdigit() else float("inf"), item))

    # Partition all co-sponsor entries in DataFrame and sort into a list
    x_labels = sorted(set(li), key=lambda item: (int(item.partition(' ')[0])
                      if item[0].isdigit() else float("inf"), item))

    # Create sorted union set of all sponsors and co-sponsors, will be used as vertex list
    union_labels = sorted(set(x_labels + y_labels), key=lambda item: (int(item.partition(' ')[0])
                          if item[0].isdigit() else float("inf"), item))

    # Put union set into new dict, list of vertices
    vert_list = [{'group': 0, 'name': label} for label in union_labels]

    # Create empty dict to hold list of Chord links
    chord_list = []

    # Get sponsors and list of co-sponsors from DataFrame
    for i in range(len(d_frame["Sponsor"])):
        y_lookup = d_frame.ix[i, "Sponsor"]
        x_list = d_frame.ix[i, "Cosponsor"]

        # For each sponsor, pair them with their co-sponsors
        for x_lookup in x_list:
            # Index lookup for chart data
            source_ind = union_labels.index(y_lookup)
            target_ind = union_labels.index(x_lookup)
            # Append chord pair to dict
            chord_list.append({"source": source_ind, "target": target_ind, "value": 1})

    return vert_list, chord_list


def plot_chord_chart(nodes, links):
    """Plot a chord chart."""
    lg.info("Plotting chart ...")
    # Turn dict of vertices and chords into DataFrames
    nodes_df = pd.DataFrame(nodes)
    links_df = pd.DataFrame(links)

    # Merge DataFrames into source data
    source_data = links_df.merge(nodes_df, how="left", left_on="source", right_index=True)
    source_data = source_data.merge(nodes_df, how="left", left_on="target", right_index=True)

    # Create chord chart
    chord_from_df = Chord(source_data, source="name_x", target="name_y", value="value")

    # Create chord chart file as html
    output_file("chord_from_df.html", mode="inline")

    # Show chart
    show(chord_from_df)

if __name__ == "__main__":
    # Set logging to INFO level
    lg.basicConfig(level=lg.INFO, format="%(levelname)s - %(message)s")

    # Suppress info logging level from requests library
    lg.getLogger("requests").setLevel(lg.WARNING)

    # Get links
    vote_data = get_links()

    # Make DataFrame
    p_data = filter_json_to_frame(vote_data)

    # Get list of vertices and chords
    v_list, e_list = create_vertex_and_chord_lists(p_data)

    # Plot chart
    plot_chord_chart(v_list, e_list)
