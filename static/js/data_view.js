// static/js/data_view.js
document.addEventListener("DOMContentLoaded", () => {
  const dbName = document.getElementById("db-name").dataset.name;
  const collName = document.getElementById("coll-name").dataset.name;
  const tableBody = document.querySelector("#data-table tbody");
  const paginationDiv = document.getElementById("pagination");
  const refreshBtn = document.getElementById("refresh-btn");

  const addModal = new bootstrap.Modal(document.getElementById("addModal"));
  const editModal = new bootstrap.Modal(document.getElementById("editModal"));

  const addForm = document.getElementById("add-form");
  const editForm = document.getElementById("edit-form");

  let currentPage = 1;
  const pageSize = 10;

  // --- Fetch data with pagination ---
  async function fetchDocuments(page = 1) {
    try {
      const res = await fetch(
        `/api/data/${dbName}/${collName}?page=${page}&limit=${pageSize}`
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      renderTable(data.documents);
      renderPagination(data.total, page);
    } catch (err) {
      alert("Error fetching documents: " + err.message);
    }
  }

  // --- Render documents into table ---
  function renderTable(docs) {
    tableBody.innerHTML = "";
    if (!docs.length) {
      tableBody.innerHTML =
        '<tr><td colspan="3" class="text-center text-muted">No documents found.</td></tr>';
      return;
    }

    docs.forEach((doc) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><pre>${JSON.stringify(doc, null, 2)}</pre></td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-secondary me-2 edit-btn" data-doc='${JSON.stringify(
            doc
          )}'>Edit</button>
          <button class="btn btn-sm btn-outline-danger delete-btn" data-doc='${JSON.stringify(
            doc
          )}'>Delete</button>
        </td>
      `;
      tableBody.appendChild(tr);
    });

    attachRowHandlers();
  }

  // --- Pagination controls ---
  function renderPagination(totalDocs, current) {
    const totalPages = Math.ceil(totalDocs / pageSize);
    paginationDiv.innerHTML = "";
    if (totalPages <= 1) return;

    for (let i = 1; i <= totalPages; i++) {
      const btn = document.createElement("button");
      btn.className = `btn btn-sm ${
        i === current ? "btn-primary" : "btn-outline-primary"
      } me-1`;
      btn.textContent = i;
      btn.addEventListener("click", () => {
        currentPage = i;
        fetchDocuments(currentPage);
      });
      paginationDiv.appendChild(btn);
    }
  }

  // --- CRUD Actions ---
  refreshBtn.addEventListener("click", () => fetchDocuments(currentPage));

  // Add document
  addForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const jsonText = document.getElementById("add-json").value;
    try {
      const doc = JSON.parse(jsonText);
      const res = await fetch(`/api/data/${dbName}/${collName}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(doc),
      });
      if (!res.ok) throw new Error(await res.text());
      addModal.hide();
      fetchDocuments(currentPage);
    } catch (err) {
      alert("Invalid JSON or error adding: " + err.message);
    }
  });

  // Edit document
  editForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const oldDoc = JSON.parse(document.getElementById("edit-old-doc").value);
    const newDoc = JSON.parse(document.getElementById("edit-json").value);
    try {
      const res = await fetch(`/api/data/${dbName}/${collName}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old: oldDoc, new: newDoc }),
      });
      if (!res.ok) throw new Error(await res.text());
      editModal.hide();
      fetchDocuments(currentPage);
    } catch (err) {
      alert("Error editing document: " + err.message);
    }
  });

  function attachRowHandlers() {
    document.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const doc = JSON.parse(e.target.dataset.doc);
        if (!confirm("Delete this document?")) return;
        try {
          const res = await fetch(`/api/data/${dbName}/${collName}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(doc),
          });
          if (!res.ok) throw new Error(await res.text());
          fetchDocuments(currentPage);
        } catch (err) {
          alert("Error deleting: " + err.message);
        }
      });
    });

    document.querySelectorAll(".edit-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const doc = JSON.parse(e.target.dataset.doc);
        document.getElementById("edit-json").value = JSON.stringify(
          doc,
          null,
          2
        );
        document.getElementById("edit-old-doc").value = JSON.stringify(doc);
        editModal.show();
      });
    });
  }

  // Initial load
  fetchDocuments();
});
