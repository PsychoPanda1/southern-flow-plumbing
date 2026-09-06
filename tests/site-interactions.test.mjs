import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { runInNewContext } from "node:vm";

const source = readFileSync(new URL("../site/script.js", import.meta.url), "utf8");

// Test the shipped script without a browser or third-party DOM dependency.
// These behavior checks supplement, rather than replace, device testing.
function setup({ mobile = true, clipboardFails = false } = {}) {
  let document;
  class Element {
    constructor(attrs = {}) {
      this.attrs = new Map(Object.entries(attrs));
      this.listeners = new Map();
      this.children = [];
      const classes = new Set();
      this.classList = {
        contains: (value) => classes.has(value),
        remove: (value) => classes.delete(value),
        toggle: (value) => {
          if (classes.has(value)) { classes.delete(value); return false; }
          classes.add(value); return true;
        },
      };
    }
    addEventListener(name, callback) {
      const handlers = this.listeners.get(name) ?? [];
      handlers.push(callback);
      this.listeners.set(name, handlers);
    }
    async emit(name, event = {}) {
      for (const callback of this.listeners.get(name) ?? []) await callback(event);
    }
    getAttribute(name) { return this.attrs.get(name) ?? null; }
    setAttribute(name, value) { this.attrs.set(name, String(value)); }
    hasAttribute(name) { return this.attrs.has(name); }
    contains(target) { return this === target || this.children.some(child => child.contains(target)); }
    focus() { document.activeElement = this; }
    querySelectorAll() { return this.children; }
    querySelector() { return this.children[0] ?? null; }
  }
  document = new Element();
  const button = new Element({ "aria-expanded": "false" });
  const nav = new Element();
  const sectionLink = new Element({ href: "#services" });
  const callLink = new Element({ href: "#estimate", "data-mobile-call": "tel:+18437938806" });
  nav.children = [sectionLink, callLink];
  const section = new Element();
  const estimate = new Element();
  const outside = new Element();
  const copy = new Element({ "data-copy-phone": "843-793-8806" });
  const status = new Element();
  const year = new Element();
  const elements = { ".menu-button": button, ".site-nav": nav, "#year": year, "[data-copy-phone]": copy, ".copy-status": status };
  document.querySelector = (selector) => elements[selector] ?? null;
  document.querySelectorAll = () => [callLink];
  document.getElementById = (id) => ({ services: section, estimate })[id] ?? null;
  const queries = new Map();
  const window = { matchMedia(query) {
    const entry = new Element();
    entry.matches = mobile;
    queries.set(query, entry);
    return entry;
  } };
  const copied = [];
  const navigator = { clipboard: { async writeText(value) {
    if (clipboardFails) throw new Error("Clipboard unavailable");
    copied.push(value);
  } } };
  runInNewContext(source, { document, window, navigator, Node: Element, Date });
  return { button, nav, sectionLink, callLink, section, outside, copy, status, year, document, queries, copied };
}

test("menu opens, Escape closes it and restores focus", async () => {
  const ui = setup();
  await ui.button.emit("click");
  assert.equal(ui.button.getAttribute("aria-expanded"), "true");
  assert.ok(ui.nav.classList.contains("open"));
  await ui.document.emit("keydown", { key: "Escape" });
  assert.equal(ui.button.getAttribute("aria-expanded"), "false");
  assert.equal(ui.document.activeElement, ui.button);
});

test("section navigation moves focus out of the hidden menu", async () => {
  const ui = setup();
  await ui.button.emit("click");
  ui.sectionLink.focus();
  await ui.sectionLink.emit("click");
  assert.equal(ui.document.activeElement, ui.section);
  assert.equal(ui.section.getAttribute("tabindex"), "-1");
  assert.equal(ui.nav.classList.contains("open"), false);
});

test("moving focus or clicking outside closes the menu", async () => {
  for (const name of ["click", "focusin"]) {
    const ui = setup();
    await ui.button.emit("click");
    await ui.document.emit(name, { target: ui.outside });
    assert.equal(ui.nav.classList.contains("open"), false);
    assert.equal(ui.button.getAttribute("aria-expanded"), "false");
  }
});

test("calling from the menu leaves visible focus if the dialer is dismissed", async () => {
  const ui = setup();
  await ui.button.emit("click");
  ui.callLink.focus();
  await ui.callLink.emit("click");
  assert.equal(ui.callLink.getAttribute("href"), "tel:+18437938806");
  assert.equal(ui.document.activeElement, ui.button);
  assert.equal(ui.nav.classList.contains("open"), false);
});

test("menu resizing clears stale state and keeps focus on a visible control", async () => {
  const ui = setup();
  const query = ui.queries.get("(max-width: 900px)");
  ui.button.focus();
  await ui.button.emit("click");
  query.matches = false;
  await query.emit("change");
  assert.equal(ui.document.activeElement, ui.sectionLink);
  assert.equal(ui.nav.classList.contains("open"), false);
  query.matches = true;
  await query.emit("change");
  assert.equal(ui.document.activeElement, ui.button);
});

test("estimate link switches between the exact business phone and desktop section", async () => {
  const ui = setup({ mobile: false });
  const query = ui.queries.get("(max-width: 620px)");
  assert.equal(ui.callLink.getAttribute("href"), "#estimate");
  query.matches = true;
  await query.emit("change");
  assert.equal(ui.callLink.getAttribute("href"), "tel:+18437938806");
  query.matches = false;
  await query.emit("change");
  assert.equal(ui.callLink.getAttribute("href"), "#estimate");
});

test("clipboard success and failure both give usable feedback", async () => {
  const success = setup();
  await success.copy.emit("click");
  assert.deepEqual(success.copied, ["843-793-8806"]);
  assert.equal(success.status.textContent, "Phone number copied.");
  const failure = setup({ clipboardFails: true });
  await failure.copy.emit("click");
  assert.equal(failure.status.textContent, "Call 843-793-8806 for a free estimate.");
});
