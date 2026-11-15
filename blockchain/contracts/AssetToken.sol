// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Capped} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Capped.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title AssetToken
/// @notice ERC-20 representing fictional economic participation in ONE real-world asset.
/// @dev Educational only. Tokens carry no legal ownership of the underlying asset.
contract AssetToken is ERC20, ERC20Capped, Ownable {
    /// @notice Off-chain identifier of the tokenized asset (e.g. "ASSET-001").
    string public assetId;

    event AssetMinted(string assetId, address indexed to, uint256 amount);

    constructor(
        string memory name_,
        string memory symbol_,
        string memory assetId_,
        uint256 cap_,
        address owner_
    ) ERC20(name_, symbol_) ERC20Capped(cap_) Ownable(owner_) {
        assetId = assetId_;
    }

    /// @notice Mints tokens up to the immutable cap. Owner only.
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
        emit AssetMinted(assetId, to, amount);
    }

    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Capped) {
        super._update(from, to, value);
    }
}
