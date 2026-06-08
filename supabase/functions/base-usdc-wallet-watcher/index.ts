import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BASESCAN_API_KEY = Deno.env.get("BASESCAN_API_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

Deno.serve(async () => {
  try {
    if (!BASESCAN_API_KEY) {
      throw new Error("BASESCAN_API_KEY is missing");
    }

    const { data: watcher, error: watcherError } = await supabase
      .from("wallet_chain_watchers")
      .select("*")
      .eq("id", "base_usdc_treasury_watcher")
      .eq("watcher_status", "active")
      .single();

    if (watcherError || !watcher) {
      throw new Error("Active watcher config not found");
    }

    const treasuryAddress = watcher.treasury_wallet_address.toLowerCase();
    const tokenContract = watcher.token_contract_address.toLowerCase();

    const startBlock = watcher.last_checked_block
      ? Number(watcher.last_checked_block) + 1
      : 0;

    const url =
      `${watcher.explorer_api_url}` +
      `?module=account` +
      `&action=tokentx` +
      `&contractaddress=${tokenContract}` +
      `&address=${treasuryAddress}` +
      `&startblock=${startBlock}` +
      `&endblock=999999999` +
      `&sort=asc` +
      `&apikey=${BASESCAN_API_KEY}`;

    const response = await fetch(url);
    const payload = await response.json();

    if (payload.status !== "1" && payload.message !== "No transactions found") {
      throw new Error(`BaseScan error: ${JSON.stringify(payload)}`);
    }

    const txs = Array.isArray(payload.result) ? payload.result : [];

    let inserted = 0;
    let newestBlock = watcher.last_checked_block
      ? Number(watcher.last_checked_block)
      : null;

    for (const tx of txs) {
      const to = String(tx.to || "").toLowerCase();
      const hash = String(tx.hash || "").toLowerCase();

      if (to !== treasuryAddress || !hash) continue;

      const decimals = Number(tx.tokenDecimal || 6);
      const rawValue = Number(tx.value || 0);
      const amount = rawValue / Math.pow(10, decimals);
      const blockNumber = Number(tx.blockNumber || 0);
      const confirmations = Number(tx.confirmations || 0);

      if (confirmations < Number(watcher.min_confirmations || 3)) {
        continue;
      }

      const { error: ingestError } = await supabase.rpc(
        "ingest_wallet_settlement_event",
        {
          p_network: watcher.network,
          p_stablecoin_symbol: watcher.stablecoin_symbol,
          p_tx_hash: hash,
          p_from_wallet: String(tx.from || "").toLowerCase(),
          p_to_wallet: to,
          p_amount_raw: amount,
          p_amount_usd: amount,
          p_block_number: blockNumber,
          p_confirmations: confirmations,
          p_metadata: {
            source: "base_usdc_wallet_watcher",
            basescan: true,
            token_contract: tokenContract,
            block_number: blockNumber,
            timestamp: tx.timeStamp || null
          }
        }
      );

      if (!ingestError) {
        inserted += 1;
      }

      if (newestBlock === null || blockNumber > newestBlock) {
        newestBlock = blockNumber;
      }
    }

    if (newestBlock !== null) {
      await supabase
        .from("wallet_chain_watchers")
        .update({
          last_checked_block: newestBlock,
          updated_at: new Date().toISOString()
        })
        .eq("id", "base_usdc_treasury_watcher");
    }

    return new Response(
      JSON.stringify({
        ok: true,
        scanned: txs.length,
        inserted,
        newestBlock
      }),
      {
        headers: { "content-type": "application/json" }
      }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({
        ok: false,
        error: String(error?.message || error)
      }),
      {
        status: 500,
        headers: { "content-type": "application/json" }
      }
    );
  }
});
