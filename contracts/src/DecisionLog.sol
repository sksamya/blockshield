// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DecisionLog
 * @notice Immutable anchor on the MST Blockchain for bank risk decisions.
 * Only the cryptographic hash of the canonical off-chain decision JSON is anchored.
 */
contract DecisionLog {
    address public owner;

    struct AnchorRecord {
        string bankId;          // E.g. "bank-b"
        bytes32 eventRef;       // Off-chain event identifier / UUID
        bytes32 decisionHash;   // keccak256(canonical JSON)
        uint256 timestamp;      // Decision timestamp
        uint256 blockTimestamp; // Anchor block timestamp
        address recordedBy;
    }

    mapping(address => bool) public registeredBanks;
    // Mapping bankId => registered signer address
    mapping(string => address) public bankSigners;
    // Mapping eventRef => AnchorRecord
    mapping(bytes32 => AnchorRecord) public anchors;
    // Array of all event references
    bytes32[] public allEventRefs;

    event BankRegistered(string indexed bankId, address indexed signer);
    event DecisionAnchored(
        bytes32 indexed eventRef,
        string indexed bankId,
        bytes32 indexed decisionHash,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only consortium owner");
        _;
    }

    modifier onlyBank(string memory bankId) {
        require(registeredBanks[msg.sender] || msg.sender == owner, "Sender not authorized bank");
        if (bankSigners[bankId] != address(0)) {
            require(bankSigners[bankId] == msg.sender || msg.sender == owner, "Bank ID signer mismatch");
        }
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerBank(string calldata bankId, address bankSigner) external onlyOwner {
        require(bankSigner != address(0), "Invalid bank address");
        registeredBanks[bankSigner] = true;
        bankSigners[bankId] = bankSigner;
        emit BankRegistered(bankId, bankSigner);
    }

    /**
     * @notice Anchor a decision hash for auditability.
     */
    function anchor(
        string calldata bankId,
        bytes32 eventRef,
        bytes32 decisionHash,
        uint256 timestamp
    ) external onlyBank(bankId) {
        require(eventRef != bytes32(0), "Invalid eventRef");
        require(decisionHash != bytes32(0), "Invalid decisionHash");
        require(anchors[eventRef].decisionHash == bytes32(0), "Decision already anchored");

        anchors[eventRef] = AnchorRecord({
            bankId: bankId,
            eventRef: eventRef,
            decisionHash: decisionHash,
            timestamp: timestamp,
            blockTimestamp: block.timestamp,
            recordedBy: msg.sender
        });

        allEventRefs.push(eventRef);
        emit DecisionAnchored(eventRef, bankId, decisionHash, timestamp);
    }

    /**
     * @notice Verify if an off-chain decision hash matches the on-chain anchor.
     */
    function verifyAnchor(bytes32 eventRef, bytes32 decisionHash)
        external
        view
        returns (bool isMatch, uint256 anchoredAt, string memory bankId)
    {
        AnchorRecord memory record = anchors[eventRef];
        if (record.decisionHash == bytes32(0)) {
            return (false, 0, "");
        }
        return (record.decisionHash == decisionHash, record.blockTimestamp, record.bankId);
    }

    function getTotalAnchors() external view returns (uint256) {
        return allEventRefs.length;
    }
}
