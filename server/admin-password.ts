import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";

const KEY_LENGTH = 64;

/** Creates a salted password hash for server-side storage only. */
export function hashAdminPassword(password: string, salt = randomBytes(16)): string {
  const derivedKey = scryptSync(password, salt, KEY_LENGTH);
  return `${salt.toString("hex")}:${derivedKey.toString("hex")}`;
}

/** Compares an entered password without exposing the persisted hash. */
export function verifyAdminPassword(password: string, storedHash: string): boolean {
  const [saltHex, keyHex] = storedHash.split(":");
  if (!saltHex || !keyHex) return false;
  const expected = Buffer.from(keyHex, "hex");
  const derived = scryptSync(password, Buffer.from(saltHex, "hex"), KEY_LENGTH);
  return expected.length === derived.length && timingSafeEqual(expected, derived);
}
