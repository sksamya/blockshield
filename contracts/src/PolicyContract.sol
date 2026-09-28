// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PolicyContract
 * @notice Governance-controlled risk parameters for consortium SIM-swap verification.
 */
contract PolicyContract {
    address public owner;

    struct PolicyConfig {
        uint256 recentSwapWindow;     // Time window (seconds) where SIM swap increases risk (default: 72 hours = 259200s)
        uint256 preNotifiedWindow;    // Valid window (seconds) for pre-notification (default: 24 hours = 86400s)
        uint256 stepUpThreshold;      // Risk score threshold (0-100) requiring BridgeKey biometric step-up (default: 50)
        uint256 blockThreshold;       // Risk score threshold (0-100) requiring outright transaction block (default: 80)
        bool smsOtpDisallowedOnSwap;  // Whether SMS OTP is strictly refused when recent swap is detected (default: true)
        uint256 highAmountThreshold;  // High value transfer threshold in cents (default: $5000 = 500000)
    }

    PolicyConfig public policy;

    event PolicyUpdated(
        uint256 recentSwapWindow,
        uint256 preNotifiedWindow,
        uint256 stepUpThreshold,
        uint256 blockThreshold,
        bool smsOtpDisallowedOnSwap,
        uint256 highAmountThreshold
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only consortium governance");
        _;
    }

    constructor() {
        owner = msg.sender;
        policy = PolicyConfig({
            recentSwapWindow: 72 hours,
            preNotifiedWindow: 24 hours,
            stepUpThreshold: 50,
            blockThreshold: 80,
            smsOtpDisallowedOnSwap: true,
            highAmountThreshold: 500000 // $5,000.00
        });
    }

    function updatePolicy(
        uint256 recentSwapWindow,
        uint256 preNotifiedWindow,
        uint256 stepUpThreshold,
        uint256 blockThreshold,
        bool smsOtpDisallowedOnSwap,
        uint256 highAmountThreshold
    ) external onlyOwner {
        policy = PolicyConfig({
            recentSwapWindow: recentSwapWindow,
            preNotifiedWindow: preNotifiedWindow,
            stepUpThreshold: stepUpThreshold,
            blockThreshold: blockThreshold,
            smsOtpDisallowedOnSwap: smsOtpDisallowedOnSwap,
            highAmountThreshold: highAmountThreshold
        });

        emit PolicyUpdated(
            recentSwapWindow,
            preNotifiedWindow,
            stepUpThreshold,
            blockThreshold,
            smsOtpDisallowedOnSwap,
            highAmountThreshold
        );
    }

    function getPolicy()
        external
        view
        returns (
            uint256 recentSwapWindow,
            uint256 preNotifiedWindow,
            uint256 stepUpThreshold,
            uint256 blockThreshold,
            bool smsOtpDisallowedOnSwap,
            uint256 highAmountThreshold
        )
    {
        return (
            policy.recentSwapWindow,
            policy.preNotifiedWindow,
            policy.stepUpThreshold,
            policy.blockThreshold,
            policy.smsOtpDisallowedOnSwap,
            policy.highAmountThreshold
        );
    }
}
