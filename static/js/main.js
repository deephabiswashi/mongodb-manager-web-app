// Global helpers: toast notifications and small utilities
window.App = (function(){
  function showToast(message, variant="dark"){
    const toastEl = document.getElementById("app-toast");
    const body = document.getElementById("app-toast-body");
    if(!toastEl || !body) return alert(message);
    // swap contextual class
    toastEl.className = `toast align-items-center text-bg-${variant} border-0`;
    body.textContent = message;
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 2200 });
    toast.show();
  }

  // Helper to get CSRF token for AJAX
  function getCSRFToken() {
    return window.csrfToken || '';
  }

  // Helper to add CSRF token to headers
  function getHeaders(additional = {}) {
    return {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
      ...additional
    };
  }

  return { showToast, getCSRFToken, getHeaders };
})();


