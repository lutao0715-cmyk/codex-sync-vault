(function () {
  var r = {};

  // JSON-LD is usually the most complete product source on ecommerce pages.
  r.jsonLD = [];
  Array.from(
    document.querySelectorAll('script[type="application/ld+json"]'),
  ).forEach(function (script) {
    try {
      var data = JSON.parse(script.textContent);
      if (data["@graph"]) {
        data["@graph"].forEach(function (item) {
          r.jsonLD.push(item);
        });
      } else {
        r.jsonLD.push(data);
      }
    } catch (e) {}
  });

  r.product = null;
  for (var i = 0; i < r.jsonLD.length; i++) {
    var ld = r.jsonLD[i];
    if (ld["@type"] === "Product" || ld["@type"] === "ProductGroup") {
      r.product = {
        name: ld.name || null,
        brand: ld.brand ? ld.brand.name || ld.brand : null,
        description: ld.description || null,
        sku: ld.sku || null,
        images: [],
        price: null,
        currency: null,
        rating: null,
        reviewCount: null,
      };
      if (ld.image) {
        r.product.images = Array.isArray(ld.image) ? ld.image : [ld.image];
      }
      if (ld.offers) {
        var offer = Array.isArray(ld.offers) ? ld.offers[0] : ld.offers;
        r.product.price = offer.price || offer.lowPrice || null;
        r.product.currency = offer.priceCurrency || null;
      }
      if (ld.aggregateRating) {
        r.product.rating = ld.aggregateRating.ratingValue || null;
        r.product.reviewCount = ld.aggregateRating.reviewCount || null;
      }
      break;
    }
  }

  if (r.product && !r.product.rating) {
    for (var j = 0; j < r.jsonLD.length; j++) {
      if (r.jsonLD[j].aggregateRating) {
        r.product.rating = r.jsonLD[j].aggregateRating.ratingValue || null;
        r.product.reviewCount = r.jsonLD[j].aggregateRating.reviewCount || null;
        break;
      }
    }
  }

  r.openGraph = {};
  Array.from(
    document.querySelectorAll(
      'meta[property^="og:"], meta[property^="product:"]',
    ),
  ).forEach(function (meta) {
    var prop = meta.getAttribute("property");
    var content = meta.getAttribute("content");
    if (prop && content) r.openGraph[prop] = content;
  });

  r.meta = {};
  ["description", "keywords"].forEach(function (name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    if (el) r.meta[name] = el.getAttribute("content");
  });

  r.pageTitle = document.title;
  var canonical = document.querySelector('link[rel="canonical"]');
  r.canonicalUrl = canonical ? canonical.getAttribute("href") : location.href;

  r.isShopify = !!(
    window.Shopify ||
    document.querySelector('meta[name="shopify-digital-wallet"]')
  );
  if (r.isShopify) {
    r.shopifyJsonUrl = location.pathname.replace(/\/$/, "") + ".json";
  }

  r.allImages = [];
  if (r.product && r.product.images) {
    r.product.images.forEach(function (img) {
      if (typeof img === "string" && r.allImages.indexOf(img) === -1)
        r.allImages.push(img);
    });
  }
  if (r.openGraph["og:image"]) {
    var ogImg = r.openGraph["og:image"];
    if (r.allImages.indexOf(ogImg) === -1) r.allImages.push(ogImg);
  }
  // Large page images are likely to be product photos when structured images are sparse.
  Array.from(document.querySelectorAll("img")).forEach(function (img) {
    if (img.naturalWidth >= 300 && img.naturalHeight >= 300) {
      var src = img.src;
      if (
        src &&
        src.indexOf("data:") !== 0 &&
        r.allImages.indexOf(src) === -1
      ) {
        r.allImages.push(src);
      }
    }
  });

  // Keep output small enough for downstream prompt context.
  delete r.jsonLD;

  return JSON.stringify(r, null, 2);
})();
