#!/usr/bin/env bun
import { defineCommand, runMain } from "citty";
import pkg from "../package.json";
import { archiveCommand } from "./commands/archive";
import { contextCommand } from "./commands/context";
import { hookCommand } from "./commands/hook";
import { initCommand } from "./commands/init";
import { listCommand } from "./commands/list";
import { newCommand } from "./commands/new";
import { pathCommand } from "./commands/path";
import { validateCommand } from "./commands/validate";

const main = defineCommand({
  meta: {
    name: "spec",
    version: pkg.version,
    description: "Spec-driven development CLI for managing specifications",
  },
  args: {
    root: {
      type: "string",
      alias: "r",
      description: "Project root directory (default: auto-detect by walking up to find .specs/)",
    },
    plain: {
      type: "boolean",
      description: "Human-readable output instead of JSON (JSON is default)",
    },
  },
  subCommands: {
    init: initCommand,
    new: newCommand,
    context: contextCommand,
    path: pathCommand,
    list: listCommand,
    archive: archiveCommand,
    validate: validateCommand,
    hook: hookCommand,
  },
});

runMain(main);
