from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
SCRIPT = REPO_DIR / "reorder_playlist.py"


class ReorderPlaylistTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_sorts_newest_first_and_strips_blank_lines(self) -> None:
        sample = textwrap.dedent(
            """\
            #EXTM3U
            #EXTENC:UTF-8
            #PLAYLIST:Example

            #EXTINF:264, Track B

            https://example.test/sotd/2026-03-29-trackb/audio.opus

            #EXTINF:264, Track A
            https://example.test/sotd/2026-03-30-tracka/audio.opus
            """
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "playlist.m3u"
            output_path = Path(tmpdir) / "playlist.sorted.m3u"
            input_path.write_text(sample, encoding="utf-8")

            result = self.run_script(str(input_path), "-o", str(output_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    #EXTM3U
                    #EXTENC:UTF-8
                    #PLAYLIST:Example
                    #EXTINF:264, Track A
                    https://example.test/sotd/2026-03-30-tracka/audio.opus
                    #EXTINF:264, Track B
                    https://example.test/sotd/2026-03-29-trackb/audio.opus
                    """
                ),
            )

    def test_preserves_stable_order_for_same_date(self) -> None:
        sample = textwrap.dedent(
            """\
            #EXTM3U
            #EXTINF:111, First
            https://example.test/sotd-2026-03-30/first.opus
            #EXTINF:222, Second
            https://example.test/2026-03-30-second/second.opus
            """
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "playlist.m3u"
            output_path = Path(tmpdir) / "playlist.sorted.m3u"
            input_path.write_text(sample, encoding="utf-8")

            result = self.run_script(str(input_path), "-o", str(output_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "#EXTINF:111, First\nhttps://example.test/sotd-2026-03-30/first.opus\n"
                "#EXTINF:222, Second\nhttps://example.test/2026-03-30-second/second.opus\n",
                output_path.read_text(encoding="utf-8"),
            )

    def test_sorts_entry_metadata_with_its_track(self) -> None:
        sample = textwrap.dedent(
            """\
            #EXTM3U
            #PLAYLIST:Example
            #EXTIMG:https://example.test/site-cover.jpg
            #EXTIMG:https://example.test/2026-03-01-old/cover.jpg
            #EXTALB:Old
            #EXTINF:111, Old
            https://example.test/2026-03-01-old/audio.opus

            #EXTIMG:https://example.test/2026-03-05-new/cover.jpg
            #EXTALB:New
            #EXTINF:222, New
            https://example.test/2026-03-05-new/audio.opus
            """
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "playlist.m3u"
            output_path = Path(tmpdir) / "playlist.sorted.m3u"
            input_path.write_text(sample, encoding="utf-8")

            result = self.run_script(str(input_path), "-o", str(output_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    #EXTM3U
                    #PLAYLIST:Example
                    #EXTIMG:https://example.test/site-cover.jpg
                    #EXTIMG:https://example.test/2026-03-05-new/cover.jpg
                    #EXTALB:New
                    #EXTINF:222, New
                    https://example.test/2026-03-05-new/audio.opus
                    #EXTIMG:https://example.test/2026-03-01-old/cover.jpg
                    #EXTALB:Old
                    #EXTINF:111, Old
                    https://example.test/2026-03-01-old/audio.opus
                    """
                ),
            )

    def test_fails_when_date_is_missing(self) -> None:
        sample = textwrap.dedent(
            """\
            #EXTM3U
            #EXTINF:111, Bad
            https://example.test/sotd/no-date-here/audio.opus
            """
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "playlist.m3u"
            input_path.write_text(sample, encoding="utf-8")

            result = self.run_script(str(input_path))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("entry 1", result.stderr)
            self.assertIn("no YYYY-MM-DD date found", result.stderr)


if __name__ == "__main__":
    unittest.main()
