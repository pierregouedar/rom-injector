# ToS & Compliance Notes

Summary: nothing here violates SteamGridDB or Valve ToS in any meaningful way. The risk profile is identical to every Decky plugin shipping today.

## SteamGridDB — green

- Official v2 API accessed with the user's own key.
- Local disk cache + 7-day negative cache reduces load (aligns with their rate-limit expectations).
- `nsfw=false` filter is always applied.
- No HTML scraping, no auth bypass, no artwork redistribution (assets only applied to the user's local Steam shortcuts).
- SGDB asks for attribution when showing art to end users. Personal-use Library tiles are a grey area; an explicit "Artwork from SteamGridDB" footer in the plugin UI would be a polite addition and has zero cost.

### Deliberately NOT implemented

- Scraping the SGDB preferences HTML page to auto-grab the API key — would violate their ToS and break on every UI change.
- Embedding an iframe of SGDB to intercept cookies — same issue.
- Redistributing cached artwork to other users — redistribution violation.

## Valve / Steam Subscriber Agreement — amber (same as every Decky plugin)

The plugin calls undocumented internal APIs injected into Steam's CEF pages:

- `SteamClient.Apps.AddShortcut`
- `SteamClient.Apps.SetShortcutIcon`
- `SteamClient.Apps.SetShortcutLaunchOptions`
- `SteamClient.Apps.SpecifyCompatTool`
- `SteamClient.Apps.SetCustomArtworkForApp`
- `SteamClient.Apps.RegisterForShortcutList`
- `SteamClient.Apps.RemoveShortcut`
- `collectionStore.CreateCollection` / `AddAppsToCollection`

These are not part of any published Steamworks API surface.

### Why this is fine in practice

- SSA prohibits cheats, bots, reverse-engineering, account manipulation, and payment bypass. None apply here.
- Same techniques power Decky Loader itself, NonSteamLaunchers, Junk Store, SteamGridDB Decky, CSS Loader, Emuchievements, and dozens more.
- Valve knowingly tolerates the Decky ecosystem (3+ years, no enforcement actions) and ships `-cef-enable-debugging` themselves on SteamOS.
- No public binary patching, no `LD_PRELOAD`, no memory editing — all interaction is through Valve's own JS bindings inside the client's built-in browser.

### Real risk

Not legal — **technical**. Valve can rename or remove these methods in any client update, and the plugin breaks until updated. No user data or account is at risk; Steam simply ignores the call.

## No-go list (would break ToS if added)

- Patching `steam.exe` / `steamwebhelper` binaries.
- Injecting DLL/shared-object hooks.
- Automating cart/wishlist actions via the store site.
- Sharing user-downloaded artwork back to a public bucket.
- Monkey-patching `window.SteamClient` with replacements (observation is fine; replacement is reverse-engineering territory).

If any of the above show up in a PR, reject it.

## Recommended polish for a public release

1. Attribution footer in the SGDB panel: "Artwork data provided by [SteamGridDB](https://www.steamgriddb.com)".
2. In-code comment documenting which Steam API version each `SteamClient.Apps.*` method is known to exist in — helps future maintainers when Valve reshuffles.
3. Respect SGDB rate limits explicitly (serial calls are already effectively ~5/s due to network + cache).
