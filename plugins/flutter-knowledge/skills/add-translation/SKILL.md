---
name: add-translation
description: Add one or more localization keys to both assets/translations/en.json and assets/translations/ar.json in sync, then regenerate lib/core/l10n/locale_keys.g.dart. Use when the user asks to add a translation, add a string, add a new key, or wire up a new label/error message in the UI.
---

# Add translation key(s)

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Argument: `$ARGUMENTS` = key + value, free-form. Examples:
- `welcomeBack "Welcome back" "مرحبا بعودتك"` — single key with both translations.
- `welcomeBack "Welcome back"` — English only; write the Arabic yourself.
- empty — derive the keys from the strings the current task needs.

## Critical rule

**Both `en.json` and `ar.json` must always contain the same set of keys.** A key in one but not the other causes the missing locale to display the raw key string and may break `locale_keys.g.dart` codegen. Never edit one file without the other.

## Configured localization

The steps and generator command below are the easy_localization implementation. For another configured library, preserve key naming, complete English/Arabic meaning, collision handling and generated-file ownership; use its actual resource format, accessor and generator from the [localization adaptation contract](../flutter-init/references/package-adaptation.md#localization). Do not create JSON files or LocaleKeys alongside an existing different localization mechanism.

## Steps

1. **Parse the request.** Identify each `(key, en, ar)` triple. Key must be `camelCase` (matches existing convention: `loginButton`, `pleaseLoginToContinue`, `enterValidPhoneNumber`).

2. **Check for collisions.** Read both `assets/translations/en.json` and `assets/translations/ar.json` and verify the key does not already exist in either. If it does, ask the user whether to overwrite or pick a new key.

3. **Write the English and Arabic yourself.** Do not ask the user for translations. If the user supplied a value, use it as given. Otherwise write the English wording, then write a natural Arabic translation of it (Modern Standard Arabic, the same meaning and tone as the English, matching the style of the existing `ar.json` entries). Never put English text in `ar.json` as a placeholder.

4. **Edit both files.** Add the new entry in the same logical location in each file (group related keys together — e.g., put a new validation message near other `*IsRequired` keys). Preserve JSON formatting (2-space indent, trailing comma rules matching the existing file). Both files must remain in the same key order.

5. **Regenerate the keys.** Adding a key includes regenerating `locale_keys.g.dart` — code generation, not a build. If you can run commands and the project's `CLAUDE.md` / `AGENTS.md` does not forbid it, run this from the project root:

   ```
   dart run easy_localization:generate -S assets/translations -O lib/core/l10n -f keys -o locale_keys.g.dart
   ```

   `-O` is the folder that already holds `locale_keys.g.dart` — `lib/core/l10n` in the standard layout. It rewrites only that file, from the JSON; code that uses the new keys then passes `flutter analyze`.

   If you cannot run commands, or the project forbids it, give the user that command, and say that the code using the new keys compiles once it has run.

6. **Show usage.** Print a one-liner showing how to use the new key in code, e.g.:

   ```dart
   Text(LocaleKeys.welcomeBack.tr())
   ```

## What NOT to do

- Do not stop to ask the user for the Arabic, and do not leave English placeholders in `ar.json` — translate it yourself.
- Do not reference a `LocaleKeys.xxx` entry in code without adding `xxx` to both JSON files in the same change.
- Do not leave a user-facing string out — a placeholder, a hint, an empty-state line — because its key does not exist yet. Add the key.
- Do not edit `lib/core/l10n/locale_keys.g.dart` by hand — it is generated.
- Do not add keys to only one of the two JSON files.
- Do not reorder or reformat unrelated entries in the JSON files.
