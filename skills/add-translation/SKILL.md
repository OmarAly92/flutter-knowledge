---
name: add-translation
description: Add one or more localization keys to both assets/translations/en.json and assets/translations/ar.json in sync, then regenerate lib/core/helpers/localization/locale_keys.g.dart. Use when the user asks to add a translation, add a string, add a new key, or wire up a new label/error message in the UI.
---

# Add translation key(s)

Argument: `$ARGUMENTS` = key + value, free-form. Examples:
- `welcomeBack "Welcome back" "مرحبا بعودتك"` — single key with both translations.
- `welcomeBack "Welcome back"` — English only; ask the user for the Arabic.
- empty — ask the user for keys to add.

## Critical rule

**Both `en.json` and `ar.json` must always contain the same set of keys.** A key in one but not the other causes the missing locale to display the raw key string and may break `locale_keys.g.dart` codegen. Never edit one file without the other.

## Steps

1. **Parse the request.** Identify each `(key, en, ar)` triple. Key must be `camelCase` (matches existing convention: `loginButton`, `pleaseLoginToContinue`, `enterValidPhoneNumber`).

2. **Check for collisions.** Read both `assets/translations/en.json` and `assets/translations/ar.json` and verify the key does not already exist in either. If it does, ask the user whether to overwrite or pick a new key.

3. **Ask for any missing Arabic translation.** If the user only supplied English, ask them for the Arabic — do not auto-translate.

4. **Edit both files.** Add the new entry in the same logical location in each file (group related keys together — e.g., put a new validation message near other `*IsRequired` keys). Preserve JSON formatting (2-space indent, trailing comma rules matching the existing file). Both files must remain in the same key order.

5. **Regenerate codegen.** Tell the user to run:

   ```
   flutter pub run easy_localization:generate -S assets/translations -O lib/core/helpers/localization -f keys -o locale_keys.g.dart
   ```

   (or just `flutter pub get` if their setup regenerates on pub get). Do not run this yourself — leave it to the user, since it touches generated files and requires their toolchain.

6. **Show usage.** Print a one-liner showing how to use the new key in code, e.g.:

   ```dart
   Text(LocaleKeys.welcomeBack.tr())
   ```

## What NOT to do

- Do not auto-translate Arabic from English. Ask the user.
- Do not edit `lib/core/helpers/localization/locale_keys.g.dart` by hand — it is generated.
- Do not add keys to only one of the two JSON files.
- Do not reorder or reformat unrelated entries in the JSON files.
