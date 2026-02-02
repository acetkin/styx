# Privacy Policy — STYX Action (for Kharon)

This GPT Action calls the STYX API at https://styx-api-iota.vercel.app to compute astrology charts and timelines.

## Data processed
- User-provided inputs sent to STYX only when needed: chart type, timestamps, and location (as a place name or coordinates).
- STYX responses returned to the GPT: calculated chart data (angles, houses, bodies, aspects, etc.) and error messages if any.

## Data storage
- This Action does not intentionally store personal data on its own.
- The STYX API may generate technical logs (e.g., request IDs, timing/latency) for debugging and reliability.

## Data sharing
- Data is sent only to the STYX API for computation. No other third parties are intended.

## User control
- Users can avoid sending location or timestamps by not requesting calculations that require them.
- If inputs are missing, the GPT will ask the user rather than guessing.

## Contact
For questions, contact the repository owner via GitHub: https://github.com/acetkin
