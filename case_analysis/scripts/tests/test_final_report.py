from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from final_check import check_final  # noqa: E402
from slack_notify import _extract_final_parts, build_final_blocks  # noqa: E402

CONFIRMED_HOW = """1. Open the index in Admin UI.
2. Rerun the 14 Oct job.
3. Check the level shows on the website."""

LIKELY_HOW = "Not given yet — we are not 100% sure. Reuters must confirm the corrected price."

CONFIRMED_DRAFT = """Problem: The 14 Oct level was not published because the price file came late.

What we recommend: Support reruns the 14 Oct job today.

Why:
- The price file arrived after the job ran.
- The file is complete now.

How to do it: 1. Open the index. 2. Rerun 14 Oct. 3. Check the website."""

LIKELY_DRAFT = """Problem: The 14 Oct level may be wrong because the vendor price changed.

What we recommend: Change nothing yet. Ask Reuters to confirm the corrected price.

Why:
- The vendor sent a new price after we published."""


def build_final(certainty: str, how: str, draft: str) -> str:
    return f"""# PES-1 — Case Analysis

## What happened
The 14 Oct level was not published. The price file came late.

## Who is affected
- **Client impact:** values delayed
- **Scope:** one index

## Decision
- **Call:** ops fix today
- **Owner:** support
- **Certainty:** {certainty}
- **What would change this:** nothing outstanding

## What we recommend
Support reruns the 14 Oct job today.

## Why we think this
- The price file arrived after the job ran.

## How to do it
{how}

## Do not do
- Do not restate other dates.

## If this is not closed today
- support

## Decision needed from a human
- none

## Draft Jira comment
```text
{draft}
```

## Technical detail (for PE)

### Our understanding of the issue
Late vendor file.

### Possibilities checked
| Possibility | How we checked | Result |
| --- | --- | --- |
| Job bug | Logs | ruled out |

### What we could not check
- None
"""


class FinalCheckTests(unittest.TestCase):
    def test_confirmed_report_with_steps_passes(self) -> None:
        result = check_final(build_final("confirmed", CONFIRMED_HOW, CONFIRMED_DRAFT))
        self.assertEqual(result.errors, [])

    def test_likely_report_without_steps_passes(self) -> None:
        result = check_final(build_final("likely", LIKELY_HOW, LIKELY_DRAFT))
        self.assertEqual(result.errors, [])

    def test_steps_are_rejected_when_not_confirmed(self) -> None:
        result = check_final(build_final("likely", CONFIRMED_HOW, CONFIRMED_DRAFT))
        self.assertIn(
            "How to do it has step-by-step instructions but Certainty is not confirmed",
            result.errors,
        )
        self.assertIn(
            "Draft Jira comment gives 'How to do it' but Certainty is not confirmed",
            result.errors,
        )

    def test_missing_headings_and_draft_labels_are_errors(self) -> None:
        markdown = build_final("confirmed", CONFIRMED_HOW, "Just some text").replace(
            "### Possibilities checked", "### Other"
        )
        result = check_final(markdown)
        self.assertIn("missing heading: ### Possibilities checked", result.errors)
        self.assertIn("Draft Jira comment is missing 'Problem:'", result.errors)

    def test_jargon_and_long_problem_are_warnings_only(self) -> None:
        markdown = build_final("confirmed", CONFIRMED_HOW, CONFIRMED_DRAFT).replace(
            "The price file came late.",
            "The price file came late. It was 0b1e2c3d-1111-2222-3333-444455556666. Then it failed.",
        )
        result = check_final(markdown)
        self.assertEqual(result.errors, [])
        self.assertIn("What happened is longer than 2 sentences", result.warnings)
        self.assertIn("## What happened contains a UUID", result.warnings)


class SlackFinalBlocksTests(unittest.TestCase):
    def _blocks_text(self, markdown: str) -> str:
        with tempfile.TemporaryDirectory() as temporary_directory:
            final_path = Path(temporary_directory) / "FINAL.md"
            final_path.write_text(markdown, encoding="utf-8")
            blocks = build_final_blocks(final_path, "PES-1", "completed")
        return "\n".join(block.get("text", {}).get("text", "") for block in blocks)

    def test_confirmed_report_shows_recommendation_why_and_how(self) -> None:
        text = self._blocks_text(build_final("confirmed", CONFIRMED_HOW, CONFIRMED_DRAFT))
        self.assertIn("What we recommend", text)
        self.assertIn("Why we think this", text)
        self.assertIn("How to do it", text)
        self.assertIn("Problem: The 14 Oct level", text)

    def test_unconfirmed_report_hides_how_to_do_it(self) -> None:
        text = self._blocks_text(build_final("likely", LIKELY_HOW, LIKELY_DRAFT))
        self.assertNotIn("How to do it", text)

    def test_legacy_do_now_is_still_shown(self) -> None:
        legacy = "# PES-1\n\n## What happened\nLate file.\n\n## Do now\n1. Rerun the job.\n"
        with tempfile.TemporaryDirectory() as temporary_directory:
            final_path = Path(temporary_directory) / "FINAL.md"
            final_path.write_text(legacy, encoding="utf-8")
            parts = _extract_final_parts(final_path)
        self.assertEqual(parts["recommend"], "1. Rerun the job.")


if __name__ == "__main__":
    unittest.main()
