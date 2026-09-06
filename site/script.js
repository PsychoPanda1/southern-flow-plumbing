const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector(".site-nav");
const menuQuery = window.matchMedia("(max-width: 900px)");

const closeMenu = (restoreFocus = false) => {
  navigation?.classList.remove("open");
  menuButton?.setAttribute("aria-expanded", "false");
  if (restoreFocus) menuButton?.focus();
};

menuButton?.addEventListener("click", () => {
  const isOpen = navigation?.classList.toggle("open") ?? false;
  menuButton.setAttribute("aria-expanded", String(isOpen));
});

navigation?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    const wasOpen = navigation.classList.contains("open");
    const href = link.getAttribute("href");
    closeMenu(wasOpen && href?.startsWith("tel:"));
    // Move keyboard focus out of the now-hidden mobile menu, without changing
    // the link's native scrolling or telephone action.
    if (wasOpen && href?.startsWith("#")) {
      const destination = document.getElementById(href.slice(1));
      if (destination) {
        if (!destination.hasAttribute("tabindex")) destination.setAttribute("tabindex", "-1");
        destination.focus({ preventScroll: true });
      }
    }
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || !navigation?.classList.contains("open")) return;
  closeMenu(true);
});

document.addEventListener("click", (event) => {
  if (!navigation?.classList.contains("open")) return;
  const target = event.target;
  if (!(target instanceof Node) || navigation.contains(target) || menuButton?.contains(target)) return;
  closeMenu();
});

document.addEventListener("focusin", (event) => {
  if (!navigation?.classList.contains("open")) return;
  const target = event.target;
  if (target instanceof Node && !navigation.contains(target) && !menuButton?.contains(target)) closeMenu();
});

menuQuery.addEventListener("change", () => {
  const focusWillBeHidden = menuQuery.matches && navigation?.contains(document.activeElement);
  const focusWasOnButton = document.activeElement === menuButton;
  closeMenu(focusWillBeHidden);
  if (!menuQuery.matches && focusWasOnButton) navigation?.querySelector("a")?.focus();
});

const year = document.querySelector("#year");
if (year) year.textContent = new Date().getFullYear();

const mobileCallQuery = window.matchMedia("(max-width: 620px)");
const mobileCallLinks = document.querySelectorAll("[data-mobile-call]");

const syncMobileCallLinks = () => {
  mobileCallLinks.forEach((link) => {
    const mobileHref = link.getAttribute("data-mobile-call");
    if (!link.hasAttribute("data-desktop-href")) {
      link.setAttribute("data-desktop-href", link.getAttribute("href") ?? "#estimate");
    }
    link.setAttribute("href", mobileCallQuery.matches && mobileHref ? mobileHref : link.getAttribute("data-desktop-href"));
  });
};

syncMobileCallLinks();
mobileCallQuery.addEventListener("change", syncMobileCallLinks);

const copyPhoneButton = document.querySelector("[data-copy-phone]");
const copyStatus = document.querySelector(".copy-status");

copyPhoneButton?.addEventListener("click", async () => {
  const phoneNumber = copyPhoneButton.getAttribute("data-copy-phone") ?? "";
  try {
    await navigator.clipboard.writeText(phoneNumber);
    if (copyStatus) copyStatus.textContent = "Phone number copied.";
  } catch {
    if (copyStatus) copyStatus.textContent = `Call ${phoneNumber} for a free estimate.`;
  }
});
