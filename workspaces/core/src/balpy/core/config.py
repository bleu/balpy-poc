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
    Chain.mainnet: "https://frequent-radial-pool.discover.quiknode.pro/4c72f5555c7330fd95a94c71f63da6de4302972e",
    Chain.polygon: "https://polygon.llamarpc.com/rpc/{}".format(LLAMA_PROJECT_ID),
    Chain.goerli: "https://ethereum-goerli.publicnode.com",
}
