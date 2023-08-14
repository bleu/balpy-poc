from enum import Enum


class Chain(Enum):
    mainnet = 1
    polygon = 137
    polygon_zkevm = 1101
    arbitrum = 42161
    gnosis = 100
    optimism = 10
    avalanche = 43114
    goerli = 5
    sepolia = 11155111
    base = 8453

    def __init__(self, id) -> None:
        self.id = id


ALL_CHAINS = [chain for chain in Chain]
