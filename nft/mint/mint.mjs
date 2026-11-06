// Mint the next cards, in card-number order, into the collection.
//
//   node mint.mjs [limit]
//
// Reads nft/registry.jsonl (written by nft/cards.py), skips cards already in
// nft/minted.<cluster>.jsonl and cards whose metadata file was withdrawn, and
// mints up to `limit` (default: mint_limit_per_run in nft/config.json) to the
// collection wallet. Each success is appended to the ledger immediately, so an
// interrupted run resumes where it stopped.

import { existsSync } from "node:fs";
import { join } from "node:path";
import { publicKey } from "@metaplex-foundation/umi";
import { mintV2, parseLeafFromMintV2Transaction } from "@metaplex-foundation/mpl-bubblegum";
import {
  CLUSTER, CONFIG, LEDGER_PATH, NFT, ROOT, appendLedger, baseUrl, explorer, makeUmi, readJsonl, readState, solBalance,
} from "./common.mjs";

const limit = Number(process.argv[2] || CONFIG.mint_limit_per_run);
const state = readState();
if (!state) throw new Error(`Not set up on ${CLUSTER}. Run setup first.`);

const minted = new Set(readJsonl(LEDGER_PATH).map((r) => r.n));
const registry = readJsonl(join(NFT, "registry.jsonl"));
const docs = join(ROOT, "docs", "nft");
const queue = registry
  .filter((r) => !minted.has(r.n) && existsSync(join(docs, `${r.n}.json`)))
  .sort((a, b) => a.n - b.n)
  .slice(0, limit);

if (!queue.length) {
  console.log("Nothing to mint.");
  process.exit(0);
}
if (minted.size + queue.length > state.capacity) {
  throw new Error(`Tree capacity ${state.capacity} would be exceeded; create a larger tree.`);
}

const umi = makeUmi();
const base = baseUrl();
const startBalance = await solBalance(umi);
console.log(`cluster ${CLUSTER}: minting ${queue.length} cards (#${queue[0].n}–#${queue.at(-1).n}); balance ${startBalance} SOL`);
if (startBalance < 0.001) throw new Error("Wallet balance too low to mint");

let ok = 0;
let failed = 0;
for (const r of queue) {
  try {
    const { signature } = await mintV2(umi, {
      leafOwner: umi.identity.publicKey,
      merkleTree: publicKey(state.merkle_tree),
      coreCollection: publicKey(state.collection),
      metadata: {
        name: `GC Edit #${String(r.n).padStart(5, "0")}`,
        symbol: CONFIG.symbol,
        uri: `${base}/${r.n}.json`,
        sellerFeeBasisPoints: CONFIG.seller_fee_basis_points,
        collection: publicKey(state.collection),
        creators: [],
      },
    }).sendAndConfirm(umi);
    let assetId = null;
    try {
      const leaf = await parseLeafFromMintV2Transaction(umi, signature);
      assetId = leaf.id.toString();
    } catch {
      // The mint succeeded; the asset id can be recovered later from the signature.
    }
    const sig = Buffer.from(signature).toString("base64");
    appendLedger({ n: r.n, key: r.key, asset_id: assetId, signature_b64: sig, minted_at: new Date().toISOString() });
    ok++;
    if (ok % 25 === 0) console.log(`  ${ok}/${queue.length}`);
  } catch (err) {
    failed++;
    console.error(`  card #${r.n} failed: ${err.message ?? err}`);
    if (failed >= 5 && ok === 0) throw new Error("Five failures before any success; stopping.");
  }
}
const endBalance = await solBalance(umi);
console.log(`minted ${ok}, failed ${failed}; spent ${(startBalance - endBalance).toFixed(6)} SOL; balance ${endBalance} SOL`);
console.log(`collection: ${explorer("address", state.collection)}`);
