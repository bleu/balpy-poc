import asyncio
import logging

from balpy.chains import Chain
from balpy.core.lib.web3_provider import Web3Provider
from dotenv import load_dotenv
from retry_async import retry
from web3._utils.filters import AsyncFilter
from web3.types import LogEntry

from scripts.listen_to_events.strategies import (
    STRATEGY_MAP,
    DefaultEventStrategy,
    parse_event_name,
)

from .config import EVENT_TYPE_TO_SIGNATURE, NOTIFICATION_CHAIN_MAP, Event
from .discord import send_discord_embed, start_discord_bot
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


async def handle_event(chain: Chain, event: LogEntry, dry_run=False):
    """Handle the event, parse it, and send a notification."""
    data = {
        "chain": chain,
        "event": event,
    }

    strategy = STRATEGY_MAP.get(parse_event_name(data["event"]), DefaultEventStrategy)()

    data["topics"], data["info"] = await asyncio.gather(
        strategy.format_topics(chain, event), strategy.format_data(chain, event)
    )

    if dry_run:
        logger.info(f"Would send notification: {data}")
        return

    return await asyncio.gather(
        send_discord_embed(data), send_telegram_notification(data)
    )


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


@retry(
    is_async=True,
    tries=5,
    delay=5,
    logger=logger,
)
async def create_event_filter(chain, from_block=None, to_block=None):
    logger.info(f"Creating event filter for {chain}")
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    if from_block and to_block:
        return await asyncio.wait_for(
            web3.eth.filter(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]],
                }  # type: ignore
            ),
            timeout=FILTER_TIMEOUT,
        )
    else:
        return await asyncio.wait_for(
            web3.eth.filter({"topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]]}),  # type: ignore
            timeout=FILTER_TIMEOUT,
        )


@retry(
    is_async=True,
    tries=-1,
    delay=5,
    logger=logger,
)
async def setup_and_run_chain(chain):
    event_filter = await create_event_filter(chain)
    await log_loop(chain, event_filter, 2)


async def main():
    """Main entry for the asynchronous event handling."""
    tasks = [setup_and_run_chain(chain) for chain in NOTIFICATION_CHAIN_MAP.keys()]
    await asyncio.gather(*tasks)


async def fetch_events_for_block_range(chain: Chain, from_block: int, to_block: int):
    web3 = Web3Provider.get_instance(chain, {}, NOTIFICATION_CHAIN_MAP)
    events = await web3.eth.get_logs(
        {
            "fromBlock": from_block,
            "toBlock": to_block,
            "topics": [[sig for sig in EVENT_TYPE_TO_SIGNATURE.values()]],  # type: ignore
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
        *[handle_event(chain, entry, dry_run=False) for entry in filtered_events]
    )


async def test_messages():
    from_block = 18000712 - 1
    to_block = 18000712 + 1
    chain = Chain.mainnet
    await asyncio.gather(
        test_block_range(chain, from_block, to_block), start_discord_bot()
    )


if __name__ == "__main__":
    asyncio.run(main())

# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(test_messages())
