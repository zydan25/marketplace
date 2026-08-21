import { randomBytes, scryptSync } from "node:crypto";
import { readFileSync } from "node:fs";

const entries = JSON.parse(readFileSync(0, "utf8"));
const hashes = entries.map(({ password }) => {
  const salt = randomBytes(16);
  const key = scryptSync(password, salt, 64);
  return `${salt.toString("hex")}:${key.toString("hex")}`;
});

console.log(JSON.stringify(hashes));
