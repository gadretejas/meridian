import { defineCommand } from "citty";
import { validateFeature } from "../lib/validator";
import { error, note, success, warn } from "../ui/output";

export const validateCommand = defineCommand({
  meta: {
    name: "validate",
    description: "Validate specification files for completeness",
  },
  args: {
    specDir: {
      type: "positional",
      description: "Path to spec directory (e.g., .specs/active/my-feature/)",
      required: true,
    },
    plain: {
      type: "boolean",
      description: "Human-readable output instead of JSON",
    },
    quiet: {
      type: "boolean",
      alias: "q",
      description: "Minimal output (pass/fail + error count only)",
    },
  },
  async run({ args }) {
    const specDir = args.specDir as string;
    const usePlain = args.plain as boolean;
    const quiet = args.quiet as boolean;

    const result = validateFeature(specDir);

    // JSON is default
    if (!usePlain && !quiet) {
      console.log(JSON.stringify(result, null, 2));
      process.exit(result.ok ? 0 : 1);
    }

    // Quiet mode
    if (quiet) {
      if (!usePlain) {
        // JSON quiet mode
        console.log(
          JSON.stringify({
            ok: result.ok,
            errorCount: result.errors.length,
            warningCount: result.warnings.length,
          }),
        );
      } else {
        if (result.ok) {
          console.log(
            `PASS ${result.warnings.length > 0 ? `(${result.warnings.length} warnings)` : ""}`,
          );
        } else {
          console.log(`FAIL (${result.errors.length} errors)`);
        }
      }
      process.exit(result.ok ? 0 : 1);
    }

    // Human-readable output (--plain flag)
    console.log(`Validating: ${specDir}`);
    console.log("=".repeat(50));

    for (const msg of result.errors) {
      error(msg.message);
    }

    for (const msg of result.warnings) {
      warn(msg.message);
    }

    for (const msg of result.info) {
      note(msg.message);
    }

    console.log("=".repeat(50));

    if (result.ok) {
      success("Validation passed");
      if (result.warnings.length > 0) {
        console.log(`   (${result.warnings.length} warnings)`);
      }
      process.exit(0);
    } else {
      error(`Validation failed (${result.errors.length} errors)`);
      process.exit(1);
    }
  },
});
