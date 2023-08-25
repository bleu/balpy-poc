import os

from balpy.chains import Chain
from dotenv import load_dotenv

load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
LLAMA_PROJECT_ID = os.getenv("LLAMA_PROJECT_ID")

POLYGONSCAN_API_KEY = os.getenv("POLYGONSCAN_API_KEY")

DEFAULT_PROVIDER_NETWORK_MAPPING = {
    # Chain.mainnet: "https://eth.llamarpc.com/rpc/{}".format(LLAMA_PROJECT_ID),
    # Chain.mainnet: "https://api.zmok.io/mainnet/oaen6dy8ff6hju9k",
    Chain.mainnet: "https://silent-floral-general.discover.quiknode.pro/4db24b930f19041c6cf3ea1c2eac8e1a93d14f34/",
    Chain.polygon: "https://polygon.llamarpc.com/rpc/{}".format(LLAMA_PROJECT_ID),
    Chain.goerli: "https://ethereum-goerli.publicnode.com",
}
