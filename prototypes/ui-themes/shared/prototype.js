const THEMES = {
  "curated-reading-room": "The Curated Reading Room",
  "modern-book-journal": "The Modern Book Journal",
  "intelligent-archive": "The Intelligent Archive",
};

const SCREENS = new Set(["home", "explore", "detail"]);
const params = new URLSearchParams(window.location.search);
const theme = THEMES[params.get("theme")] ? params.get("theme") : "curated-reading-room";
const screen = SCREENS.has(params.get("screen")) ? params.get("screen") : "home";
const artEnabled = params.get("art") !== "0";
const embedded = params.get("embed") === "1";

document.documentElement.dataset.theme = theme;
document.body.classList.toggle("art-off", !artEnabled);
document.body.classList.toggle("embed", embedded);
document.querySelector("#theme-stylesheet").href = `../${theme}/theme.css`;
document.title = `${THEMES[theme]} · BookLens`;

const books = {
  canticle: {
    title: "A Canticle for Leibowitz",
    author: "Walter M. Miller Jr.",
    cover: "https://covers.openlibrary.org/b/id/10221348-L.jpg",
    rating: "4.12",
    match: "94%",
    year: "1959",
    pages: "334 pages",
    tags: ["science fiction", "philosophical", "post-apocalyptic"],
    description: "Centuries after a nuclear collapse, an isolated order preserves fragments of knowledge while civilization begins its long return.",
  },
  odyssey: {
    title: "2001: A Space Odyssey",
    author: "Arthur C. Clarke",
    cover: "https://covers.openlibrary.org/b/id/11344400-L.jpg",
    rating: "4.16",
    match: "91%",
    year: "1968",
    pages: "297 pages",
    tags: ["science fiction", "space", "reflective"],
    description: "A measured, visionary journey from humanity's origins to a mysterious encounter beyond the known edges of space.",
  },
  almond: {
    title: "Almond",
    author: "Won-Pyung Sohn",
    cover: "https://covers.openlibrary.org/b/id/11654300-L.jpg",
    rating: "4.03",
    match: "87%",
    year: "2020",
    pages: "272 pages",
    tags: ["coming of age", "emotional", "friendship"],
    description: "A quietly powerful coming-of-age story about emotion, friendship, and the courage to step beyond a carefully ordered life.",
  },
  mystery: {
    title: "A Caribbean Mystery",
    author: "Agatha Christie",
    cover: "https://covers.openlibrary.org/b/id/14578132-L.jpg",
    rating: "3.81",
    match: "79%",
    year: "1964",
    pages: "240 pages",
    tags: ["mystery", "classic", "clever"],
    description: "Miss Marple's quiet holiday becomes an investigation when an unfinished story and a sudden death refuse to stay buried.",
  },
  instrument: {
    title: "A Blunt Instrument",
    author: "Georgette Heyer",
    cover: "https://covers.openlibrary.org/b/id/6924145-L.jpg",
    rating: "3.76",
    match: "76%",
    year: "1938",
    pages: "352 pages",
    tags: ["mystery", "witty", "investigation"],
    description: "A polished gentleman's murder exposes a crowded field of motives in a witty, tightly observed country-house mystery.",
  },
  missing: {
    title: "The Cartographer's Library of Impossible Coastlines",
    author: "Alexandra Montgomery-Singh",
    cover: null,
    rating: "4.21",
    match: "84%",
    year: "2025",
    pages: "416 pages",
    tags: ["literary", "speculative", "adventure"],
    description: "A prototype record with a deliberately long title, long author name, and no cover image to test resilient layouts.",
  },
};

function cover(book, sizeClass = "") {
  if (book.cover) {
    return `<div class="book-cover ${sizeClass}"><img src="${book.cover}" alt="Cover of ${book.title}" /></div>`;
  }
  return `<div class="book-cover fallback ${sizeClass}" role="img" aria-label="No cover available for ${book.title}"><strong>${book.title}</strong><span>${book.author}</span></div>`;
}

function reasons(items) {
  return `<ul class="reason-list">${items.map((item) => `<li class="reason">${item}</li>`).join("")}</ul>`;
}

function tile(book) {
  return `<article class="book-tile">${cover(book)}<h3 class="book-title">${book.title}</h3><p class="book-author">${book.author}</p><div class="book-meta"><span class="community-rating">★ ${book.rating}</span><span>${book.year}</span></div></article>`;
}

function nav(active = "") {
  return `<header class="site-nav"><a class="wordmark" href="#">Book<span class="wordmark-mark">Lens</span></a><nav aria-label="Main"><a class="${active === "home" ? "active" : ""}">Home</a><a class="${active === "explore" ? "active" : ""}">Discover</a><a>For You</a><a>My Library</a><a>Insights</a></nav><div class="site-nav-actions"><button class="button quiet" aria-label="Search">Search</button><button class="button secondary">My Library</button></div></header>`;
}

function home() {
  const shelfBooks = [books.canticle, books.odyssey, books.almond, books.mystery, books.missing];
  return `<div class="site-shell">${nav("home")}<main><section class="hero"><div class="container hero-grid"><div><p class="eyebrow">Your next read, made clearer</p><h1 class="display-title">Find the book that fits right now.</h1><p class="lede">Explore stories through themes, pace, and the reading patterns that matter to you—then see exactly why each recommendation fits.</p><div class="hero-actions"><a class="button primary">Discover books</a><a class="button secondary">See my matches</a></div></div><div class="hero-art" role="img" aria-label="Decorative reading-room artwork"><div class="art-caption"><span>Personal discovery</span><span>Explainable matches</span></div></div></div></section><dl class="container metric-strip"><div class="metric"><dt>Books to explore</dt><dd>1,122</dd></div><div class="metric"><dt>Your top theme</dt><dd>Reflective</dd></div><div class="metric"><dt>Unread matches</dt><dd>24</dd></div><div class="metric"><dt>Catalog source</dt><dd>Open Library</dd></div></dl><section class="section container"><div class="section-heading"><div><p class="eyebrow">Selected for you</p><h2 class="section-title">A strong match for tonight</h2></div><a class="text-link">View all matches →</a></div><article class="match-panel">${cover(books.canticle)}<div><p class="eyebrow">Top unread match</p><h3>${books.canticle.title}</h3><p>${books.canticle.author}</p>${reasons(["Reflective themes", "Your usual length", "Highly rated classic"])}</div><div class="match-number"><strong>${books.canticle.match}</strong><span>personal fit</span></div></article><div class="low-signal"><div><strong>New here?</strong> Log three books or set a few preferences to replace this sample with personal matches.</div><a class="button secondary">Build my profile</a></div></section><section class="section container"><div class="section-heading"><div><p class="eyebrow">From the catalog</p><h2 class="section-title">Enduring favorites, worth another look</h2><p class="section-copy">Cover-led browsing with community ratings kept separate from personal compatibility.</p></div><a class="text-link">Browse all →</a></div><div class="shelf">${shelfBooks.map(tile).join("")}</div></section></main></div>`;
}

function resultCard(book, selected = false) {
  return `<article class="result-card ${selected ? "selected" : ""}">${cover(book)}<div><h3>${book.title}</h3><p>${book.author}</p><p class="result-description">${book.description}</p>${reasons(book.tags.slice(0, 2))}</div><div class="result-score"><span class="match-score">${book.match}</span></div></article>`;
}

function bars() {
  return `<div class="theme-bars"><h3>Story profile</h3><div class="bar-row"><span>Reflective</span><div class="bar"><span style="width:88%"></span></div><strong>88</strong></div><div class="bar-row"><span>Expansive</span><div class="bar"><span style="width:74%"></span></div><strong>74</strong></div><div class="bar-row"><span>Hopeful</span><div class="bar"><span style="width:56%"></span></div><strong>56</strong></div><div class="bar-row"><span>Fast-paced</span><div class="bar"><span style="width:24%"></span></div><strong>24</strong></div></div>`;
}

function facts(book) {
  return `<dl class="fact-row"><div class="fact"><dt>Published</dt><dd>${book.year}</dd></div><div class="fact"><dt>Length</dt><dd>${book.pages}</dd></div><div class="fact"><dt>Rating</dt><dd class="community-rating">★ ${book.rating}</dd></div><div class="fact"><dt>Match</dt><dd class="match-score">${book.match}</dd></div></dl>`;
}

function preview(book) {
  return `<aside class="detail-preview"><div class="preview-top">${cover(book)}<div><p class="eyebrow">Selected book</p><h2>${book.title}</h2><p class="book-author">${book.author}</p><div class="hero-actions"><button class="button primary">Want to read</button></div></div></div><p class="description">${book.description}</p>${facts(book)}${reasons(["Reflective themes", "Similar rating profile", "Classic science fiction"])}${bars()}</aside>`;
}

function explore() {
  return `<div class="site-shell">${nav("explore")}<main><section class="page-intro container"><div class="intro-row"><div><p class="eyebrow">Discover</p><h1 class="page-title">Browse with intention.</h1><p class="lede">Search by title or author, then narrow the catalog by the qualities that shape a reading experience.</p></div><span class="button secondary">1,122 books</span></div><div class="search-bar"><input class="search-field" type="search" value="reflective science fiction" aria-label="Search books" /><select class="search-field" aria-label="Sort books"><option>Best match</option></select><button class="button primary filter-button">Filters · 2</button></div><div class="active-filters"><span>Active</span><button class="filter-chip">Reflective ×</button><button class="filter-chip">Science fiction ×</button><button class="filter-chip">Exclude horror ×</button></div></section><div class="container explore-layout"><section><div class="results-heading"><h2>Results</h2><span>1–4 of 38</span></div><div class="result-list">${resultCard(books.canticle, true)}${resultCard(books.odyssey)}${resultCard(books.missing)}${resultCard(books.almond)}</div></section>${preview(books.canticle)}</div></main></div>`;
}

function detail() {
  const similar = [books.odyssey, books.almond, books.missing];
  return `<div class="site-shell">${nav()}<main><section class="book-hero"><div class="narrow book-hero-grid">${cover(books.canticle)}<div><p class="eyebrow">A BookLens profile</p><h1>${books.canticle.title}</h1><p class="hero-author">by ${books.canticle.author}</p><p class="hero-description">${books.canticle.description} A meditation on memory, responsibility, and what humanity chooses to preserve.</p><div class="hero-facts"><span class="community-rating">★ ${books.canticle.rating} community</span><span class="match-score">${books.canticle.match} personal match</span><span>${books.canticle.year}</span><span>${books.canticle.pages}</span></div><div class="hero-actions"><button class="button primary">Want to read</button><button class="button secondary">Mark as read</button></div></div></div></section><section class="section"><div class="narrow detail-sections"><article class="profile-card"><p class="eyebrow">Why it may fit</p><h2>Story profile</h2><p>Signals derived from subjects and description—not a substitute for the book itself.</p>${bars()}${reasons(["Reflective themes", "Your usual length", "Similar to books you rated highly"])}</article><aside class="catalog-note"><p class="eyebrow">At a glance</p><h2>Quietly expansive</h2><p>A slower, idea-driven classic with a long historical arc and a hopeful undercurrent.</p><a class="text-link">How BookLens scored this →</a></aside></div></section><section class="section narrow"><div class="section-heading"><div><p class="eyebrow">Continue exploring</p><h2 class="section-title">Similar books, with reasons</h2></div><a class="text-link">See every match →</a></div><div class="similar-grid">${similar.map((book) => `<div>${tile(book)}${reasons(book.tags.slice(0, 1))}</div>`).join("")}</div></section></main></div>`;
}

document.querySelector("#app").innerHTML = screen === "explore" ? explore() : screen === "detail" ? detail() : home();

const themeSelect = document.querySelector("#theme-select");
const artToggle = document.querySelector("#art-toggle");
themeSelect.value = theme;
artToggle.checked = artEnabled;

function navigate(next = {}) {
  const query = new URLSearchParams({ theme, screen, art: artToggle.checked ? "1" : "0" });
  Object.entries(next).forEach(([key, value]) => query.set(key, value));
  window.location.search = query.toString();
}

themeSelect.addEventListener("change", () => navigate({ theme: themeSelect.value }));
artToggle.addEventListener("change", () =>
  navigate({ art: artToggle.checked ? "1" : "0" }),
);

document.querySelectorAll("[data-screen-link]").forEach((link) => {
  const nextScreen = link.dataset.screenLink;
  const query = new URLSearchParams({ theme, screen: nextScreen, art: artEnabled ? "1" : "0" });
  link.href = `?${query}`;
  if (nextScreen === screen) link.setAttribute("aria-current", "page");
});
