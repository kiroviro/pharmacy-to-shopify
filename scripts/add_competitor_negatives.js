/**
 * ViaPharma DSA — Add competitor brand & unrelated category negatives
 *
 * Paste into: Google Ads → Tools → Scripts → + New script → Run
 *
 * Adds 9 terms × 2 match types (exact + phrase) = 18 negative keywords.
 *
 * Note: фрамар + framar were added by the initial optimization script run
 * (2026-04-02) and are NOT repeated here to avoid duplicates.
 */

var CAMPAIGN_NAME = "ViaPharma DSA";

function main() {
  var campaign = getCampaign();
  if (!campaign) {
    Logger.log("ERROR: Campaign '" + CAMPAIGN_NAME + "' not found!");
    return;
  }

  Logger.log("Found campaign: " + campaign.getName() + " (ID: " + campaign.getId() + ")");
  addNegatives(campaign);
  Logger.log("\nDone.");
}

function getCampaign() {
  var iterator = AdsApp.campaigns()
    .withCondition("campaign.name = '" + CAMPAIGN_NAME + "'")
    .get();
  return iterator.hasNext() ? iterator.next() : null;
}

function addNegatives(campaign) {
  var terms = [
    // Competitor pharmacy chains (Bulgaria)
    "galen",
    "галена",
    "galena",
    "гален",
    "benu",
    "софарма",

    // Unrelated product category — medical/fashion earrings
    "медицински обеци",
  ];

  Logger.log("\nAdding " + terms.length + " terms × 2 match types = " + (terms.length * 2) + " negatives:");

  for (var i = 0; i < terms.length; i++) {
    var term = terms[i];
    campaign.createNegativeKeyword("[" + term + "]");  // exact match
    campaign.createNegativeKeyword('"' + term + '"');   // phrase match
    Logger.log("  + [" + term + "]  +  \"" + term + "\"");
  }
}
