# Upstream sources

This maintenance repository includes original and modified Python source files from:

- PDFMathTranslate Next 2.9.0: https://github.com/PDFMathTranslate-next/PDFMathTranslate-next
- BabelDOC 0.6.4: https://github.com/funstory-ai/BabelDOC

Both installed packages declare AGPL-3.0. Their original file contents are preserved under `patches/original`, modified files under `patches/patched`, and review diffs under `patches/review`. Local scientific-document safety changes were made on 2026-10-13; see `docs/maintenance.md`.

The pinned official Windows release supplies runtime executables and third-party packages. They are not redistributed in this source repository. The release asset and its checksum are recorded in `release.lock.json`.
