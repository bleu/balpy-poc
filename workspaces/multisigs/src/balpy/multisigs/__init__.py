BASE_URL = "https://api.thegraph.com/subgraphs/name/balpy-labs"

BALANCER_MAINNET_SUBGRAPH_URL_MAP = {
    Chain.mainnet: BASE_URL + "/balpy-v2",
    Chain.polygon: BASE_URL + "/balpy-polygon-v2",
    Chain.polygon_zkevm: "https://api.studio.thegraph.com/query/24660/balpy-polygon-zk-v2/version/latest",
    Chain.arbitrum: BASE_URL + "/balpy-arbitrum-v2",
    Chain.gnosis: BASE_URL + "/balpy-gnosis-chain-v2",
    Chain.optimism: BASE_URL + "/balpy-optimism-v2",
    Chain.avalanche: BASE_URL + "/balpy-avalanche-v2",
    Chain.goerli: "https://api.studio.thegraph.com/query/24660/balpy-sepolia-v2/version/latest",
    Chain.sepolia: BASE_URL + "/balpy-avalanche-v2",
    # Chain.base: TODO
}
