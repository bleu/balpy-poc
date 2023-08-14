from balpy.chains import Chain
from balpy.subgraphs.client import GraphQLClient
from balpy.subgraphs.query import GraphQLQuery

BASE_URL = "https://api.thegraph.com/subgraphs/name/balancer-labs"

BALANCER_MAINNET_SUBGRAPH_URL_MAP = {
    Chain.mainnet: BASE_URL + "/balancer-v2",
    Chain.polygon: BASE_URL + "/balancer-polygon-v2",
    Chain.polygon_zkevm: "https://api.studio.thegraph.com/query/24660/balancer-polygon-zk-v2/version/latest",
    Chain.arbitrum: BASE_URL + "/balancer-arbitrum-v2",
    Chain.gnosis: BASE_URL + "/balancer-gnosis-chain-v2",
    Chain.optimism: BASE_URL + "/balancer-optimism-v2",
    Chain.avalanche: BASE_URL + "/balancer-avalanche-v2",
    Chain.goerli: "https://api.studio.thegraph.com/query/24660/balancer-sepolia-v2/version/latest",
    Chain.sepolia: BASE_URL + "/balancer-avalanche-v2",
    # Chain.base: TODO
}


class BalancerSubgraph(GraphQLClient):
    def get_url(self, chain):
        return BALANCER_MAINNET_SUBGRAPH_URL_MAP[chain]


class BalancerSubgraphQuery(GraphQLQuery):
    def get_client(self):
        return BalancerSubgraph(self.chain)
