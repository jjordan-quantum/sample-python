import time
import json
from lib import abi
from lib import pancake

#------------------------------------------------------------------
# CONNECT TO BSC

#wallet_address = '0xcfB7624E20Dd39f373FC92fC447B1398bf40bd35'
#wallet_address = '0xBaDe72bB36e39E3c201c2C6F645F683614CbAA7f' # NEAL's
wallet_address = '0x335cC3433192e87a84bF5C00d2939E4400056c25' # my wallet

# TODO
# REMOVE THIS FOR DEPLOYMENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#PRIVATE_KEY = '6690008c02fdf5976fae94b34c3b29f214571e2e99fea5d0b02a4d81d52f6b87'  # NEAL's
PRIVATE_KEY = '3b62ca31c5a7007300f949f838bd0178bfea890a21c6b514ae615264269ea20c'  # my wallet

getblock_API_key = '2aebf3b3-089c-4487-b570-9c50991bff2b'

#wss_provider = 'wss://bsc.getblock.io/mainnet/?api_key='+getblock_API_key
#web3 = Web3(Web3.WebsocketProvider(wss_provider))

http_provider = 'https://bsc.getblock.io/mainnet/?api_key='+getblock_API_key
#web3 = Web3(Web3.HTTPProvider(http_provider))

# instantiate Pancake and tokens
client = pancake.Pancake(wallet=wallet_address, private_key=PRIVATE_KEY, http_provider=http_provider)
router = client.router

# get ERC20 ABI
with open('lib/IUniswapV2ERC20.json', 'r') as read_file:
    erc20_abi = json.load(read_file)['abi']

# get pancake pair abi
with open('lib/IUniswapV2Pair.json', 'r') as read_file:
    pair_abi = json.load(read_file)['abi']

# create local references to the desired Token objects
cub = client.tokens["CUB"]     # reserve0
busd = client.tokens["BUSD"]   # reserve1

cub_address = cub.address
busd_address = busd.address

#########################################################
#
# SWAP PARAMETERS
#
##########################################################
amount = 0.00500001
token_in = "BNB"
token_out = "CAKE"
deadline = 300
slippage = 0.98
gas_price = int(client.web3.eth.gas_price * 2)

# SWAP FUNCTION

#tokens_transferred = client.swapAtMarket(amount, token_in, token_out, deadline=deadline, gasPrice=gas_price)

#print(f'Tokens transferred: {tokens_transferred}')

#############################################################

from decimal import Decimal

print(client.web3.toWei(1, 'finney'))
