---
name: add-translation
description: Use when adding or changing localized Flutter strings or translation keys; keep English/Arabic resources synchronized and regenerate the configured localization accessors.
---

# Add translation key(s)

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Argument: `$ARGUMENTS` = key + value, free-form. Examples:
- `login.welcomeBack "Welcome back" "مرحبا بعودتك"` — single key with both translations.
- `welcomeBack "Welcome back"` — English only; pick the group and write the Arabic yourself.
- empty — derive the keys from the strings the current task needs.

## Key layout

Detect the layout from the existing `en.json` and mirror it:

- **Grouped (new projects, already-grouped files):** each feature owns a top-level object named by the camelCase of its folder (`lib/feature/order_details/` → `"orderDetails"`). Strings used by more than one feature (Save, Cancel, generic errors, validation messages) live in `"common"`. Keys inside a group are camelCase.
- **Flat (existing file whose keys are all top-level strings):** keep adding flat camelCase keys. Do not nest, regroup or migrate it.

```json
{
  "common": { "save": "Save", "cancel": "Cancel" },
  "login": { "title": "Welcome back", "loginButton": "Login" }
}
```

The easy_localization generator joins nested keys with `_`: `login.title` becomes `LocaleKeys.login_title` (value `'login.title'`). It also emits a constant per group (`LocaleKeys.login`); never call `.tr()` on a group.

## Critical rule

**Both `en.json` and `ar.json` must always contain the same keys in the same structure and order.** A key in one but not the other causes the missing locale to display the raw key string and may break `locale_keys.g.dart` codegen. Never edit one file without the other.

## Configured localization

The steps and generator command below are the easy_localization implementation. For another configured library, preserve key naming and feature grouping where the format nests, complete English/Arabic meaning, collision handling and generated-file ownership; use its actual resource format, accessor and generator from the [localization adaptation contract](../flutter-init/references/package-adaptation.md#localization). Do not create JSON files or LocaleKeys alongside an existing different localization mechanism.

## Steps

1. **Parse the request.** Identify each `(key, en, ar)` triple. Key must be `camelCase` (`loginButton`, `pleaseLoginToContinue`, `enterValidPhoneNumber`). In a grouped file, also pick its group: the owning feature's group, or `common` when the string is shared — reuse an existing `common` key instead of duplicating it in a feature group.

2. **Check for collisions.** Read both `assets/translations/en.json` and `assets/translations/ar.json` and verify the key does not already exist in the target group (or at the top level of a flat file) in either. A new group name must not match an existing top-level key. On a collision, ask the user whether to overwrite or pick a new key.

3. **Write the English and Arabic yourself.** Do not ask the user for translations. If the user supplied a value, use it as given. Otherwise write the English wording, then write a natural Arabic translation of it (Modern Standard Arabic, the same meaning and tone as the English, matching the style of the existing `ar.json` entries). Never put English text in `ar.json` as a placeholder.

4. **Edit both files.** In a grouped file, add the entry inside its group, creating the group object if missing (`common` first, feature groups after it). In a flat file, place it near related keys (e.g., a new validation message near other `*IsRequired` keys). Use the same position in both files. Preserve JSON formatting (2-space indent, trailing comma rules matching the existing file).

5. **Regenerate the keys.** Adding a key includes regenerating `locale_keys.g.dart` — code generation, not a build. If you can run commands and the project's `CLAUDE.md` / `AGENTS.md` does not forbid it, run this from the project root:

   ```
   dart run easy_localization:generate -S assets/translations -O lib/core/l10n -f keys -o locale_keys.g.dart
   ```

   `-O` is the folder that already holds `locale_keys.g.dart` — `lib/core/l10n` in the standard layout. It rewrites only that file, from the JSON; code that uses the new keys then passes `flutter analyze`.

   If you cannot run commands, or the project forbids it, give the user that command, and say that the code using the new keys compiles once it has run.

6. **Show usage.** Print a one-liner showing how to use the new key in code, e.g.:

   ```dart
   Text(LocaleKeys.login_welcomeBack.tr())
   ```

## What NOT to do

- Do not stop to ask the user for the Arabic, and do not leave English placeholders in `ar.json` — translate it yourself.
- Do not reference a `LocaleKeys.xxx` entry in code without adding its key to both JSON files in the same change.
- Do not leave a user-facing string out — a placeholder, a hint, an empty-state line — because its key does not exist yet. Add the key.
- Do not edit `lib/core/l10n/locale_keys.g.dart` by hand — it is generated.
- Do not add keys to only one of the two JSON files.
- Do not reorder or reformat unrelated entries in the JSON files, and do not convert a flat file to groups.
