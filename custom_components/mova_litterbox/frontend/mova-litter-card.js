/* Bundled, theme-aware MOVA device card. No other dashboard plugins are needed. */
(() => {
  "use strict";
  if (customElements.get("mova-litter-card")) return;

  const KEYS = [
    "device_status", "visits_today", "avg_duration", "last_visit",
    "pet_abnormalities", "bag_estimated_days_remaining", "bag_visits",
    "bag_reminder_due", "bag_replacement_date", "bag_reminder_mode",
    "bag_reminder_days", "bag_reminder_visits", "bag_replaced",
    "start_cleaning", "start_emptying", "start_leveling", "pause", "resume", "stop",
    "air_purification", "deodorizing_liquid", "cleaning_mode", "litter_type",
    "leveling_angle", "air_purification_duration", "delay_cleaning",
    "deodorizing_spray_duration", "do_not_disturb", "child_mode", "soft_stool_mode",
    "deep_clean", "air_purification_night_mode", "auto_air_purification",
    "deodorizing_auto_spray", "key_light", "key_tone",
  ];
  const MATCH_KEYS = [...KEYS].sort((a, b) => b.length - a.length);
  const ACTIONS = [
    ["start_cleaning", "Clean", "mdi:broom"],
    ["start_emptying", "Empty", "mdi:delete-empty"],
    ["start_leveling", "Level", "mdi:format-line-spacing"],
    ["pause", "Pause", "mdi:pause"],
    ["resume", "Resume", "mdi:play"],
    ["stop", "Stop", "mdi:stop"],
  ];
  const SETTINGS = [
    ["cleaning_mode", "Cleaning mode"], ["litter_type", "Litter type"],
    ["leveling_angle", "Leveling angle"], ["air_purification_duration", "Air purification duration"],
    ["delay_cleaning", "Cleaning delay"], ["deodorizing_spray_duration", "Spray duration"],
    ["do_not_disturb", "Do not disturb"], ["child_mode", "Child lock"],
    ["soft_stool_mode", "Soft stool mode"], ["deep_clean", "Deep clean"],
    ["air_purification_night_mode", "Air purification at night"],
    ["auto_air_purification", "Auto air purification"],
    ["deodorizing_auto_spray", "Auto deodorizing spray"],
    ["key_light", "Button light"], ["key_tone", "Button sound"],
  ];
  const unavailable = (state) => !state || ["unknown", "unavailable"].includes(state.state);
  const title = (value) => String(value || "—").replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());

  class MovaLitterCard extends HTMLElement {
    static getStubConfig() { return {}; }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._devices = [];
      this._selection = null;
      this._loading = false;
      this._loaded = false;
      this._lastAttempt = 0;
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
      this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
    }

    setConfig(config) {
      this._config = config || {};
      this._selection = this._config.device || this._selection;
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._loaded && !this._loading && Date.now() - this._lastAttempt > 30000) {
        void this._discover();
      }
      this._update();
    }

    getCardSize() { return 2; }
    getGridOptions() { return { columns: 6, min_columns: 3, rows: "auto" }; }

    async _discover() {
      if (!this._hass?.callWS) return;
      this._loading = true;
      this._lastAttempt = Date.now();
      try {
        const [entities, devices] = await Promise.all([
          this._hass.callWS({ type: "config/entity_registry/list" }),
          this._hass.callWS({ type: "config/device_registry/list" }),
        ]);
        const names = new Map(devices.map((device) => [device.id, device.name_by_user || device.name]));
        const grouped = new Map();
        for (const item of entities) {
          if (item.platform !== "mova_litterbox" || !item.device_id || item.disabled_by) continue;
          if (!grouped.has(item.device_id)) grouped.set(item.device_id, {
            id: item.device_id, name: names.get(item.device_id) || "MOVA Litter Box", fields: {}, pets: new Map(),
          });
          const device = grouped.get(item.device_id);
          const key = MATCH_KEYS.find((candidate) => item.unique_id?.endsWith(`_${candidate}`));
          if (key) {
            device.fields[key] = item.entity_id;
            continue;
          }
          const pet = item.unique_id?.match(/_pet_(.+)_(yesterday_visits|last_visit|visits|weight)$/);
          if (pet) {
            if (!device.pets.has(pet[1])) device.pets.set(pet[1], {});
            device.pets.get(pet[1])[pet[2]] = item.entity_id;
          }
        }
        this._devices = [...grouped.values()].filter((device) => device.fields.device_status);
        this._loaded = this._devices.length > 0;
        this._render();
      } catch (error) {
        this._error = "Could not load MOVA devices. Refresh the dashboard to retry.";
        this._render();
        console.warn("MOVA card device discovery failed", error);
      } finally {
        this._loading = false;
      }
    }

    _device() {
      return this._devices.find((device) => device.id === this._selection) || this._devices[0];
    }

    _state(key) {
      const id = this._device()?.fields[key];
      return id ? this._hass?.states?.[id] : undefined;
    }

    _set(selector, value) {
      const element = this.shadowRoot.querySelector(selector);
      if (element) element.textContent = value;
    }

    _render() {
      if (!this._config) return;
      const wasOpen = this.shadowRoot.querySelector("dialog")?.open;
      const device = this._device();
      this.shadowRoot.innerHTML = `
        <style>
          :host{display:block;min-width:0;font-family:var(--primary-font-family,inherit);color:var(--primary-text-color)}
          *{box-sizing:border-box}button,input,select{font:inherit}button{cursor:pointer}button:disabled,input:disabled,select:disabled{opacity:.45;cursor:not-allowed}
          button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
          ha-card{overflow:hidden}.tile{width:100%;display:flex;align-items:center;gap:13px;padding:16px;border:0;background:transparent;color:inherit;text-align:left;min-height:90px}
          .icon{height:44px;width:44px;border-radius:14px;flex:none;display:grid;place-items:center;background:var(--state-icon-color,var(--secondary-background-color));color:var(--state-icon-active-color,var(--primary-color))}
          .icon ha-icon{--mdc-icon-size:26px}.copy{flex:1;min-width:0}.name{display:block;font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
          .status,.sub{display:block;color:var(--secondary-text-color);font-size:13px;margin-top:3px}.sub{font-size:12px}.value{text-align:right;flex:none}.value strong{display:block;font-size:20px;font-weight:600}.value small{display:block;color:var(--secondary-text-color);font-size:11px}
          .due{color:var(--error-color,#d9534f)!important}dialog{width:min(560px,calc(100vw - 24px));max-height:calc(100dvh - 24px);border:1px solid var(--divider-color);border-radius:20px;background:var(--card-background-color,var(--ha-card-background,#fff));color:var(--primary-text-color);padding:0;box-shadow:0 20px 60px #0005}
          dialog::backdrop{background:#0008}.sheet{max-height:calc(100dvh - 24px);display:flex;flex-direction:column}.head{display:flex;align-items:center;gap:12px;padding:18px 20px;border-bottom:1px solid var(--divider-color)}.head h2{font-size:19px;margin:0;flex:1}.close{border:0;background:var(--secondary-background-color);color:inherit;border-radius:50%;width:36px;height:36px}
          .body{overflow:auto;padding:20px}.lead{font-size:14px;color:var(--secondary-text-color);margin:0 0 18px}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:20px}.stat{background:var(--secondary-background-color);border-radius:12px;padding:12px}.stat small{display:block;color:var(--secondary-text-color);font-size:11px}.stat strong{display:block;margin-top:5px;font-size:18px;overflow-wrap:anywhere}
          h3{font-size:14px;margin:22px 0 10px}.pet-list{display:grid;gap:7px}.pet{padding:10px 12px;background:var(--secondary-background-color);border-radius:10px;display:flex;justify-content:space-between;gap:8px;font-size:13px}.pet small{color:var(--secondary-text-color)}
          .bag{background:var(--secondary-background-color);border-radius:14px;padding:14px}.bag-top{display:flex;align-items:center;justify-content:space-between;gap:10px}.bag-top strong{font-size:15px}.bag p{margin:5px 0 12px;font-size:13px;color:var(--secondary-text-color)}.row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:9px}.row label{font-size:12px;color:var(--secondary-text-color);min-width:105px}.row input,.row select{flex:1;min-width:120px;padding:7px;border:1px solid var(--divider-color);border-radius:8px;color:inherit;background:var(--card-background-color,var(--ha-card-background,#fff))}
          .small-button{border:1px solid var(--divider-color);background:var(--card-background-color,var(--ha-card-background,#fff));color:inherit;border-radius:8px;padding:7px 10px;font-size:12px}.action-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.action{display:flex;align-items:center;justify-content:center;gap:7px;min-height:46px;border:1px solid var(--divider-color);border-radius:10px;background:var(--secondary-background-color);color:inherit;font-size:13px}.action ha-icon{--mdc-icon-size:18px}.action[aria-pressed=true]{color:var(--primary-color);border-color:var(--primary-color)}
          details{border-top:1px solid var(--divider-color);margin-top:21px;padding-top:13px}summary{cursor:pointer;font-weight:600;font-size:14px}.settings{display:grid;gap:2px;margin-top:12px}.setting{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:42px;font-size:13px}.setting span{flex:1}.setting button{border:1px solid var(--divider-color);border-radius:9px;background:var(--secondary-background-color);color:inherit;padding:7px 11px}.setting button[aria-pressed=true]{color:var(--primary-color);border-color:var(--primary-color)}.setting select,.setting input{max-width:150px;padding:6px;border:1px solid var(--divider-color);border-radius:7px;background:var(--card-background-color,var(--ha-card-background,#fff));color:inherit}
          .message{font-size:12px;color:var(--error-color,#d9534f);min-height:1em;margin:12px 0 0}@media(max-width:420px){.body{padding:16px}.head{padding:15px 16px}.action-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{gap:5px}.stat{padding:10px}}
        </style>
        <ha-card><button class="tile" type="button" aria-label="Open MOVA litter box controls"><span class="icon"><ha-icon icon="mdi:cat"></ha-icon></span><span class="copy"><span class="name"></span><span class="status"></span><span class="sub"></span></span><span class="value"><strong class="visits"></strong><small>visits today</small></span></button></ha-card>
        <dialog><div class="sheet"><div class="head"><ha-icon icon="mdi:cat"></ha-icon><h2 class="dialog-name"></h2><button class="close" type="button" data-close aria-label="Close">×</button></div><div class="body">
          <div class="device-choice" hidden><label for="mova-device">Device </label><select id="mova-device"></select></div><p class="lead"></p>
          <div class="stats"><div class="stat"><small>Visits today</small><strong class="stat-visits">—</strong></div><div class="stat"><small>Average visit</small><strong class="stat-duration">—</strong></div><div class="stat"><small>Last visit</small><strong class="stat-last">—</strong></div></div>
          <section class="pet-section" hidden><h3>Toileting data</h3><div class="pet-list"></div></section>
          <section class="bag"><div class="bag-top"><strong>Waste bag</strong><button class="small-button" type="button" data-press="bag_replaced">Bag replaced now</button></div><p class="bag-estimate"></p><div class="row"><label for="mova-bag-date">Last replaced</label><input id="mova-bag-date" data-date="bag_replacement_date" type="date"></div><div class="row"><label for="mova-bag-mode">Reminder</label><select id="mova-bag-mode" data-select="bag_reminder_mode"></select></div><div class="manual" hidden><div class="row"><label for="mova-bag-visits">At visits</label><input id="mova-bag-visits" data-number="bag_reminder_visits" type="number"><button class="small-button" type="button" data-save="bag_reminder_visits">Save</button></div><div class="row"><label for="mova-bag-days">Or after days</label><input id="mova-bag-days" data-number="bag_reminder_days" type="number"><button class="small-button" type="button" data-save="bag_reminder_days">Save</button></div></div></section>
          <h3>Actions</h3><div class="action-grid"></div><div class="action-grid quick-switches" style="margin-top:8px"></div>
          <details><summary>Settings</summary><div class="settings"></div></details><p class="message" role="status"></p>
        </div></div></dialog>`;
      this._set(".name", device?.name || "MOVA Litter Box");
      this._set(".dialog-name", device?.name || "MOVA Litter Box");
      const actionGrid = this.shadowRoot.querySelector(".action-grid");
      for (const [key, label, icon] of ACTIONS) {
        if (!device?.fields[key]) continue;
        const button = document.createElement("button");
        button.className = "action";
        button.type = "button";
        button.dataset.press = key;
        const haIcon = document.createElement("ha-icon");
        haIcon.setAttribute("icon", icon);
        button.append(haIcon, document.createTextNode(label));
        actionGrid.append(button);
      }
      for (const [key, label, icon] of [["air_purification", "Air purification", "mdi:air-filter"], ["deodorizing_liquid", "Deodorize", "mdi:spray"]]) {
        if (!device?.fields[key]) continue;
        const button = document.createElement("button");
        button.className = "action";
        button.type = "button";
        button.dataset.toggle = key;
        const haIcon = document.createElement("ha-icon");
        haIcon.setAttribute("icon", icon);
        button.append(haIcon, document.createTextNode(label));
        this.shadowRoot.querySelector(".quick-switches").append(button);
      }
      for (const [key, label] of SETTINGS) {
        const entity = device?.fields[key];
        if (!entity) continue;
        const row = document.createElement("div");
        row.className = "setting";
        const name = document.createElement("span");
        name.textContent = label;
        row.append(name);
        const domain = entity.split(".", 1)[0];
        const control = document.createElement(domain === "select" ? "select" : domain === "number" ? "input" : "button");
        if (domain === "select") control.dataset.select = key;
        else if (domain === "number") { control.type = "number"; control.dataset.number = key; }
        else { control.type = "button"; control.dataset.toggle = key; }
        row.append(control);
        if (domain === "number") {
          const save = document.createElement("button");
          save.type = "button";
          save.dataset.save = key;
          save.textContent = "Save";
          row.append(save);
        }
        this.shadowRoot.querySelector(".settings").append(row);
      }
      const choice = this.shadowRoot.querySelector(".device-choice");
      choice.hidden = this._devices.length < 2;
      const picker = choice.querySelector("select");
      for (const item of this._devices) picker.add(new Option(item.name, item.id));
      if (device) picker.value = device.id;
      this._update();
      if (wasOpen) this.shadowRoot.querySelector("dialog").showModal();
    }

    _update() {
      if (!this.shadowRoot.querySelector("ha-card")) return;
      const device = this._device();
      const state = (key) => this._state(key);
      const value = (key) => unavailable(state(key)) ? "—" : state(key).state;
      this._set(".name", device?.name || "MOVA Litter Box");
      this._set(".dialog-name", device?.name || "MOVA Litter Box");
      this._set(".status", device ? title(value("device_status")) : this._error || (this._loading ? "Finding device…" : "No MOVA litter box found"));
      this._set(".visits", value("visits_today"));
      this._set(".stat-visits", value("visits_today"));
      this._set(".stat-duration", value("avg_duration"));
      this._set(".stat-last", value("last_visit"));
      this._set(".lead", `Device status: ${title(value("device_status"))}`);
      const estimate = state("bag_estimated_days_remaining");
      const days = Number(estimate?.state);
      const due = state("bag_reminder_due")?.state === "on";
      const bagText = due || (!unavailable(estimate) && days <= 0) ? "Replace the waste bag now" : unavailable(estimate) ? "Set the last replacement date to start an estimate" : `Replace the waste bag in about ${days} day${days === 1 ? "" : "s"}`;
      this._set(".sub", bagText);
      this._set(".bag-estimate", bagText);
      this.shadowRoot.querySelector(".sub")?.classList.toggle("due", due);
      this.shadowRoot.querySelector(".bag-estimate")?.classList.toggle("due", due);
      for (const button of this.shadowRoot.querySelectorAll("[data-press]")) {
        const current = state(button.dataset.press);
        button.disabled = !current || current.state === "unavailable";
      }
      for (const button of this.shadowRoot.querySelectorAll("[data-toggle]")) {
        const current = state(button.dataset.toggle);
        button.disabled = unavailable(current);
        button.setAttribute("aria-pressed", current?.state === "on" ? "true" : "false");
        if (button.closest(".settings")) button.textContent = current?.state === "on" ? "On" : "Off";
      }
      for (const select of this.shadowRoot.querySelectorAll("[data-select]")) {
        const current = state(select.dataset.select);
        const options = current?.attributes?.options || [];
        if (select.options.length !== options.length || options.some((option, i) => select.options[i]?.value !== option)) {
          select.replaceChildren(...options.map((option) => new Option(option, option)));
        }
        select.disabled = unavailable(current);
        if (select !== this.shadowRoot.activeElement) select.value = current?.state || "";
      }
      for (const input of this.shadowRoot.querySelectorAll("[data-date],[data-number]")) {
        const key = input.dataset.date || input.dataset.number;
        const current = state(key);
        input.disabled = !current || current.state === "unavailable";
        if (input !== this.shadowRoot.activeElement) input.value = unavailable(current) ? "" : current.state;
        if (input.type === "number") {
          input.min = current?.attributes?.min ?? "";
          input.max = current?.attributes?.max ?? "";
          input.step = current?.attributes?.step ?? "1";
        }
      }
      this.shadowRoot.querySelector(".manual").hidden = state("bag_reminder_mode")?.state !== "Manual";
      const petList = this.shadowRoot.querySelector(".pet-list");
      petList.replaceChildren();
      if (device) for (const pet of device.pets.values()) {
        const visits = this._hass?.states?.[pet.visits];
        const name = visits?.attributes?.friendly_name?.replace(/ Visits Today$/, "") || "Pet";
        const row = document.createElement("div");
        row.className = "pet";
        const label = document.createElement("span");
        label.textContent = name;
        const data = document.createElement("small");
        const weight = this._hass?.states?.[pet.weight];
        data.textContent = `${unavailable(visits) ? "—" : visits.state} visits today${unavailable(weight) ? "" : ` · ${weight.state} ${weight.attributes.unit_of_measurement || "kg"}`}`;
        row.append(label, data);
        petList.append(row);
      }
      this.shadowRoot.querySelector(".pet-section").hidden = !petList.childElementCount;
    }

    async _call(key, service, data = {}) {
      const entity_id = this._device()?.fields[key];
      if (!entity_id) return;
      const message = this.shadowRoot.querySelector(".message");
      message.textContent = "";
      try {
        await this._hass.callService(entity_id.split(".")[0], service, { entity_id, ...data });
      } catch (error) {
        message.textContent = error?.message || "The command could not be sent.";
      }
    }

    _onClick(event) {
      const button = event.target.closest("button");
      if (!button) return;
      if (button.classList.contains("tile")) {
        this.shadowRoot.querySelector("dialog")?.showModal();
      } else if (button.dataset.close !== undefined) {
        this.shadowRoot.querySelector("dialog")?.close();
      } else if (button.dataset.press) {
        void this._call(button.dataset.press, "press");
      } else if (button.dataset.toggle) {
        const key = button.dataset.toggle;
        void this._call(key, this._state(key)?.state === "on" ? "turn_off" : "turn_on");
      } else if (button.dataset.save) {
        const key = button.dataset.save;
        const input = this.shadowRoot.querySelector(`[data-number="${key}"]`);
        if (input?.reportValidity()) void this._call(key, "set_value", { value: Number(input.value) });
      }
    }

    _onChange(event) {
      const element = event.target;
      if (element.id === "mova-device") {
        this._selection = element.value;
        this._render();
        return;
      }
      if (element.dataset.select) void this._call(element.dataset.select, "select_option", { option: element.value });
      if (element.dataset.date && element.value) void this._call(element.dataset.date, "set_value", { date: element.value });
    }
  }

  customElements.define("mova-litter-card", MovaLitterCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "mova-litter-card", name: "MOVA Litter Box",
    description: "Device tile with litter box status, visits, bag estimate, and controls",
    preview: true,
    documentationURL: "https://github.com/murtaza911/ha-mova-litterbox",
  });
})();
