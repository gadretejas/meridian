// ANSI color codes
const colors = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
  gray: "\x1b[90m",
} as const;

// Check if colors are supported
const useColors = process.stdout.isTTY && !process.env.NO_COLOR;

function colorize(text: string, color: keyof typeof colors): string {
  return useColors ? `${colors[color]}${text}${colors.reset}` : text;
}

export function success(message: string): void {
  console.log(colorize(`✓ ${message}`, "green"));
}

export function error(message: string): void {
  console.error(colorize(`✗ ${message}`, "red"));
}

export function warn(message: string): void {
  console.warn(colorize(`⚠ ${message}`, "yellow"));
}

export function info(message: string): void {
  console.log(`  ${message}`);
}

export function note(message: string): void {
  console.log(colorize(`ℹ ${message}`, "cyan"));
}

export function printHeader(title: string): void {
  const line = "═".repeat(60);
  console.log(colorize(line, "bold"));
  console.log(colorize(title, "bold"));
  console.log(colorize(line, "bold"));
}

export function printDivider(label: string): void {
  console.log();
  console.log(colorize(`▸ ${label}`, "bold"));
  console.log(colorize("─".repeat(50), "gray"));
}

export function printTable(rows: string[][], columnWidths: number[]): void {
  for (const row of rows) {
    const formatted = row.map((cell, i) => cell.padEnd(columnWidths[i] || 20)).join(" ");
    console.log(`  ${formatted}`);
  }
}
