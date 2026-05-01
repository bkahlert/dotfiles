# Typing Guidelines

Avoid primitive obsession. Do not default to `string`, `number`, or `boolean` when a more descriptive general-purpose or domain-specific type exists.

- **General Purpose:** Use `Duration` or `Timestamp` instead of `numMilliseconds` or `epochSeconds`.
- **Business Domains:** Use semantic types like `InternationalBankAccountNumber` (IBAN), `VehicleIdentificationNumber` (VIN), or `CurrencyCode` instead of
  generic strings.
- **Validation:** Favor types that imply structural constraints or units of measure to improve clarity and reduce logic errors.
