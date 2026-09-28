// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FraudRegistry
 * @notice Shared consortium registry for banks to report and query suspected mule accounts.
 */
contract FraudRegistry {
    address public owner;

    struct Bank {
        string name;
        address signerAddress;
        bool isActive;
    }

    struct MuleFlag {
        bytes32 accountToken;    // Keyed hash of account number
        string reporterBankId;  // E.g. "bank-b"
        bytes32 evidenceHash;   // keccak256 of off-chain case data
        uint256 timestamp;      // Timestamp when flagged
        bool isActive;
        string reason;
    }

    mapping(string => Bank) public banks;
    mapping(address => string) public bankByAddress;
    // Mapping accountToken => MuleFlag
    mapping(bytes32 => MuleFlag) public muleFlags;
    // Mapping accountToken => history
    mapping(bytes32 => MuleFlag[]) private flagHistory;

    event BankRegistered(string indexed bankId, address indexed signerAddress, string name);
    event MuleFlagged(
        bytes32 indexed accountToken,
        string indexed reporterBankId,
        bytes32 evidenceHash,
        uint256 timestamp,
        string reason
    );
    event MuleUnflagged(bytes32 indexed accountToken, string indexed bankId, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only consortium owner");
        _;
    }

    modifier onlyRegisteredBank(string memory bankId) {
        Bank memory b = banks[bankId];
        require(b.isActive, "Bank not active or unregistered");
        require(msg.sender == b.signerAddress || msg.sender == owner, "Unauthorized bank signer");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerBank(
        string calldata bankId,
        address signerAddress,
        string calldata name
    ) external onlyOwner {
        require(signerAddress != address(0), "Invalid bank address");
        banks[bankId] = Bank(name, signerAddress, true);
        bankByAddress[signerAddress] = bankId;
        emit BankRegistered(bankId, signerAddress, name);
    }

    /**
     * @notice Flag an account as a suspected mule.
     */
    function flagMule(
        bytes32 accountToken,
        string calldata bankId,
        bytes32 evidenceHash,
        string calldata reason
    ) external onlyRegisteredBank(bankId) {
        require(accountToken != bytes32(0), "Invalid account token");

        MuleFlag memory flag = MuleFlag({
            accountToken: accountToken,
            reporterBankId: bankId,
            evidenceHash: evidenceHash,
            timestamp: block.timestamp,
            isActive: true,
            reason: reason
        });

        muleFlags[accountToken] = flag;
        flagHistory[accountToken].push(flag);

        emit MuleFlagged(accountToken, bankId, evidenceHash, block.timestamp, reason);
    }

    /**
     * @notice Clear/unflag a mule account if resolved.
     */
    function unflagMule(
        bytes32 accountToken,
        string calldata bankId
    ) external onlyRegisteredBank(bankId) {
        require(muleFlags[accountToken].isActive, "Account not flagged");
        muleFlags[accountToken].isActive = false;

        emit MuleUnflagged(accountToken, bankId, block.timestamp);
    }

    /**
     * @notice Query if an account token is flagged as a mule.
     */
    function isMule(bytes32 accountToken) external view returns (bool, string memory, uint256, string memory) {
        MuleFlag memory f = muleFlags[accountToken];
        return (f.isActive, f.reporterBankId, f.timestamp, f.reason);
    }
}
