/** Binary entry point — thin over run() so the CLI itself is testable. */
import { run } from "./cli.js";

process.exitCode = await run(process.argv.slice(2));
