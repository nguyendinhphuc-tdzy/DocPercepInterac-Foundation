/**
 * Validates that frontend/src/contracts/generated/foundation.ts matches
 * the in-memory generation from docs/contracts/foundation.openapi.yaml.
 *
 * This check is strictly side-effect free: it does not modify the working tree.
 */

import { promises as fs } from "node:fs";
import { fileURLToPath } from "node:url";
import { generateContractProjection } from "./generate-contracts.mjs";

const OUTPUT_RELATIVE_PATH = "../src/contracts/generated/foundation.ts";

async function main() {
  try {
    const outputUrl = new URL(OUTPUT_RELATIVE_PATH, import.meta.url);
    const outputPath = fileURLToPath(outputUrl);

    let committedContent = null;
    try {
      committedContent = await fs.readFile(outputPath, "utf8");
    } catch {
      console.error(`Error: Generated contract projection not found at: ${outputPath}`);
      console.error("Run: npm run contracts:generate to generate it.");
      process.exit(1);
    }

    const expectedContent = await generateContractProjection();

    const normalizedCommitted = committedContent.replace(/\r\n/g, "\n");
    const normalizedExpected = expectedContent.replace(/\r\n/g, "\n");

    if (normalizedCommitted !== normalizedExpected) {
      console.error("Error: Frontend contract projection is stale or has drifted from docs/contracts/foundation.openapi.yaml.");
      console.error(`Target file: ${outputPath}`);
      console.error("Run: npm run contracts:generate to update the projection.");
      process.exit(1);
    }

    console.log("Contracts check passed: frontend/src/contracts/generated/foundation.ts is up to date.");
    process.exit(0);
  } catch (err) {
    console.error("Contract drift check failed with an unexpected error:", err);
    process.exit(1);
  }
}

main();
