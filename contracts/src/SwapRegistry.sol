// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SwapRegistry
 * @notice Stores privacy-preserving SIM-swap, eSIM, and Port-Out events signed by authorized carriers on the MST Blockchain.
 */
contract SwapRegistry {
    address public owner;

    struct Carrier {
        string name;
        address signerAddress;
        bool isActive;
    }

    struct SwapEvent {
        bytes token;              // HMAC-SHA256(carrier_key, phone_number)
        string carrierId;        // E.g. "carrier-a"
        string eventType;        // "SIM_SWAP" | "ESIM" | "PORT_OUT"
        uint256 timestamp;       // Event timestamp (seconds)
        bool preNotified;        // Customer pre-notified carrier
        string notificationRef;  // Optional reference ID
        uint256 blockTimestamp;  // Timestamp when recorded on MST chain
    }

    struct PreNotification {
        bytes token;
        string carrierId;
        uint256 validUntil;
        bool consumed;
    }

    // Mapping carrierId => Carrier info
    mapping(string => Carrier) public carriers;
    // Mapping carrier address => carrierId
    mapping(address => string) public carrierByAddress;
    // Mapping token => latest SwapEvent
    mapping(bytes32 => SwapEvent) public latestEvents;
    // Mapping token => event count
    mapping(bytes32 => uint256) public eventCounts;
    // Mapping token => array of all events
    mapping(bytes32 => SwapEvent[]) private eventHistory;
    // Nonce replay protection: nonce => used
    mapping(bytes32 => bool) public usedNonces;
    // Mapping token => PreNotification
    mapping(bytes32 => PreNotification) public preNotifications;

    event CarrierRegistered(string indexed carrierId, address indexed signerAddress, string name);
    event CarrierStatusUpdated(string indexed carrierId, bool isActive);
    event PreNotificationRegistered(bytes32 indexed tokenHash, string carrierId, uint256 validUntil);
    event SwapRecorded(
        bytes32 indexed tokenHash,
        string indexed carrierId,
        string eventType,
        uint256 timestamp,
        bool preNotified
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only consortium owner");
        _;
    }

    modifier onlyCarrier(string memory carrierId) {
        Carrier memory c = carriers[carrierId];
        require(c.isActive, "Carrier not active");
        require(msg.sender == c.signerAddress || msg.sender == owner, "Unauthorized carrier signer");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerCarrier(
        string calldata carrierId,
        address signerAddress,
        string calldata name
    ) external onlyOwner {
        require(signerAddress != address(0), "Invalid signer address");
        carriers[carrierId] = Carrier(name, signerAddress, true);
        carrierByAddress[signerAddress] = carrierId;
        emit CarrierRegistered(carrierId, signerAddress, name);
    }

    function setCarrierStatus(string calldata carrierId, bool isActive) external onlyOwner {
        require(carriers[carrierId].signerAddress != address(0), "Carrier not found");
        carriers[carrierId].isActive = isActive;
        emit CarrierStatusUpdated(carrierId, isActive);
    }

    /**
     * @notice Register a customer pre-notification of an upcoming SIM change.
     */
    function registerPreNotification(
        bytes calldata token,
        string calldata carrierId,
        uint256 validDurationSeconds
    ) external onlyCarrier(carrierId) {
        bytes32 tokenHash = keccak256(token);
        uint256 validUntil = block.timestamp + validDurationSeconds;
        preNotifications[tokenHash] = PreNotification(token, carrierId, validUntil, false);
        emit PreNotificationRegistered(tokenHash, carrierId, validUntil);
    }

    /**
     * @notice Check if a token has a valid active pre-notification.
     */
    function hasActivePreNotification(bytes calldata token) public view returns (bool) {
        bytes32 tokenHash = keccak256(token);
        PreNotification memory pn = preNotifications[tokenHash];
        return (!pn.consumed && pn.validUntil >= block.timestamp);
    }

    /**
     * @notice Record a SIM swap or related lifecycle event.
     */
    function recordEvent(
        bytes calldata token,
        string calldata carrierId,
        string calldata eventType,
        uint256 timestamp,
        bool preNotified,
        string calldata notificationRef,
        bytes32 nonce,
        bytes calldata signature
    ) external returns (bytes32) {
        require(!usedNonces[nonce], "Nonce already used");
        usedNonces[nonce] = true;

        Carrier memory carrier = carriers[carrierId];
        require(carrier.isActive, "Carrier not active or unregistered");

        // Verify EIP-191 signature if provided
        if (signature.length == 65) {
            bytes32 messageHash = keccak256(
                abi.encodePacked(token, carrierId, eventType, timestamp, preNotified, nonce)
            );
            bytes32 ethSignedHash = keccak256(
                abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash)
            );
            address recovered = recoverSigner(ethSignedHash, signature);
            require(recovered == carrier.signerAddress, "Invalid carrier signature");
        } else {
            require(msg.sender == carrier.signerAddress || msg.sender == owner, "Sender must be carrier");
        }

        bytes32 tokenHash = keccak256(token);

        // Check and update pre-notification status
        bool wasPreNotified = preNotified;
        if (hasActivePreNotification(token)) {
            wasPreNotified = true;
            preNotifications[tokenHash].consumed = true;
        }

        SwapEvent memory swap = SwapEvent({
            token: token,
            carrierId: carrierId,
            eventType: eventType,
            timestamp: timestamp,
            preNotified: wasPreNotified,
            notificationRef: notificationRef,
            blockTimestamp: block.timestamp
        });

        latestEvents[tokenHash] = swap;
        eventHistory[tokenHash].push(swap);
        eventCounts[tokenHash] += 1;

        emit SwapRecorded(tokenHash, carrierId, eventType, timestamp, wasPreNotified);
        return tokenHash;
    }

    /**
     * @notice Look up the latest event for a given token hash.
     */
    function getLatestEvent(bytes calldata token)
        external
        view
        returns (
            string memory carrierId,
            string memory eventType,
            uint256 timestamp,
            bool preNotified,
            string memory notificationRef,
            uint256 blockTimestamp
        )
    {
        bytes32 tokenHash = keccak256(token);
        SwapEvent memory e = latestEvents[tokenHash];
        return (e.carrierId, e.eventType, e.timestamp, e.preNotified, e.notificationRef, e.blockTimestamp);
    }

    /**
     * @notice Get all past events for a token.
     */
    function getEventHistory(bytes calldata token) external view returns (SwapEvent[] memory) {
        bytes32 tokenHash = keccak256(token);
        return eventHistory[tokenHash];
    }

    function recoverSigner(bytes32 ethSignedHash, bytes memory signature) internal pure returns (address) {
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (v < 27) {
            v += 27;
        }
        return ecrecover(ethSignedHash, v, r, s);
    }
}
