# Maintenance

- This repository maintains a local safety patch for PDFMathTranslate Next 2.9.0 and BabelDOC 0.6.4; do not silently apply it to another release.
- Installed tools and private settings belong in persistent locations outside this checkout. Reuse them across projects.
- Never commit API keys, account settings, user PDFs, translation outputs, asset bundles or runtimes.
- Preserve upstream AGPL notices. Update patch payloads, review diffs and the hash manifest together.
- Run `python -m unittest discover -s tests -p test_patch_manager.py` after deployment changes; run `scripts/Test.ps1` against the persistent installation after translator changes.
- Keep the README and deployment/rollback instructions current. Commit and push validated engineering changes to the user's GitHub repository.
