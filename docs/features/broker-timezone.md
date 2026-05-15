# Broker timezone

## What it is

Each trading account has a **broker timezone** setting. It describes the timezone your broker uses when stamping open and close times in exported journals (for example MetaTrader Excel or CSV exports), not necessarily where you live.

Common values are fixed offsets such as `UTC+2` or `UTC+3`, or an IANA region name such as `Europe/Berlin` if your broker aligns with a named zone.

## Why it matters

Brokers record trade times in **their** server clock. TradingCoach stores those moments as true UTC in the database, then uses your account's broker timezone whenever analytics need to match **your** trading day, hour, or weekday. Session labels (Asian, London, New York) are derived separately from global market clocks so they stay aligned with real session boundaries, including daylight saving.

Without the correct broker timezone, hour-of-day and day-of-week breakdowns can shift by several hours relative to what you see in your terminal.

## What you see

- **Dashboard and reports:** P&L by hour, by weekday, overtrading days, and the equity curve by calendar day reflect your broker timezone when an account is selected.
- **Trading sessions:** Session breakdowns (Asian / London / New York) follow standard market session windows with daylight saving handled automatically.
- **Coaching and calendar context:** Trade-to-news and trade-to-event matching uses stored UTC times; your broker timezone still drives which trades fall on which calendar day for day-based rules.

## Setting it

Set broker timezone when you create an account. Use the offset or region that matches your broker's server time in the export file, not your local PC clock unless they are the same.

## Related

- Architecture: `docs/decisions/005-utc-timestamp-convention.md`
- Economic calendar (news matching): `docs/prd/economic-calendar.md`
