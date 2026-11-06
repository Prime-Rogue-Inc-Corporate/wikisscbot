// Shared setup for the collection scripts.
//
// Environment:
//   SOLANA_CLUSTER   devnet (default) or mainnet-beta
//   SOLANA_RPC_URL   optional RPC endpoint (defaults to the public one for the cluster)
//   SOLANA_KEYPAIR   the minting wallet's secret key as a JSON array of 64 numbers
//                    (the format `solana-keygen` writes). Keep it in a GitHub secret.

import { readFileSync, writeFileSync, existsSync, appendFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createUmi } from "@metaplex-foundation/umi-bundle-defaults";
import { keypairIdentity } from "@metaplex-foundation/umi";
import { mplBubblegum } from "@metaplex-foundation/mpl-bubblegum";
import { mplCore } from "@metaplex-foundation/mpl-core";

export const HERE = dirname(fileURLToPath(import.meta.url));
export const NFT = join(HERE, "..");
export const ROOT = join(NFT, "..");
export const CONFIG = JSON.parse(readFileSync(join(NFT, "config.json"), "utf8"));

export const CLUSTER = process.env.SOLANA_CLUSTER || "devnet";
if (!["devnet", "mainnet-beta"].includes(CLUSTER)) {
  throw new Error(`SOLANA_CLUSTER must be devnet or mainnet-beta, not ${CLUSTER}`);
}
const DEFAULT_RPC = { devnet: "https://api.devnet.solana.com", "mainnet-beta": "https://api.mainnet-beta.solana.com" };

export const STATE_PATH = join(NFT, `state.${CLUSTER}.json`);
export const LEDGER_PATH = join(NFT, `minted.${CLUSTER}.jsonl`);

export function makeUmi() {
  const raw = process.env.SOLANA_KEYPAIR;
  if (!raw) throw new Error("SOLANA_KEYPAIR is not set (JSON array of the wallet's 64-byte secret key)");
  const umi = createUmi(process.env.SOLANA_RPC_URL || DEFAULT_RPC[CLUSTER]).use(mplBubblegum()).use(mplCore());
  const kp = umi.eddsa.createKeypairFromSecretKey(new Uint8Array(JSON.parse(raw)));
  umi.use(keypairIdentity(kp));
  return umi;
}

export function baseUrl() {
  const b = CONFIG.base_url.replace(/\/+$/, "");
  if (b.includes("YOUR-DOMAIN")) {
    throw new Error("Set base_url in nft/config.json to where docs/nft is published before minting");
  }
  return b;
}

export function readState() {
  return existsSync(STATE_PATH) ? JSON.parse(readFileSync(STATE_PATH, "utf8")) : null;
}

export function writeState(state) {
  writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + "\n");
}

export function readJsonl(path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
}

export function appendLedger(row) {
  appendFileSync(LEDGER_PATH, JSON.stringify(row) + "\n");
}

export async function solBalance(umi) {
  const b = await umi.rpc.getBalance(umi.identity.publicKey);
  return Number(b.basisPoints) / 1e9;
}

export function explorer(kind, id) {
  const q = CLUSTER === "devnet" ? "?cluster=devnet" : "";
  return `https://explorer.solana.com/${kind}/${id}${q}`;
}
