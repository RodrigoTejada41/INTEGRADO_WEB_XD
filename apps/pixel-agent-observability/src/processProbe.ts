import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

export async function detectPixelProcesses(): Promise<string[]> {
  const platform = process.platform;
  try {
    if (platform === "win32") {
      const { stdout } = await execAsync("tasklist");
      return stdout
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.toLowerCase().includes("pixel"))
        .map((line) => line.split(/\s+/)[0])
        .filter(Boolean);
    }

    const { stdout } = await execAsync("ps -eo comm");
    return stdout
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.toLowerCase().includes("pixel"));
  } catch {
    return [];
  }
}

