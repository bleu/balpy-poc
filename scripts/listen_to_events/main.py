import asyncio
import logging

from balpy.chains import Chain
from balpy.core.lib.web3_provider import Web3Provider
from balpy.core.utils import get_explorer_link
from dotenv import load_dotenv
from hexbytes import HexBytes
from web3._utils.filters import AsyncFilter
from web3.types import LogEntry

from .config import (
    EVENT_TYPE_TO_INDEXED_PARAMS,
    EVENT_TYPE_TO_PARAMS,
    EVENT_TYPE_TO_SIGNATURE,
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
    data = event["data"]

    if isinstance(data, HexBytes):
        try:
            raw_value = int(data.hex(), base=16)
            data = f"{raw_value} ({hex(raw_value)})"
            if event_name == Event.SwapFeePercentageChanged:
                data = f"{(raw_value / 1e18):.2%}"
        except ValueError:
            pass
    return {param: data for param in params}


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


async def get_previous_swap_fee(chain, event):
    contract = event["address"]
    block_number = event["blockNumber"]
    web3 = Web3Provider.get_instance()
    return (
        await web3.eth.contract(
            address=contract,
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
        .call(block_identifier=block_number - 1)
    )


class SwapFeePercentageChangedStrategy(EventStrategy):
    def format_topics(self, event):
        # Any specific transformations for this event's topics
        return {k: v for k, v in parse_event_topics(event).items()}

    async def format_data(self, chain, event):
        # Fetch the former swap fee, assuming we have a method to do so.
        former_fee = await get_previous_swap_fee(chain, event)
        # former_fee = "TODO"
        data = parse_event_data(event)
        # Format the data accordingly
        formatted_data = {
            "Former Fee": f"{(former_fee / 1e18):.2%}",
            "New Fee": f"{data['swapFeePercentage']}%",
        }
        return formatted_data


STRATEGY_MAP = {
    Event.SwapFeePercentageChanged: SwapFeePercentageChangedStrategy,
}


async def handle_event(chain: Chain, event: LogEntry):
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

    return await send_telegram_notification(message_text)


async def log_loop(chain: Chain, event_filter: AsyncFilter, poll_interval: int):
    """Continuous loop to fetch and handle new log entries."""
    logger.info(f"Starting log loop for {chain}")

    seen_tx_event_combinations = set()

    while True:
        try:
            logger.info(f"Fetching new entries in {chain}")
            entries = await event_filter.get_new_entries()

            unique_entries = []
            for entry in entries:
                event_name = parse_event_name(entry)
                tx_hash = entry["transactionHash"]
                # find tx "to":
                web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
                tx = await web3.eth.get_transaction(tx_hash)
                print(tx)
                if tx["to"] == COW_PROTOCOL_SETTLEMENT_CONTRACT_ADDR:
                    continue

                if (tx_hash, event_name) not in seen_tx_event_combinations:
                    seen_tx_event_combinations.add((tx_hash, event_name))
                    unique_entries.append(entry)

            await asyncio.gather(
                *[handle_event(chain, entry) for entry in unique_entries]
            )
            await asyncio.sleep(poll_interval)
            seen_tx_event_combinations = set()
        except Exception as e:
            logger.error(f"Error while fetching new entries for {chain}: {e}")


async def setup_and_run_chain(chain):
    """Setup event filter for a chain and start the log loop."""
    retry = 0
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    while retry < RETRY_COUNT:
        try:
            event_filter = await asyncio.wait_for(
                web3.eth.filter(
                    {
                        "topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]],
                    }  # type: ignore
                ),
                timeout=FILTER_TIMEOUT,
            )
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


if __name__ == "__main__":
    asyncio.run(main())
