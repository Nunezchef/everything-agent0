import { createStore } from "/js/AlpineStore.js";
import * as API from "/js/api.js";
import { store as notificationStore } from "/components/notifications/notification-store.js";

function toast(type, text, timeoutSec = 4) {
  notificationStore.addFrontendToastOnly(type, text, "", timeoutSec);
}

function extractError(response) {
  if (!response) return "Unknown ECC error";
  if (response.error) return String(response.error);
  if (response.git && response.git.error) return String(response.git.error);
  return "ECC operation failed";
}

const model = {
  loading: false,
  error: null,
  status: null,
  backups: [],
  selectedBackupId: "",
  backupBeforeUpdate: true,

  async _call(payload) {
    return await API.callJsonApi("ecc_sync", payload);
  },

  async _callChecked(payload) {
    const response = await this._call(payload);
    if (response && response.success === false) {
      throw new Error(extractError(response));
    }
    return response;
  },

  formatTime(ts) {
    if (!ts) return "unknown";
    const dt = new Date(ts);
    if (Number.isNaN(dt.getTime())) return String(ts);
    return dt.toLocaleString();
  },

  async loadStatus() {
    this.loading = true;
    this.error = null;
    try {
      this.status = await this._callChecked({ action: "status" });
      const backupList = await this._callChecked({ action: "backup_list" });
      this.backups = backupList.items || [];
    } catch (e) {
      this.error = e.message || String(e);
      toast("error", `ECC status failed: ${this.error}`, 6);
    } finally {
      this.loading = false;
    }
  },

  async syncNow() {
    this.loading = true;
    this.error = null;
    try {
      await this._callChecked({ action: "sync" });
      toast("success", "ECC installed/synced");
      await this.loadStatus();
    } catch (e) {
      this.error = e.message || String(e);
      toast("error", `ECC sync failed: ${this.error}`, 6);
    } finally {
      this.loading = false;
    }
  },

  async updateLatest() {
    this.loading = true;
    this.error = null;
    try {
      await this._callChecked({
        action: "update_latest",
        backup_before_update: this.backupBeforeUpdate,
      });
      toast("success", "ECC updated from Git");
      await this.loadStatus();
    } catch (e) {
      this.error = e.message || String(e);
      toast("error", `ECC update failed: ${this.error}`, 6);
    } finally {
      this.loading = false;
    }
  },

  async createBackup() {
    this.loading = true;
    this.error = null;
    try {
      await this._callChecked({ action: "backup_create" });
      toast("success", "ECC backup point created");
      const backupList = await this._callChecked({ action: "backup_list" });
      this.backups = backupList.items || [];
    } catch (e) {
      this.error = e.message || String(e);
      toast("error", `ECC backup failed: ${this.error}`, 6);
    } finally {
      this.loading = false;
    }
  },

  async restoreSelectedBackup() {
    if (!this.selectedBackupId) return;
    this.loading = true;
    this.error = null;
    try {
      await this._callChecked({
        action: "backup_restore",
        backup_id: this.selectedBackupId,
      });
      toast("success", "ECC backup restored");
      await this.loadStatus();
    } catch (e) {
      this.error = e.message || String(e);
      toast("error", `ECC restore failed: ${this.error}`, 6);
    } finally {
      this.loading = false;
    }
  },
};

const store = createStore("eccSettings", model);
export { store };
