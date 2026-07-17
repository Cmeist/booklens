const themes = ["curated-reading-room", "modern-book-journal", "intelligent-archive"];
const screenControl = document.querySelector("#screen-control");
const artControl = document.querySelector("#art-control");
const viewportControls = [...document.querySelectorAll('input[name="viewport"]')];
const cards = [...document.querySelectorAll(".theme-card")];

function currentViewport() {
  return viewportControls.find((control) => control.checked)?.value ?? "desktop";
}

function updatePreviewSize() {
  const mobile = currentViewport() === "mobile";
  const sourceWidth = mobile ? 390 : 1440;
  const sourceHeight = mobile ? 844 : 980;

  cards.forEach((card) => {
    const windowElement = card.querySelector(".preview-window");
    const frame = card.querySelector("iframe");
    const availableWidth = windowElement.clientWidth;
    const scale = Math.min(1, availableWidth / sourceWidth);
    frame.style.width = `${sourceWidth}px`;
    frame.style.height = `${sourceHeight}px`;
    frame.style.transform = `scale(${scale})`;
    windowElement.style.height = `${Math.round(sourceHeight * scale)}px`;
  });
}

function updateSources() {
  const screen = screenControl.value;
  const art = artControl.checked ? "1" : "0";

  cards.forEach((card) => {
    const theme = card.dataset.theme;
    const url = `./shared/prototype.html?theme=${theme}&screen=${screen}&art=${art}&embed=1`;
    card.querySelector("iframe").src = url;
    card.querySelector(".full-link").href = `./${theme}/?screen=${screen}&art=${art}`;
  });

  updatePreviewSize();
}

screenControl.addEventListener("change", updateSources);
artControl.addEventListener("change", updateSources);
viewportControls.forEach((control) => control.addEventListener("change", updatePreviewSize));
window.addEventListener("resize", updatePreviewSize);

if ("ResizeObserver" in window) {
  const observer = new ResizeObserver(updatePreviewSize);
  cards.forEach((card) => observer.observe(card.querySelector(".preview-window")));
}

if (themes.every((theme) => cards.some((card) => card.dataset.theme === theme))) {
  updateSources();
}

