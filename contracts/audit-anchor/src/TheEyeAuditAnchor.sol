// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControlDefaultAdminRules} from
    "@openzeppelin/contracts/access/extensions/AccessControlDefaultAdminRules.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title The Eye Audit Anchor
/// @notice Anchors only non-personal integrity commitments. Never submit PII or content.
/// @dev Deliberately non-upgradeable. Off-chain manifests carry encrypted-storage references.
contract TheEyeAuditAnchor is AccessControlDefaultAdminRules, Pausable {
    bytes32 public constant ANCHOR_ROLE = keccak256("ANCHOR_ROLE");

    error ZeroBatchId();
    error ZeroMerkleRoot();
    error ZeroManifestHash();
    error InvalidSequenceRange(uint64 firstSequence, uint64 lastSequence);
    error InvalidEventCount(uint64 supplied, uint64 expected);
    error InvalidSchemaVersion();
    error BatchAlreadyAnchored(bytes32 batchId);
    error RootAlreadyAnchored(bytes32 merkleRoot);

    struct Anchor {
        bytes32 merkleRoot;
        bytes32 manifestHash;
        uint64 firstSequence;
        uint64 lastSequence;
        uint64 eventCount;
        uint32 schemaVersion;
        uint64 anchoredAt;
        address anchoredBy;
    }

    mapping(bytes32 batchId => Anchor anchor) private _anchors;
    mapping(bytes32 merkleRoot => bytes32 batchId) public batchByRoot;

    event BatchAnchored(
        bytes32 indexed batchId,
        bytes32 indexed merkleRoot,
        bytes32 indexed manifestHash,
        uint64 firstSequence,
        uint64 lastSequence,
        uint64 eventCount,
        uint32 schemaVersion,
        address anchoredBy,
        uint64 anchoredAt
    );

    /// @param adminDelay Delay for transfers of the default admin role.
    /// @param initialAdmin Cold/admin governance identity; not the operational signer.
    /// @param initialAnchor Operator authorized to submit commitments.
    constructor(uint48 adminDelay, address initialAdmin, address initialAnchor)
        AccessControlDefaultAdminRules(adminDelay, initialAdmin)
    {
        _grantRole(ANCHOR_ROLE, initialAnchor);
    }

    /// @notice Persist a single immutable batch commitment.
    function anchorBatch(
        bytes32 batchId,
        bytes32 merkleRoot,
        bytes32 manifestHash,
        uint64 firstSequence,
        uint64 lastSequence,
        uint64 eventCount,
        uint32 schemaVersion
    ) external onlyRole(ANCHOR_ROLE) whenNotPaused {
        if (batchId == bytes32(0)) revert ZeroBatchId();
        if (merkleRoot == bytes32(0)) revert ZeroMerkleRoot();
        if (manifestHash == bytes32(0)) revert ZeroManifestHash();
        if (schemaVersion == 0) revert InvalidSchemaVersion();
        if (lastSequence < firstSequence) revert InvalidSequenceRange(firstSequence, lastSequence);
        uint64 expected = lastSequence - firstSequence + 1;
        if (eventCount == 0 || eventCount != expected) revert InvalidEventCount(eventCount, expected);
        if (_anchors[batchId].anchoredAt != 0) revert BatchAlreadyAnchored(batchId);
        if (batchByRoot[merkleRoot] != bytes32(0)) revert RootAlreadyAnchored(merkleRoot);

        uint64 timestamp = uint64(block.timestamp);
        _anchors[batchId] = Anchor(
            merkleRoot, manifestHash, firstSequence, lastSequence, eventCount,
            schemaVersion, timestamp, msg.sender
        );
        batchByRoot[merkleRoot] = batchId;
        emit BatchAnchored(
            batchId, merkleRoot, manifestHash, firstSequence, lastSequence,
            eventCount, schemaVersion, msg.sender, timestamp
        );
    }

    /// @notice Read an anchored batch; a zero `anchoredAt` means absent.
    function getAnchor(bytes32 batchId) external view returns (Anchor memory) {
        return _anchors[batchId];
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
