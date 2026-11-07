import { mkdir, copyFile } from "node:fs/promises";
import { spawn } from "node:child_process";

await mkdir("dist/assets", { recursive: true });
await copyFile("index.html", "dist/index.html");
await copyFile("src/js/app.js", "dist/assets/app.js");
const child = spawn(process.execPath, ["./node_modules/tailwindcss/lib/cli.js", "-i", "./src/css/input.css", "-o", "./dist/assets/app.css", "--minify"], { stdio: "inherit" });
const code = await new Promise(resolve => child.on("close", resolve));
if (code !== 0) process.exit(code ?? 1);

