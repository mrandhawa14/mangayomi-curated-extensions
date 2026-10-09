# Mangayomi Curated Extensions

A checked and deduplicated anime extension index built from several community Mangayomi repositories.

## Add it to Mangayomi

Use this URL as an anime extension repository:

```text
https://raw.githubusercontent.com//mrandhawa14/mangayomi-curated-extensions/main/anime_index.json
```

The intentional double slash returns the same index, but makes older Mangayomi releases use their neutral fallback icon instead of deriving the GitHub owner's profile picture. App [PR #1045](https://github.com/kodjodevf/mangayomi/pull/1045) removes owner avatars directly.

## What "checked" means

Each weekly build verifies that:

- the upstream index is valid JSON;
- the extension source file responds and is not an HTML error page;
- the source website responds and is not a known shutdown placeholder, including a declared Cloudflare challenge;
- inactive, malformed, manually excluded, and lower-priority duplicate entries are omitted.
- known compatibility risks, including 0.8.9 bridge casts and loopback-only helpers, are listed in the health report.

The weekly workflow tests a candidate selection and uploads its health report. It does not automatically replace the published index because streaming sites often block data-center IP addresses even when they work for app users. A refresh also fails safely if an upstream feed is unavailable or the candidate unexpectedly falls below 40 entries.

These checks cannot prove that every search result or video host works. Mangayomi playback tests are still the final verification. See [`health_report.json`](health_report.json) for the latest result and the reason each omitted source was rejected.

The index retains each extension's upstream `sourceCodeUrl`. This avoids republishing third-party code without permission and lets upstream maintainers remain the source of updates.

## Customize the selection

- Edit `sources.json` to add or remove upstream indexes.
- Edit `selection.json` to exclude, override, or explicitly allow a temporarily blocked provider.
- Run `python scripts/build_index.py` to rebuild the index and report.
- Run `python -m unittest discover -s tests -v` to test the builder.

Adult sources remain marked with the upstream `isNsfw` value so Mangayomi can handle them appropriately.

The current selection overrides SFlix, Anime-Sama, FFZY, AniWave, and AniKoto with tested compatibility fixes while their upstream contributions are being reviewed. MoviesFlix is included as an alternate SFlix source with separate site links and the same Movie and TV search and playback support. Anichi and AnimeKai are tested ports from the maintained Yuzono Aniyomi implementations and are being reviewed in [extension PR #14](https://github.com/Mallyd11/mangayomi-anime-extensions/pull/14). CineJoy requires Mangayomi 0.9.9 or newer and depends on the paired [protected-HLS app contribution](https://github.com/kodjodevf/mangayomi/pull/1040). The `all` language KickAssAnime entry is excluded because it enables an unavailable `localhost:8080` proxy by default; the separate direct `en` entry remains available.

## Upstream projects

- [9vsv6/mangayomi-ar-extensions](https://github.com/9vsv6/mangayomi-ar-extensions)
- [gato404/kegareta-sauces](https://github.com/gato404/kegareta-sauces)
- [m2k3a/mangayomi-extensions](https://github.com/m2k3a/mangayomi-extensions)
- [Mallyd11/mangayomi-anime-extensions](https://github.com/Mallyd11/mangayomi-anime-extensions)
- [Swakshan/mangayomi-swak-extensions](https://github.com/Swakshan/mangayomi-swak-extensions)
- [tympanicblock61/mangayomi-extensions](https://github.com/tympanicblock61/mangayomi-extensions)

All extension metadata and code remain attributable to their respective upstream projects. The builder and automation in this repository are released under the MIT License.
