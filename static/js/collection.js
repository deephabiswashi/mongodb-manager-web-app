document.addEventListener("DOMContentLoaded", () => {
  const addBtn = document.getElementById("addCollectionBtn");
  const modal = new bootstrap.Modal(document.getElementById("addCollectionModal"));
  const confirmAdd = document.getElementById("confirmAddCollection");
  const input = document.getElementById("newCollectionName");

  // ➕ Open modal
  addBtn.addEventListener("click", () => {
    input.value = "";
    modal.show();
  });

  // Client-side validation for collection name
  function validateCollectionName(name) {
    if (!name || name.trim().length === 0) {
      return { valid: false, message: "Collection name is required" };
    }
    if (name.length > 255) {
      return { valid: false, message: "Collection name cannot exceed 255 characters" };
    }
    if (!/^[a-zA-Z0-9_\-\.]+$/.test(name)) {
      return { valid: false, message: "Collection name can only contain letters, numbers, underscores, hyphens, and dots" };
    }
    if (name.startsWith('system.')) {
      return { valid: false, message: "Collection name cannot start with 'system.'" };
    }
    return { valid: true };
  }

  // ✅ Confirm add
  confirmAdd.addEventListener("click", async () => {
    const name = input.value.trim();
    const validation = validateCollectionName(name);
    if (!validation.valid) {
      App.showToast(validation.message, 'danger');
      return;
    }
    const res = await fetch("/api/collection/create", {
      method: "POST",
      headers: App.getHeaders(),
      body: JSON.stringify({ db: dbName, collection: name })
    });
    const data = await res.json();
    if (res.ok) {
      App.showToast(data.message || "Collection created!", "success");
    } else {
      App.showToast(data.message || data.error || "Failed to create collection", "danger");
    }
    modal.hide();
    loadCollections();
  });

  // 🗑 Delete collection
  document.addEventListener("click", async (e) => {
    if (e.target.classList.contains("delete-collection")) {
      const name = e.target.dataset.name;
      if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
      const res = await fetch("/api/collection/delete", {
        method: "POST",
        headers: App.getHeaders(),
        body: JSON.stringify({ db: dbName, collection: name })
      });
      const data = await res.json();
      if (res.ok) {
        App.showToast(data.message || "Collection deleted!", "success");
      } else {
        App.showToast(data.message || data.error || "Failed to delete collection", "danger");
      }
      loadCollections();
    }
  });

  // 🔄 Reload collections (AJAX refresh)
  async function loadCollections() {
    const res = await fetch(`/api/collections/${dbName}`);
    const data = await res.json();
    const body = document.getElementById("collectionsBody");

    if (!data.collections.length) {
      document.getElementById("collectionsContainer").innerHTML =
        `<div class="alert alert-info">No collections found in this database.</div>`;
      return;
    }

    body.innerHTML = "";
    data.collections.forEach(col => {
      const row = `
        <tr data-name="${col}">
          <td>${col}</td>
          <td>
            <a href="/data/${dbName}/${col}" class="btn btn-primary btn-sm">📂 Open</a>
            <button class="btn btn-danger btn-sm delete-collection" data-name="${col}">🗑 Delete</button>
          </td>
        </tr>`;
      body.insertAdjacentHTML("beforeend", row);
    });
  }
});
