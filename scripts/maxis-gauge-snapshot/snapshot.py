# From https://github.com/snapshot-labs/snapshot.js/blob/master/src/sign/index.ts
import json
import os
from time import time
from typing import Any, Dict, Union

from balpy.chains import Chain
from balpy.core.lib.web3_provider import Web3Provider
from eth_account.messages import encode_structured_data
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.encoding import Web3JsonEncoder

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


class Encoder(Web3JsonEncoder):
    def default(self, obj: Any) -> Union[Dict[Any, Any], HexStr]:
        if isinstance(obj, bytes):
            return HexStr(HexBytes(obj).hex())
        else:
            return super().default(obj)


class Snapshot:
    def __init__(self, url: str, chain: Chain):
        self.url = url
        self.chain = chain or Chain.mainnet

    async def sign(self, address: str, message: dict, types: dict):
        web3 = Web3Provider.get_instance(self.chain)

        checksum_address = Web3.to_checksum_address(address)
        message["from"] = Web3.to_checksum_address(
            message.get("from", checksum_address)
        )
        message["timestamp"] = message.get("timestamp", int(time()))

        data = encode_structured_data(
            {
                "domain": DOMAIN,
                "types": types,
                "message": message,
                "primaryType": "Proposal",
            }
        )

        sig = web3.eth.account.sign_message(data, os.getenv("PRIVATE_KEY"))

        payload = {"address": checksum_address, "sig": sig, "data": data}

        return await self.send(payload)

    async def send(self, envelop: dict):
        url = self.url
        data = json.dumps(envelop, cls=Encoder)
        import requests

        response = requests.post(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if response.status_code == 200:
            print(response.json())
            return response.json()
        else:
            print(response.text)
            raise ValueError(response.text)

        # async with aiohttp.ClientSession() as session:
        #     async with session.post(url, body=data) as response:
        #         if response.status == 200:
        #             return await response.json()
        #         else:
        #             print(await response.text())
        #             response_content = await response.json()
        #             raise ValueError(response_content)

    async def proposal(self, address: str, message: dict):
        message.setdefault("discussion", "")
        message.setdefault("app", "")
        return await self.sign(address, message, PROPOSAL_TYPES)


proposal_data = {
    "space": "joferi.eth",
    "type": "single-choice",  # define the voting system
    "title": "Test proposal using Snapshot.js",
    "body": "This is the content of the proposal",
    "choices": ["Alice", "Bob", "Carol"],
    "start": 1636984800,
    "end": 1637244000,
    "snapshot": 13620822,
    "network": "1",
    "plugins": json.dumps({}),
    "app": "gauges-integration",
}
