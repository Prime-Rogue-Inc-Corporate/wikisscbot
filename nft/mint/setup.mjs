// One-time setup per cluster: create the Metaplex Core collection (with the
// BubblegumV2 plugin) and the Bubblegum v2 Merkle tree the cards are minted into.
// Writes nft/state.<cluster>.json. Refuses to run twice.

import { generateSigner } from "@metaplex-foundation/umi";
import { createTreeV2 } from "@metaplex-foundation/mpl-bubblegum";
import { createCollection } from "@metaplex-foundation/mpl-core";
import { CLUSTER, CONFIG, STATE_PATH, baseUrl, explorer, makeUmi, readState, solBalance, writeState } from "./common.mjs";

if (readState()) {
  console.log(`Already set up on ${CLUSTER}: ${STATE_PATH}. Nothing to do.`);
  process.exit(0);
}

const umi = makeUmi();
const base = baseUrl();
console.log(`cluster ${CLUSTER}, wallet ${umi.identity.publicKey}, balance ${await solBalance(umi)} SOL`);

const collection = generateSigner(umi);
await createCollection(umi, {
  collection,
  name: CONFIG.collection_name.slice(0, 32),
  uri: `${base}/collection.json`,
  plugins: [{ type: "BubblegumV2" }],
}).sendAndConfirm(umi);
console.log(`collection ${collection.publicKey}  ${explorer("address", collection.publicKey)}`);

const tree = generateSigner(umi);
const { max_depth, max_buffer_size, canopy_depth } = CONFIG.tree;
await (await createTreeV2(umi, {
  merkleTree: tree,
  maxDepth: max_depth,
  maxBufferSize: max_buffer_size,
  canopyDepth: canopy_depth,
  public: false,
})).sendAndConfirm(umi);
console.log(`tree ${tree.publicKey} (capacity ${2 ** max_depth})  ${explorer("address", tree.publicKey)}`);

writeState({
  cluster: CLUSTER,
  created: new Date().toISOString(),
  authority: umi.identity.publicKey.toString(),
  collection: collection.publicKey.toString(),
  merkle_tree: tree.publicKey.toString(),
  tree: CONFIG.tree,
  capacity: 2 ** max_depth,
});
console.log(`saved ${STATE_PATH}; balance now ${await solBalance(umi)} SOL`);
