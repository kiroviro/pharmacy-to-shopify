/**
 * ViaPharma DSA Campaign Optimization Script
 *
 * Paste this into Google Ads → Tools → Scripts → New Script → Run
 *
 * What it does:
 * 1. Sets budget to €20/day
 * 2. Adds 50+ negative keywords (research, controlled, competitor queries)
 * 3. Adds 4 sitelink extensions
 * 4. Adds 4 callout extensions
 * 5. Adds structured snippet (Brands)
 * 6. Sets ad schedule with bid adjustments
 *
 * What you must do MANUALLY after running (see checklist below script):
 * - Switch bidding strategy to Manual CPC + eCPC
 * - Lower max CPC to €0.35
 * - Add "All languages" to language targeting
 * - Fix location targeting to "Presence only"
 * - Split ad groups by category (phase 2)
 * - Add audience signals (observation mode)
 */

var CAMPAIGN_NAME = "ViaPharma DSA";

function main() {
  var campaign = getCampaign();
  if (!campaign) {
    Logger.log("ERROR: Campaign '" + CAMPAIGN_NAME + "' not found!");
    return;
  }

  Logger.log("Found campaign: " + campaign.getName() + " (ID: " + campaign.getId() + ")");

  setBudget(campaign);
  addNegativeKeywords(campaign);
  addSitelinkExtensions(campaign);
  addCalloutExtensions(campaign);
  addStructuredSnippets(campaign);
  setAdSchedule(campaign);

  Logger.log("\n=== DONE ===");
  Logger.log("Script completed. See manual checklist for remaining steps.");
}

function getCampaign() {
  var iterator = AdsApp.campaigns()
    .withCondition("campaign.name = '" + CAMPAIGN_NAME + "'")
    .get();
  if (iterator.hasNext()) {
    return iterator.next();
  }
  return null;
}

// ─── 1. Budget: €10 → €20/day ───────────────────────────────────────────────

function setBudget(campaign) {
  Logger.log("\n--- Setting budget to €20/day ---");
  var budget = campaign.getBudget();
  var currentBudget = budget.getAmount();
  Logger.log("Current budget: €" + currentBudget);
  budget.setAmount(20);
  Logger.log("New budget: €20/day");
}

// ─── 2. Negative keywords ───────────────────────────────────────────────────

function addNegativeKeywords(campaign) {
  Logger.log("\n--- Adding negative keywords ---");

  var negatives = [
    // Research / no-buy intent (Bulgarian)
    "безплатно",
    "листовка",
    "упътване",
    "инструкции",
    "форум",
    "ревюта",
    "мнение",
    "мнения",
    "противопоказания",
    "как се приема",
    "дозировка",
    "домашно",
    "домашен",
    "снимки",
    "рецепта",

    // Research / no-buy intent (English)
    "wiki",
    "wikipedia",
    "youtube",
    "video",
    "images",
    "pictures",
    "side effects",
    "pdf",
    "free",
    "download",
    "torrent",
    "reddit",

    // Controlled substances
    "tramadol",
    "xanax",
    "rivotril",
    "fentanil",
    "fentanyl",
    "clonazepam",
    "modafinil",
    "adderall",
    "vicodin",
    "oxycontin",
    "стероиди",
    "анаболи",
    "анаболен",
    "канабис",
    "марихуана",

    // Employment / wholesale
    "работа",
    "работни места",
    "jobs",
    "career",
    "wholesale",
    "на едро",
    "дистрибутор",
    "франчайз",
    "reseller",

    // Competitors
    "sopharmacy",
    "аптека рига",
    "ремедиум",
    "subra",
    "фрамар",
    "framar",
    "lilly дрогерия",
    "dm дрогерия"
  ];

  var count = 0;
  for (var i = 0; i < negatives.length; i++) {
    campaign.createNegativeKeyword("[" + negatives[i] + "]");  // exact match
    campaign.createNegativeKeyword('"' + negatives[i] + '"');   // phrase match
    count += 2;
  }

  Logger.log("Added " + count + " negative keywords (" + negatives.length + " terms × 2 match types)");
}

// ─── 3. Sitelink extensions ─────────────────────────────────────────────────

function addSitelinkExtensions(campaign) {
  Logger.log("\n--- Adding sitelink extensions ---");

  var sitelinks = [
    {
      text: "Намаления до -30%",
      description1: "Хиляди продукти на промоция",
      description2: "Козметика, витамини и здраве",
      finalUrl: "https://viapharma.us/collections/namaleniya"
    },
    {
      text: "Витамини и добавки",
      description1: "Solgar, Nature's Way, Doppelherz",
      description2: "Качествени хранителни добавки",
      finalUrl: "https://viapharma.us/collections/vitamini-i-minerali"
    },
    {
      text: "Козметика за лице",
      description1: "La Roche-Posay, Bioderma, Eucerin",
      description2: "Дерматологична козметика",
      finalUrl: "https://viapharma.us/collections/grizha-za-litse"
    },
    {
      text: "Безплатна доставка BOX NOW",
      description1: "До автомат BOX NOW безплатно",
      description2: "Промо до 31 май 2026",
      finalUrl: "https://viapharma.us/pages/dostavka"
    }
  ];

  for (var i = 0; i < sitelinks.length; i++) {
    var sl = sitelinks[i];
    var builder = AdsApp.extensions.newSitelinkBuilder()
      .withLinkText(sl.text)
      .withDescription1(sl.description1)
      .withDescription2(sl.description2)
      .withFinalUrl(sl.finalUrl);

    var result = builder.build();
    if (result.isSuccessful()) {
      var sitelink = result.getResult();
      campaign.addSitelink(sitelink);
      Logger.log("  Added sitelink: " + sl.text);
    } else {
      Logger.log("  FAILED sitelink: " + sl.text + " — " + result.getErrors());
    }
  }
}

// ─── 4. Callout extensions ──────────────────────────────────────────────────

function addCalloutExtensions(campaign) {
  Logger.log("\n--- Adding callout extensions ---");

  var callouts = [
    "Оригинални продукти",
    "14 дни връщане",
    "Бърза доставка от 1.52 лв",
    "Над 10 000 продукта"
  ];

  for (var i = 0; i < callouts.length; i++) {
    var builder = AdsApp.extensions.newCalloutBuilder()
      .withText(callouts[i]);

    var result = builder.build();
    if (result.isSuccessful()) {
      var callout = result.getResult();
      campaign.addCallout(callout);
      Logger.log("  Added callout: " + callouts[i]);
    } else {
      Logger.log("  FAILED callout: " + callouts[i] + " — " + result.getErrors());
    }
  }
}

// ─── 5. Structured snippets ────────────────────────────────────────────────

function addStructuredSnippets(campaign) {
  Logger.log("\n--- Adding structured snippet (Brands) ---");

  var builder = AdsApp.extensions.newSnippetBuilder()
    .withHeader("Brands")
    .withValues([
      "La Roche-Posay",
      "Eucerin",
      "Bioderma",
      "Solgar",
      "Avene",
      "BOIRON",
      "Vichy",
      "Uriage"
    ]);

  var result = builder.build();
  if (result.isSuccessful()) {
    var snippet = result.getResult();
    campaign.addSnippet(snippet);
    Logger.log("  Added structured snippet: Brands");
  } else {
    Logger.log("  FAILED snippet: " + result.getErrors());
  }
}

// ─── 6. Ad schedule with bid adjustments ────────────────────────────────────

function setAdSchedule(campaign) {
  Logger.log("\n--- Setting ad schedule ---");

  // Note: Google Ads Scripts ad scheduling uses campaign-level targeting.
  // Days: MONDAY=1, TUESDAY=2, ..., SUNDAY=7
  // Bid modifiers: 1.0 = no change, 0.7 = -30%

  var schedules = [
    // Mon-Fri 08:00-22:00 → no adjustment (full bid)
    { day: "MONDAY",    start: {hour: 8, minute: 0}, end: {hour: 22, minute: 0}, bid: 1.0 },
    { day: "TUESDAY",   start: {hour: 8, minute: 0}, end: {hour: 22, minute: 0}, bid: 1.0 },
    { day: "WEDNESDAY", start: {hour: 8, minute: 0}, end: {hour: 22, minute: 0}, bid: 1.0 },
    { day: "THURSDAY",  start: {hour: 8, minute: 0}, end: {hour: 22, minute: 0}, bid: 1.0 },
    { day: "FRIDAY",    start: {hour: 8, minute: 0}, end: {hour: 22, minute: 0}, bid: 1.0 },

    // Mon-Fri 22:00-08:00 → -30%
    { day: "MONDAY",    start: {hour: 0, minute: 0}, end: {hour: 8, minute: 0}, bid: 0.7 },
    { day: "TUESDAY",   start: {hour: 0, minute: 0}, end: {hour: 8, minute: 0}, bid: 0.7 },
    { day: "WEDNESDAY", start: {hour: 0, minute: 0}, end: {hour: 8, minute: 0}, bid: 0.7 },
    { day: "THURSDAY",  start: {hour: 0, minute: 0}, end: {hour: 8, minute: 0}, bid: 0.7 },
    { day: "FRIDAY",    start: {hour: 0, minute: 0}, end: {hour: 8, minute: 0}, bid: 0.7 },
    { day: "MONDAY",    start: {hour: 22, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.7 },
    { day: "TUESDAY",   start: {hour: 22, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.7 },
    { day: "WEDNESDAY", start: {hour: 22, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.7 },
    { day: "THURSDAY",  start: {hour: 22, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.7 },
    { day: "FRIDAY",    start: {hour: 22, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.7 },

    // Sat-Sun all day → -20%
    { day: "SATURDAY",  start: {hour: 0, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.8 },
    { day: "SUNDAY",    start: {hour: 0, minute: 0}, end: {hour: 24, minute: 0}, bid: 0.8 },
  ];

  for (var i = 0; i < schedules.length; i++) {
    var s = schedules[i];
    campaign.addAdSchedule({
      dayOfWeek: s.day,
      startHour: s.start.hour,
      startMinute: s.start.minute,
      endHour: s.end.hour,
      endMinute: s.end.minute,
      bidModifier: s.bid
    });
    Logger.log("  " + s.day + " " + s.start.hour + ":00-" + s.end.hour + ":00 → bid x" + s.bid);
  }
}
