/** @type {import('@commitlint/types').UserConfig} */
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Allow conventional commit types used in this project
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "refactor",
        "docs",
        "test",
        "chore",
        "perf",
        "ci",
        "revert",
        "style",
        "build",
      ],
    ],
    // Keep subject line under 70 chars (project convention)
    "header-max-length": [2, "always", 70],
    // Subject case: lower-case allowed (common in this repo)
    "subject-case": [0],
  },
};
