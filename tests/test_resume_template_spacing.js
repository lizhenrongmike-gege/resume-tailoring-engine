const assert = require("assert");

const { profile } = require("../scripts/resume_template");

for (const [name, spacing] of Object.entries(profile.spacing)) {
  assert.strictEqual(
    spacing.line,
    240,
    `${name} line spacing should be 240 twips for Word single spacing`,
  );
}

console.log("resume_template spacing uses Word single-spacing (240)");
