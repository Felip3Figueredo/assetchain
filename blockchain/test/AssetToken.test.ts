import { expect } from "chai";
import { ethers } from "hardhat";

const CAP = ethers.parseEther("10000000");

async function deployFixture() {
  const [owner, alice, bob] = await ethers.getSigners();
  const Token = await ethers.getContractFactory("AssetToken");
  const token = await Token.deploy("Usina Solar Alpha", "SOLA", "ASSET-001", CAP, owner.address);
  await token.waitForDeployment();
  return { token, owner, alice, bob };
}

describe("AssetToken", () => {
  it("deploys with name, symbol, assetId, cap and owner", async () => {
    const { token, owner } = await deployFixture();
    expect(await token.name()).to.equal("Usina Solar Alpha");
    expect(await token.symbol()).to.equal("SOLA");
    expect(await token.assetId()).to.equal("ASSET-001");
    expect(await token.cap()).to.equal(CAP);
    expect(await token.owner()).to.equal(owner.address);
    expect(await token.totalSupply()).to.equal(0n);
  });

  it("mints the initial supply to the treasury and emits AssetMinted", async () => {
    const { token, owner, alice } = await deployFixture();
    await expect(token.mint(alice.address, CAP))
      .to.emit(token, "AssetMinted")
      .withArgs("ASSET-001", alice.address, CAP);
    expect(await token.balanceOf(alice.address)).to.equal(CAP);
    expect(await token.totalSupply()).to.equal(CAP);
    void owner;
  });

  it("transfers between wallets and emits Transfer", async () => {
    const { token, alice, bob } = await deployFixture();
    await token.mint(alice.address, CAP);
    const amount = ethers.parseEther("100000");
    await expect(token.connect(alice).transfer(bob.address, amount))
      .to.emit(token, "Transfer")
      .withArgs(alice.address, bob.address, amount);
    expect(await token.balanceOf(bob.address)).to.equal(amount);
    expect(await token.balanceOf(alice.address)).to.equal(CAP - amount);
  });

  it("reverts a transfer without enough balance", async () => {
    const { token, alice, bob } = await deployFixture();
    await expect(token.connect(alice).transfer(bob.address, 1n))
      .to.be.revertedWithCustomError(token, "ERC20InsufficientBalance");
  });

  it("reverts minting above the cap", async () => {
    const { token, alice } = await deployFixture();
    await token.mint(alice.address, CAP);
    await expect(token.mint(alice.address, 1n))
      .to.be.revertedWithCustomError(token, "ERC20ExceededCap");
  });

  it("reverts minting by a non-owner", async () => {
    const { token, alice } = await deployFixture();
    await expect(token.connect(alice).mint(alice.address, 1n))
      .to.be.revertedWithCustomError(token, "OwnableUnauthorizedAccount");
  });
});
