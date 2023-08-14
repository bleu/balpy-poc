from balpy.chains import Chain
from balpy.subgraphs.client import GraphQLClient
from balpy.subgraphs.query import GraphQLQuery

BASE_URL = "https://api.thegraph.com/subgraphs/name/balancer-labs"

BALANCER_MAINNET_GAUGES_SUBGRAPH_URL_MAP = {
    Chain.mainnet: BASE_URL + "/balancer-gauges",
    Chain.polygon: BASE_URL + "/balancer-gauges-polygon",
    # Chain.polygon_zkevm: TODO
    Chain.arbitrum: BASE_URL + "/balancer-gauges-arbitrum",
    Chain.gnosis: BASE_URL + "/balancer-gauges-gnosis-chain",
    # Chain.optimism: TODO
    # Chain.avalanche: TODO
    # Chain.goerli: TODO
    # Chain.sepolia: TODO
    # Chain.base: TODO
}

DEPLOYED_CHAINS = BALANCER_MAINNET_GAUGES_SUBGRAPH_URL_MAP.keys()


class GaugesSubgraph(GraphQLClient):
    def get_url(self, chain):
        return BALANCER_MAINNET_GAUGES_SUBGRAPH_URL_MAP[chain]


class GaugesSubgraphQuery(GraphQLQuery):
    def get_client(self):
        return GaugesSubgraph(self.chain)
