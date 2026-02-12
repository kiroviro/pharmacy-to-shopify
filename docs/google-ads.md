# Google Ads Integration

Create and manage Google Ads Performance Max campaigns via the API to drive traffic to the Shopify store.

## Setup

1. **Credentials** -- fill in `config/google-ads.yaml` with:
   - Developer Token (Google Ads -> Tools & Settings -> API Center, requires a Manager/MCC account)
   - OAuth2 Client ID + Secret (Google Cloud Console -> APIs & Services -> Credentials)
   - Customer ID (Google Ads advertiser account, no dashes)
   - Login Customer ID (Manager/MCC account ID, if applicable)
   - Merchant Center ID (merchants.google.com)

   See `config/google-ads.yaml.example` for a template with placeholder values.

2. **Generate refresh token**:
   ```bash
   python3 scripts/google_ads_auth.py
   ```
   This opens a browser for OAuth2 authorization and prints a refresh token to paste into the config.

3. **Create a Performance Max campaign**:
   ```bash
   # Validate config without creating anything
   python3 scripts/google_ads_pmax.py --dry-run

   # Create campaign with custom daily budget
   python3 scripts/google_ads_pmax.py --budget 5.00
   ```

## What the Campaign Script Creates

- **Campaign budget** -- daily budget (default $20, configurable via `--budget`)
- **Performance Max campaign** -- linked to Merchant Center product feed, using Maximize Conversion Value bidding
- **Asset group** -- with `viapharma.us` as the landing page
- **Text assets** -- 5 headlines, 2 long headlines, 4 descriptions in Bulgarian, business name
- **Listing group filter** -- includes all products from the Merchant Center feed
- **Target market** -- Bulgaria (Bulgarian language ads)

The campaign is created in **PAUSED** state. Review it in the Google Ads UI, add image assets (logo, marketing images), and enable when ready.

## Google Ads Policy Note

Google has strict policies on pharmaceutical advertising. Vitamins, supplements, and cosmetics are generally allowed. Prescription drugs and certain OTC medicines may require LegitScript certification.
