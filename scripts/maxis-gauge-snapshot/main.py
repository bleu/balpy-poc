import asyncio
import json
import math
from datetime import datetime
from time import time

from balpy.chains import Chain
from balpy.contracts import BalancerContractFactory
from snapshot import Snapshot

SNAPSHOT_TITLE_TEMPLATE = "Optimistic Gauge Addition Veto Vote for {}-W{}"
SNAPSHOT_DEFAULT_DESCRIPTION = "200k veBAL required to veto Optimistic gauge addition, signal for as many gauges as you don't want."


class MissingGaugeData(Exception):
    pass


class KilledGaugeException(Exception):
    pass


async def fetch_gauge_data(_chain, _gauge_address):
    mainnet_gauge = BalancerContractFactory.create(Chain.mainnet, _gauge_address)
    cap = await mainnet_gauge.getRelativeWeightCap()
    cap_pct = cap / 1e18

    if await mainnet_gauge.is_killed():
        raise KilledGaugeException(f"Gauge {_gauge_address} is killed")

    chain_gauge_addr = await mainnet_gauge.getRecipient()
    chain_gauge = BalancerContractFactory.create(Chain[_chain], chain_gauge_addr)

    return {
        "name": await chain_gauge.name(),
        "cap": f"{cap_pct:.0%}",
        "link": "https://example-link.com/BGR-001",
    }


def read_file(filename, raise_on_missing=False):
    # first check if file exists
    from pathlib import Path

    if not Path(filename).is_file():
        if raise_on_missing:
            raise FileNotFoundError(f"File {filename} not found")
        return None
    else:
        with open(filename, "r") as file:
            return file.read()


def get_proposal_idx(idx):
    return f"BGR-{idx}"


def format_choice_text(idx, name, chain, cap):
    return "{}: {} - {} - {}".format(get_proposal_idx(idx), name, chain, cap)


async def generate_snapshot_json():
    year, week, *_ = datetime.now().isocalendar()
    title = SNAPSHOT_TITLE_TEMPLATE.format(year, week)
    gauges = []

    with open("demo/checkpointer_gauges_by_chain.json", "r") as file:
        gauge_data_by_chain = json.load(file)

    gauge_adds = [
        (chain, address)
        for chain, addresses in gauge_data_by_chain.items()
        for address in addresses
    ]

    gauge_adds_data = await asyncio.gather(
        *[fetch_gauge_data(chain, address) for chain, address in gauge_adds]
    )

    for idx, ((chain, address), gauge_data) in enumerate(
        zip(gauge_adds, gauge_adds_data)
    ):
        name, cap = gauge_data["name"], gauge_data["cap"]

        if not name or not cap:
            raise MissingGaugeData(f"Missing data for gauge {(chain, address)}")

        choice = {
            "text": format_choice_text(idx, name, chain, cap),
            "link": gauge_data.get("link"),
        }
        gauges.append(choice)

    header_md = read_file("header.md")
    footer_md = read_file("footer.md")

    body = (
        f"{header_md}\n\n{footer_md}"
        if header_md and footer_md
        else SNAPSHOT_DEFAULT_DESCRIPTION
    )

    snapshot_json = {
        "title": title,
        "body": body,
        "gauges": gauges,
        "choices": [choice["text"] for choice in gauges],
    }

    return snapshot_json


def generate_snapshot_md(snapshot_json):
    MD_GAUGES_HEADER = "Gauges listed:\n"

    choices_md = "\n".join(
        f"- {'[' + choice['text'] + '](' + choice['link'] + ')'}"
        if "link" in choice
        else "- " + choice["text"]
        for choice in snapshot_json["gauges"]
    )

    return f"{snapshot_json['body']}\n\n{MD_GAUGES_HEADER}\n{choices_md}"


async def create_snapshot_proposal(data):
    START = math.floor(time())
    snapshot = Snapshot("https://seq.snapshot.org", Chain.mainnet)

    proposal_data = {
        "title": data["title"],
        "body": generate_snapshot_md(data),
        "choices": data["choices"],
        "space": "joferi.eth",
        "type": "approval",
        "start": START,
        "end": START + 60 * 60 * 24 * 7,  # 7 days
        "snapshot": await snapshot.w3.eth.get_block_number(),
        "network": "1",
        "plugins": "{}",
        "app": "gauges-integration",
    }

    await snapshot.proposal(proposal_data)


async def main():
    snapshot_json = await generate_snapshot_json()

    await create_snapshot_proposal(snapshot_json)

    with open("demo/weekly_veto_snapshot.json", "w") as json_file:
        json.dump(snapshot_json, json_file, indent=4)

    snapshot_md = generate_snapshot_md(snapshot_json)
    with open("demo/weekly_veto_snapshot.md", "w") as md_file:
        md_file.write(snapshot_md)

    print(
        "Weekly Veto Snapshot generated and saved as weekly_veto_snapshot.json and weekly_veto_snapshot.md"
    )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
