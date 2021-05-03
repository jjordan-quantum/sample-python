# return the current reserve ratio for the LP pool with the given address
def getReserveRatio(web3, contract_address, abi):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    reserves = contract.functions.getReserves().call()
    return float(reserves[1]) / reserves[0]

# return the current reserve<n> - n must be 0 or 1
def getReserve(web3, contract_address, abi, n):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    reserves = contract.functions.getReserves().call()
    return reserves[n]

# return the totalSupply of LP tokens
def getTotalSupply(web3, contract_address, abi):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    return contract.functions.totalSupply().call()

# return balanceOf address
def getBalanceOf(web3, contract_address, abi, query_address):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    return contract.functions.balanceOf(query_address).call()