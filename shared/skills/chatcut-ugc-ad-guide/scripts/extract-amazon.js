(function () {
  var r = {};
  var el;

  el = document.querySelector("#productTitle");
  r.title = el ? el.textContent.trim() : null;

  el = document.querySelector("#bylineInfo");
  r.brand = el
    ? el.textContent
        .trim()
        .replace(/^(Brand:\s*|Visit the\s+|Store:\s*)/i, "")
        .replace(/\s+Store$/i, "")
    : null;

  el = document.querySelector(".a-price .a-offscreen");
  r.price = el ? el.textContent.trim() : null;

  el = document.querySelector(".basisPrice .a-offscreen");
  r.originalPrice = el ? el.textContent.trim() : null;

  el = document.querySelector(".savingsPercentage");
  r.discount = el ? el.textContent.trim() : null;

  el = document.querySelector("#acrPopover .a-icon-alt");
  r.rating = el ? el.textContent.trim() : null;

  el = document.querySelector("#acrCustomerReviewText");
  r.reviewCount = el ? el.textContent.trim() : null;

  r.sellingPoints = Array.from(
    document.querySelectorAll("#feature-bullets li .a-list-item"),
  )
    .map(function (e) {
      return e.textContent.trim();
    })
    .filter(function (t) {
      return t.length > 10;
    });

  r.overview = {};
  Array.from(
    document.querySelectorAll("#productOverview_feature_div tr"),
  ).forEach(function (tr) {
    var tds = Array.from(tr.querySelectorAll("td"));
    if (tds.length >= 2)
      r.overview[tds[0].textContent.trim()] = tds[1].textContent.trim();
  });

  r.specs = Array.from(
    document.querySelectorAll(
      "#productDetails_techSpec_section_1 tr, #detailBullets_feature_div li",
    ),
  )
    .map(function (e) {
      return e.textContent.trim().replace(/\s+/g, " ");
    })
    .filter(function (t) {
      return t.length > 3;
    });

  r.dimensions = {};
  var dimKeys = [
    "Product Dimensions",
    "Item Dimensions",
    "Package Dimensions",
    "Item Weight",
    "Item Weight",
    "Size",
    "Capacity",
  ];
  Array.from(
    document.querySelectorAll(
      "#productDetails_techSpec_section_1 tr, #prodDetails tr",
    ),
  ).forEach(function (tr) {
    var th = tr.querySelector("th");
    var td = tr.querySelector("td");
    if (!th || !td) return;
    var key = th.textContent.trim();
    dimKeys.forEach(function (dk) {
      if (key.indexOf(dk) !== -1)
        r.dimensions[key.replace(/\s+/g, " ")] = td.textContent
          .trim()
          .replace(/\s+/g, " ");
    });
  });
  Array.from(
    document.querySelectorAll("#detailBullets_feature_div li"),
  ).forEach(function (li) {
    var text = li.textContent.trim().replace(/\s+/g, " ");
    dimKeys.forEach(function (dk) {
      if (text.indexOf(dk) !== -1) {
        var parts = text.split(/[:\u200F\u200E]+/);
        if (parts.length >= 2)
          r.dimensions[parts[0].trim()] = parts.slice(1).join(":").trim();
      }
    });
  });
  Object.keys(r.overview).forEach(function (k) {
    dimKeys.forEach(function (dk) {
      if (k.indexOf(dk) !== -1) r.dimensions[k] = r.overview[k];
    });
  });

  // Amazon's hiRes script payload is more reliable than visible thumbnail URLs.
  r.images = [];
  Array.from(document.querySelectorAll("script")).forEach(function (script) {
    var text = script.textContent;
    if (text.indexOf("hiRes") === -1 || text.indexOf("media-amazon") === -1)
      return;
    var matches = text.match(
      /"hiRes"\s*:\s*"(https:\/\/m\.media-amazon\.com\/images\/I\/[^"]+)"/g,
    );
    if (!matches) return;
    matches.forEach(function (m) {
      var url = m.replace(/"hiRes"\s*:\s*"/, "").replace(/"$/, "");
      if (r.images.indexOf(url) === -1) r.images.push(url);
    });
  });

  var titles = Array.from(
    document.querySelectorAll('[data-hook="review-title"]'),
  );
  var bodies = Array.from(
    document.querySelectorAll('[data-hook="review-body"]'),
  );
  r.reviews = [];
  for (var i = 0; i < Math.min(titles.length, 5); i++) {
    r.reviews.push({
      title: titles[i] ? titles[i].textContent.trim() : "",
      body: bodies[i]
        ? bodies[i].textContent
            .trim()
            .replace(/\s*Read more\s*$/, "")
            .substring(0, 300)
        : "",
    });
  }

  el = document.querySelector("#couponBadgeRegularVpc, .couponBadge");
  r.coupon = el ? el.textContent.trim() : null;

  return JSON.stringify(r, null, 2);
})();
