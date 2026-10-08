# Mangayomi Curated Extensions

A checked and deduplicated anime extension index built from several community Mangayomi repositories.

## Add it to Mangayomi

Use this URL as an anime extension repository:

```text
https://raw.githubusercontent.com/mrandhawa14/mangayomi-curated-extensions/main/anime_index.json
```

## What "checked" means

Each weekly build verifies that:

- the upstream index is valid JSON;
- the extension source file responds and is not an HTML error page;
- the source website responds, including a declared Cloudflare challenge;
- inactive, malformed, manually excluded, and lower-priority duplicate entries are omitted.

The weekly workflow tests a candidate selection and uploads its health report. It does not automatically replace the published index because streaming sites often block data-center IP addresses even when they work for app users. A refresh also fails safely if an upstream feed is unavailable or the candidate unexpectedly falls below 40 entries.

These checks cannot prove that every search result or video host works. Mangayomi playback tests are still the final verification. See [`health_report.json`](health_report.json) for the latest result and the reason each omitted source was rejected.

The index retains each extension's upstream `sourceCodeUrl`. This avoids republishing third-party code without permission and lets upstream maintainers remain the source of updates.

## Customize the selection

- Edit `sources.json` to add or remove upstream indexes.
- Edit `selection.json` to exclude, override, or explicitly allow a temporarily blocked provider.
- Run `python scripts/build_index.py` to rebuild the index and report.
- Run `python -m unittest discover -s tests -v` to test the builder.

Adult sources remain marked with the upstream `isNsfw` value so Mangayomi can handle them appropriately.

The current selection overrides SFlix with the tested `ssflix.pro` provider fix, including catalogue and HLS playback compatibility with Mangayomi 0.8.9, while the upstream contribution is being reviewed. The `all` language KickAssAnime entry is excluded because it enables an unavailable `localhost:8080` proxy by default; the separate direct `en` entry remains available.

## Upstream projects

- [9vsv6/mangayomi-ar-extensions](https://github.com/9vsv6/mangayomi-ar-extensions)
- [gato404/kegareta-sauces](https://github.com/gato404/kegareta-sauces)
- [m2k3a/mangayomi-extensions](https://github.com/m2k3a/mangayomi-extensions)
- [Mallyd11/mangayomi-anime-extensions](https://github.com/Mallyd11/mangayomi-anime-extensions)
- [Swakshan/mangayomi-swak-extensions](https://github.com/Swakshan/mangayomi-swak-extensions)
- [tympanicblock61/mangayomi-extensions](https://github.com/tympanicblock61/mangayomi-extensions)

All extension metadata and code remain attributable to their respective upstream projects. The builder and automation in this repository are released under the MIT License.
