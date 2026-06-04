---
name: lanhu-verify-parity
description: "Verify visual and implementation parity for Lanhu design restoration. Use after generating a baseline or implementing Lanhu design code to check schema fidelity, preview PNG match, local asset usage, styling completeness, and framework adaptation risks."
---

# Verify Lanhu Parity

Use this skill to validate that restored UI code still follows Lanhu's schema and visible preview. It is useful both after baseline generation and after target-framework implementation.

## Validation Inputs

Use all available inputs:

- `.schema.json` for authoritative design values
- `.png` preview for visible-frame composition
- `.tokens.txt` for supplemental complex-property checks
- `.image_mapping.json` and `assets/slices/` for image localization
- `restore/parity-report.json` when a static baseline exists
- Target app source files and rendered app screenshots when implementation is complete

## Verification Checklist

Check these before finalizing:

- Fixed dimensions remain fixed where the schema requires them.
- Absolute positions, flex directions, gaps, padding, margins, and alignment match the schema.
- Clipping and overflow behavior matches the visible design.
- Text content, font family, size, weight, line-height, alignment, and color are restored.
- Fills preserve exact `rgba()` values, opacity, gradients, images, and blend-sensitive wrappers.
- Borders, non-uniform radii, multiple shadows, inset shadows, and opacity are complete.
- Local assets render and no Lanhu CDN URL remains in app code.
- Visible elements in the preview PNG exist in the implementation.
- Hidden layers, alternate states, and covered screens are skipped unless the user requested them.
- Components are not over-split; extracted components have a repeated or semantic business boundary.
- Project conventions from `DESIGN.md`, local components, or existing styling patterns are followed.

## Rendered-App Checks

When the target project can run locally, start its dev server and inspect the implemented route or component in a browser. Use screenshots to check:

- No overlapping text or controls.
- No cropped text unless the design clips it.
- Images are visible at expected sizes.
- Mobile or responsive behavior only changes when the target platform requires it or the user asked for it.

For static HTML outputs, a local file or simple HTTP server is enough. For framework apps, use the project's existing dev command and available test scripts.

## Error Recovery

If a mismatch appears:

1. Identify whether the source of truth is schema, official reference code, tokens, preview PNG, or project convention.
2. Fix the smallest affected area instead of rebuilding the full screen.
3. Re-check the same mismatch after the fix.
4. Report intentional adaptations clearly, including the platform reason.

## Final Report

Summarize:

- What was implemented or verified.
- Which checks ran.
- Any known deltas from the Lanhu design.
- Any user-visible limitations, such as unavailable fonts or platform-specific substitutions.
