pragma solidity ^0.8.20;

contract Owned {
    function adminAction() external onlyOwner {}
}

contract Vault is Owned {
    function authorize() external {
        require(tx.origin == msg.sender);
    }

    function upgradeTo(address implementation) external onlyOwner {}

    function checkInvariant(uint256 assets, uint256 claims) external pure {
        assert(assets >= claims);
    }
}
