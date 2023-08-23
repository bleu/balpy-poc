import asyncio
import logging
from typing import List

from balpy.chains import Chain
from balpy.core.lib.web3_provider import Web3Provider
from balpy.core.utils import get_explorer_link
from dotenv import load_dotenv
from eth_abi import abi
from web3._utils.filters import AsyncFilter
from web3.types import LogEntry

from .config import (
    EVENT_TYPE_TO_INDEXED_PARAMS,
    EVENT_TYPE_TO_PARAMS,
    EVENT_TYPE_TO_SIGNATURE,
    EVENT_TYPE_TO_UNHASHED_SIGNATURE,
    NOTIFICATION_CHAIN_MAP,
    SIGNATURE_TO_EVENT_TYPE,
    Event,
)
from .telegram import send_telegram_notification

load_dotenv()

# Constants
RETRY_COUNT = 3
RETRY_DELAY = 5  # seconds
FILTER_TIMEOUT = 10  # seconds

COW_PROTOCOL_SETTLEMENT_CONTRACT_ADDR = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"

IGNORED_TX_TO = [
    x.lower()
    for x in [
        "0xad3b67BCA8935Cb510C8D18bD45F0b94F54A968f",
        COW_PROTOCOL_SETTLEMENT_CONTRACT_ADDR,
    ]
]

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_event_name(event: LogEntry):
    """Parse and return the event name from the event's topics."""
    return SIGNATURE_TO_EVENT_TYPE[event["topics"][0].hex()]


def parse_event_topics(event: LogEntry):
    """Parse and return indexed event topics."""
    topics = event["topics"]
    event_name = parse_event_name(event)
    indexed_params = EVENT_TYPE_TO_INDEXED_PARAMS.get(event_name, [])
    return {param: topic.hex() for param, topic in zip(indexed_params, topics[1:])}


def parse_event_data(event: LogEntry):
    """Parse and return event data."""
    event_name = parse_event_name(event)
    params = EVENT_TYPE_TO_PARAMS.get(event_name, [])
    event_abi = (
        EVENT_TYPE_TO_UNHASHED_SIGNATURE[event_name].split("(")[1][:-1].split(",")
    )
    data = bytes.fromhex(event["data"].hex()[2:])

    data = abi.decode(event_abi, data)

    return {param: param_data for param, param_data in zip(params, data)}


async def get_swap_fee(chain, contract_address, block_number):
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    return (
        await web3.eth.contract(
            address=web3.to_checksum_address(contract_address),
            abi=[
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getSwapFeePercentage",
                    "outputs": [
                        {"internalType": "uint256", "name": "", "type": "uint256"}
                    ],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                }
            ],
        )
        .functions.getSwapFeePercentage()
        .call(block_identifier=block_number)
    )


class EventStrategy:
    def format_topics(self, topics):
        raise NotImplementedError("Subclasses should implement this method")

    async def format_data(self, data):
        raise NotImplementedError("Subclasses should implement this method")


class DefaultEventStrategy(EventStrategy):
    def format_topics(self, topics):
        return {k: v for k, v in topics.items()}

    async def format_data(self, _chain, data):
        return {k: v for k, v in data.items()}


class SwapFeePercentageChangedStrategy(EventStrategy):
    def format_topics(self, event):
        # Any specific transformations for this event's topics
        return {k: v for k, v in parse_event_topics(event).items()}

    async def format_data(self, chain, event):
        # Fetch the former swap fee, assuming we have a method to do so.
        former_fee = await get_swap_fee(
            chain, event["address"], event["blockNumber"] - 1
        )
        # former_fee = "TODO"
        data = parse_event_data(event)
        # Format the data accordingly
        formatted_data = {
            "Former Fee": f"{(former_fee / 1e18):.4%}",
            "New Fee": f"{data['swapFeePercentage'] / 1e18:.4%}",
        }
        return formatted_data


from datetime import datetime


class AmpUpdateStartedStrategy(EventStrategy):
    def format_topics(self, event):
        # Any specific transformations for this event's topics
        return {k: v for k, v in parse_event_topics(event).items()}

    async def format_data(self, chain, event):
        # Assume no extra data is fetched from the chain for this event.
        data = parse_event_data(event)
        print(data)

        # Convert the hex values to appropriate formats
        start_value = data["startValue"]
        end_value = data["endValue"]
        start_time = data["startTime"]
        end_time = data["endTime"]

        formatted_data = {
            "Start Value": start_value / 1000,
            "End Value": end_value / 1000,
            "Start Time": datetime.utcfromtimestamp(start_time).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "End Time": datetime.utcfromtimestamp(end_time).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
        }
        return formatted_data


class AmpUpdateStoppedStrategy(EventStrategy):
    def format_topics(self, event):
        return {k: v for k, v in parse_event_topics(event).items()}

    async def format_data(self, chain, event):
        data = parse_event_data(event)
        formatted_data = {"Current Value": data["currentValue"] / 1000}
        return formatted_data


class PoolCreatedStrategy(EventStrategy):
    def format_topics(self, event):
        return {k: v for k, v in parse_event_topics(event).items()}

    async def format_data(self, chain, event):
        data = parse_event_data(event)
        formatted_data = {"Pool Address": data["poolAddress"]}
        return formatted_data


class NewSwapFeePercentageStrategy(EventStrategy):
    def format_topics(self, event):
        return {k: v for k, v in parse_event_topics(event).items()}

    # Fetch the former swap fee, assuming we have a method to do so.

    async def format_data(self, chain, event):
        data = parse_event_data(event)

        former_fee = await get_swap_fee(
            chain, data["_address"], event["blockNumber"] - 1
        )
        formatted_data = {
            "Address": data["_address"],
            "Former Fee": f"{(former_fee / 1e18):.4%}",
            "Fee": f"{data['_fee'] / 1e18:.4%}",
        }
        return formatted_data


STRATEGY_MAP = {
    Event.SwapFeePercentageChanged: SwapFeePercentageChangedStrategy,
    Event.AmpUpdateStarted: AmpUpdateStartedStrategy,
    Event.AmpUpdateStopped: AmpUpdateStoppedStrategy,
    Event.PoolCreated: PoolCreatedStrategy,
    Event.NewSwapFeePercentage: NewSwapFeePercentageStrategy,
}


async def handle_event(chain: Chain, event: LogEntry, dry_run=False):
    """Handle the event, parse it, and send a notification."""
    chain_name = chain.name
    event_name = parse_event_name(event)

    strategy = STRATEGY_MAP.get(event_name, DefaultEventStrategy)()

    topics = strategy.format_topics(event)
    data = await strategy.format_data(chain, event)

    topic_text = ""
    if topics:
        topic_text = (
            f"Topic: %0A%0A{'%0A'.join([f'{k}: {v}' for k, v in topics.items()])}%0A%0A"
        )

    data_text = ""
    if data:
        data_text = f"Data: %0A%0A{'%0A'.join([f'{k}: {v}' for k, v in data.items()])}"

    message_text = (
        f"Chain: {chain_name}%0A"
        f"Event: {event_name.value}%0A"
        f"Transaction: {get_explorer_link(chain, event['transactionHash'].hex())}%0A"
        f"Block: {event['blockNumber']}%0A"
        f"{topic_text}"
        f"{data_text}"
    )

    if dry_run:
        logger.info(f"Would send notification: {message_text}")
        return

    return await send_telegram_notification(message_text)


def filter_multiple_swap_fee_changes(entries):
    """Filter out entries with multiple SwapFeePercentageChanged events for the same address in the same transaction."""
    tx_hash_to_address_counts = {}

    # Count occurrences of SwapFeePercentageChanged events by transaction hash and address
    for entry in entries:
        if parse_event_name(entry) == Event.SwapFeePercentageChanged:
            tx_hash = entry["transactionHash"]
            address = entry["address"]
            tx_hash_to_address_counts.setdefault(tx_hash, {}).setdefault(address, 0)
            tx_hash_to_address_counts[tx_hash][address] += 1

    # Filter out entries where the count of SwapFeePercentageChanged events for a specific address in a specific transaction is more than 1
    return [
        entry
        for entry in entries
        if tx_hash_to_address_counts.get(entry["transactionHash"], {}).get(
            entry["address"], 0
        )
        == 1
        or parse_event_name(entry) != Event.SwapFeePercentageChanged
    ]


async def log_loop(chain: Chain, event_filter: AsyncFilter, poll_interval: int):
    """Continuous loop to fetch and handle new log entries."""
    logger.info(f"Starting log loop for {chain}")

    while True:
        try:
            logger.info(f"Fetching new entries in {chain}")
            entries = await event_filter.get_new_entries()

            # Filter out specific transactions to ignore
            web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
            entries = [
                entry
                for entry in entries
                if (await web3.eth.get_transaction(entry["transactionHash"]))[
                    "to"
                ].lower()
                not in IGNORED_TX_TO
            ]

            filtered_entries = filter_multiple_swap_fee_changes(entries)

            await asyncio.gather(
                *[handle_event(chain, entry) for entry in filtered_entries]
            )
            await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Error while fetching new entries for {chain}: {e}")


async def create_event_filter(chain, from_block=None, to_block=None):
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    if from_block and to_block:
        return await asyncio.wait_for(
            web3.eth.filter(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]],
                }
            ),  # type: ignore
            timeout=FILTER_TIMEOUT,
        )
    else:
        return await asyncio.wait_for(
            web3.eth.filter({"topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]]}),  # type: ignore
            timeout=FILTER_TIMEOUT,
        )


async def setup_and_run_chain(chain):
    retry = 0
    while retry < RETRY_COUNT:
        try:
            event_filter = await create_event_filter(chain)
            await log_loop(chain, event_filter, 2)
            break
        except asyncio.TimeoutError:
            logger.warning(f"Timeout when setting up filter for {chain}. Retrying...")
            retry += 1
        except Exception as e:
            logger.error(f"Error setting up filter for {chain}: {e}. Retrying...")
            retry += 1
            await asyncio.sleep(RETRY_DELAY)

    if retry == RETRY_COUNT:
        logger.error(f"Exceeded retry attempts for {chain}.")


async def main():
    """Main entry for the asynchronous event handling."""
    tasks = [setup_and_run_chain(chain) for chain in NOTIFICATION_CHAIN_MAP.keys()]
    await asyncio.gather(*tasks)


async def fetch_events_for_block_range(
    chain: Chain, from_block: int, to_block: int
) -> List[LogEntry]:
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    events = await web3.eth.get_logs(
        {
            "fromBlock": from_block,
            "toBlock": to_block,
            "topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]],
        }
    )
    return events


async def test_block_range(chain: Chain, from_block: int, to_block: int):
    logger.info(f"Fetching events from block {from_block} to {to_block} for {chain}")
    events = await fetch_events_for_block_range(chain, from_block, to_block)

    # Filter out specific transactions to ignore
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    events = [
        entry
        for entry in events
        if (await web3.eth.get_transaction(entry["transactionHash"]))
        .get("to", "")
        .lower()
        not in IGNORED_TX_TO
    ]

    filtered_events = filter_multiple_swap_fee_changes(events)

    return await asyncio.gather(
        *[handle_event(chain, entry, False) for entry in filtered_events]
    )


if __name__ == "__main__":
    asyncio.run(main())

# if __name__ == "__main__":
#     from_block = 17971038 - 1
#     to_block = 17971038 + 1
#     chain = Chain.mainnet
#     asyncio.run(test_block_range(chain, from_block, to_block))
