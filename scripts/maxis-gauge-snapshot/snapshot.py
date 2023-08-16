# From https://github.com/snapshot-labs/snapshot.js/blob/master/src/sign/index.ts
import os
from time import time

import aiohttp
from balpy.chains import Chain
from balpy.core.lib.web3_provider import Web3Provider
from eth_account._utils.structured_data.hashing import encode_data
from eth_account.messages import SignableMessage
from eth_utils.crypto import keccak
from hexbytes import HexBytes

# https://testnet.snapshot.org
# https://hub.snapshot.org

DOMAIN = dict(name="snapshot", version="0.1.4")
PROPOSAL_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
    ],
    "Proposal": [
        {"name": "from", "type": "address"},
        {"name": "space", "type": "string"},
        {"name": "timestamp", "type": "uint64"},
        {"name": "type", "type": "string"},
        {"name": "title", "type": "string"},
        {"name": "body", "type": "string"},
        {"name": "discussion", "type": "string"},
        {"name": "choices", "type": "string[]"},
        {"name": "start", "type": "uint64"},
        {"name": "end", "type": "uint64"},
        {"name": "snapshot", "type": "uint64"},
        {"name": "plugins", "type": "string"},
        {"name": "app", "type": "string"},
    ],
}


class Snapshot:
    def __init__(self, url: str, chain: Chain):
        self.url = url
        self.chain = chain or Chain.mainnet
        self.w3 = Web3Provider.get_instance(self.chain)

    async def sign(self, message: dict, types: dict):
        private_key = os.getenv(
            "PRIVATE_KEY",
        )
        checksum_address = self.w3.eth.account.from_key(private_key).address
        message["from"] = checksum_address
        message["timestamp"] = message.get("timestamp", int(time()))

        message_data = {
            "domain": DOMAIN,
            "types": types,
            "message": message,
            # "primaryType": "Proposal",
        }

        data = SignableMessage(
            HexBytes(b"\x01"),
            keccak(
                encode_data(
                    "EIP712Domain", message_data["types"], message_data["domain"]
                )
            ),
            keccak(
                encode_data(
                    "Proposal",
                    message_data["types"],
                    message_data["message"],
                )
            ),
        )

        private_key = os.getenv(
            "PRIVATE_KEY",
            "e8c4b26ab3e86ab1e3cce5733c00186011712d3536021f211e963f451538ab53",
        )
        sig = self.w3.eth.account.sign_message(data, private_key).signature.hex()

        message_data = {
            **message_data,
            "types": {
                "Proposal": message_data["types"]["Proposal"],
            },
        }
        payload = {"address": checksum_address, "sig": sig, "data": message_data}

        return await self.send(payload)

    async def send(self, envelop: dict):
        url = self.url
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=envelop,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    response_content = await response.json()
                    raise ValueError(response_content)

    async def proposal(self, message: dict):
        message.setdefault("discussion", "")
        message.setdefault("app", "")
        return await self.sign(message, PROPOSAL_TYPES)
