const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector(".site-nav");

menuButton?.addEventListener("click", () => {
  const isOpen = navigation?.classList.toggle("open") ?? false;
  menuButton.setAttribute("aria-expanded", String(isOpen));
});

navigation?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navigation.classList.remove("open");
    menuButton?.setAttribute("aria-expanded", "false");
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || !navigation?.classList.contains("open")) return;
  navigation.classList.remove("open");
  menuButton?.setAttribute("aria-expanded", "false");
  menuButton?.focus();
});

document.addEventListener("click", (event) => {
  if (!navigation?.classList.contains("open")) return;
  const target = event.target;
  if (!(target instanceof Node) || navigation.contains(target) || menuButton?.contains(target)) return;
  navigation.classList.remove("open");
  menuButton?.setAttribute("aria-expanded", "false");
});

const year = document.querySelector("#year");
if (year) year.textContent = new Date().getFullYear();
