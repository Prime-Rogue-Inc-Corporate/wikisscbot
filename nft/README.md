# GC Wiki Edits: Collector's Edition (satire)

Every eligible edit in the archive becomes a trading card, minted as a compressed NFT on Solana (Metaplex Bubblegum v2). It's a joke, and the cards say so.

## What a card contains

- Card number, page title, the edit summary, date, wiki, byte change, rarity
- A **fictional character** standing for the network gateway (`characters.json`), plus the network label
- A link to the diff on Wikipedia

**Never on a card or in its metadata:** the IP address. Addresses inside edit summaries (e.g. "Undid revision … by 1.2.3.4") are replaced with `[address]`.

**Never made into a card:**
- Edits listed in `skip.txt` (by revision or by page)
- Edits from small offices (`skip_labels_on_biographies` in `config.json`, currently the House of Commons and the Senate) to pages Wikimedia classifies as biographies, so no card points at one MP's office
- User and talk pages (only article-like namespaces in `config.json`)

Adding something to `skip.txt` later withdraws its card. The image and metadata files are deleted, so a minted card's metadata stops resolving.

Rarity: **Legendary** = reverted and 1,000+ bytes; **Rare** = reverted, or 2,000+ bytes; **Uncommon** = 300+ bytes; **Common** = everything else.

## How it works

1. `python nft/cards.py [ahead]` registers new edits in `registry.jsonl`. Card numbers are permanent and run oldest first. It writes `docs/nft/<n>.svg` and `<n>.json` for minted cards plus the next batch, so the published folder grows with the collection.
2. `nft/mint/setup.mjs` (once per cluster) creates the Metaplex Core collection and a Merkle tree for 32,768 cards (a one-time rent of well under 1 SOL; the log prints the balance before and after). It records them in `state.<cluster>.json`.
3. `nft/mint/mint.mjs [limit]` mints the next cards in order into the collection wallet. Each success is logged to `minted.<cluster>.jsonl` straight away, so interrupted runs resume.

The **NFT collection** workflow runs all three on GitHub Actions and commits the results.

## Setup

1. **Wallet.** Make a new wallet used only for this, e.g. `solana-keygen new -o gcedit.json`, or export a fresh Phantom account. Add the secret key (the JSON array from `solana-keygen`, or the base58 string Phantom exports) as the repository secret **`SOLANA_KEYPAIR`**. Never reuse a wallet that holds anything else.
2. **Base URL.** Set `base_url` in `nft/config.json` to where `docs/nft/` is published, e.g. `https://yourdomain/nft`. Minting refuses to run while it says `YOUR-DOMAIN`.
3. **Try devnet first.** Fund the wallet with free devnet SOL (faucet.solana.com). Run the workflow with *cluster: devnet, action: setup*, then *action: mint, limit: 20*, and check the cards on the Solana Explorer links in the log.
4. **Mainnet.** Send ~1 SOL to the wallet (tree rent plus fees for the whole archive with room to spare). Run *mainnet-beta / setup* once, then *mint* in batches. 400 per run is the default; the archive is ~13,500 cards, so about 34 runs.
5. **Optional daily automint:** set the repository variables `NFT_AUTOMINT=true` and `NFT_CLUSTER=mainnet-beta`.
6. **Optional:** add a private RPC (Helius, QuickNode, etc.) as the secret `SOLANA_RPC_URL`. The public endpoints rate-limit bulk minting.

## Selling for pennies

The workflow mints every card to the collection wallet. Two ways to sell:

- **List on a marketplace** (Magic Eden or Tensor, which support compressed NFTs) at a few cents each. This is the simplest option, but the marketplace takes its fee.
- **Your own mint page:** a small Cloudflare Worker that takes a few-cent SOL payment and transfers the next card to the buyer. Not built yet.

## Licence and framing

Page titles and edit summaries come from Wikimedia projects under CC BY-SA 4.0, credited on every card. Characters are fictional composites of shared government network gateways. An edit from a government network is not evidence of who made it, and the cards never claim otherwise.
