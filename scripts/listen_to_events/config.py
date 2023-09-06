from enum import Enum

from balpy.chains import Chain
from balpy.core.lib.web3_provider import Web3Provider

web3 = Web3Provider.get_instance()


class Event(Enum):
    SwapFeePercentageChanged = "SwapFeePercentageChanged"
    AmpUpdateStarted = "AmpUpdateStarted"
    AmpUpdateStopped = "AmpUpdateStopped"
    PoolRegistered = "PoolRegistered"
    NewSwapFeePercentage = "NewSwapFeePercentage"


EVENT_TYPE_TO_UNHASHED_SIGNATURE = {
    Event.SwapFeePercentageChanged: "SwapFeePercentageChanged(uint256)",  # swapFeePercentage
    Event.AmpUpdateStarted: "AmpUpdateStarted(uint256,uint256,uint256,uint256)",  # startValue, endValue, startTime, endTime
    Event.AmpUpdateStopped: "AmpUpdateStopped(uint256)",  # currentValue
    Event.PoolRegistered: "PoolRegistered(bytes32,address,uint8)",  # poolAddress
    Event.NewSwapFeePercentage: "NewSwapFeePercentage(address,uint256)",  # poolAddress, swapFeePercentage
}

EVENT_TYPE_TO_SIGNATURE = {
    event_name: web3.keccak(text=text_sig).hex()
    for event_name, text_sig in EVENT_TYPE_TO_UNHASHED_SIGNATURE.items()
}
EVENT_TYPE_TO_INDEXED_PARAMS = {
    Event.PoolRegistered: ["poolId", "poolAddress"],
}

EVENT_TYPE_TO_PARAMS = {
    Event.SwapFeePercentageChanged: ["swapFeePercentage"],
    Event.AmpUpdateStarted: ["startValue", "endValue", "startTime", "endTime"],
    Event.AmpUpdateStopped: ["currentValue"],
    Event.NewSwapFeePercentage: ["_address", "_fee"],
    Event.PoolRegistered: ["specialization"],
}


SIGNATURE_TO_EVENT_TYPE = {v: k for k, v in EVENT_TYPE_TO_SIGNATURE.items()}

NOTIFICATION_CHAIN_MAP = {
    Chain.mainnet: "https://frequent-radial-pool.discover.quiknode.pro/4c72f5555c7330fd95a94c71f63da6de4302972e",
    Chain.polygon: "https://polygon-mainnet.g.alchemy.com/v2/pNHndmkCUlO4FZTLJSRUCcGKVFXumFuJ",
    Chain.polygon_zkevm: f"https://polygonzkevm-mainnet.g.alchemy.com/v2/v7Ec47UcoFB1V_I_SZcke638RNmLw9EM",
    Chain.arbitrum: "https://arb-mainnet.g.alchemy.com/v2/I9zUuFx228-1hzJKoHEfeJyljBn2Wl5I",
    Chain.optimism: "https://opt-mainnet.g.alchemy.com/v2/CLaPrMa_bTgusPZ1PArSMfBiFxJvk9Ih",
    Chain.avalanche: "https://fabled-clean-river.avalanche-mainnet.discover.quiknode.pro/bd0bdfc62aaccf30599c873dab389e1cd445959e/ext/bc/C/rpc/",
    Chain.gnosis: "https://delicate-weathered-sanctuary.xdai.discover.quiknode.pro/a6c577b0e8be1c07bac8bb720a72114570013985/",
    Chain.base: "https://base-mainnet.g.alchemy.com/v2/Ax03tgh7LvDEODZs0hEQGl20ddJPjUri",
}
