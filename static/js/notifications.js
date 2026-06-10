/* Campana de notificaciones + Web Push (solo super_manager / superuser).
   Config vía data-attrs del nodo #notif-bell:
     data-vapid-key, data-url-list, data-url-unread, data-url-read-all,
     data-url-read (con 0 como placeholder del pk), data-url-subscribe, data-url-unsubscribe */
(function () {
  'use strict';

  const bell = document.getElementById('notif-bell');
  if (!bell) return;

  const cfg = bell.dataset;
  const badge = document.getElementById('notif-badge');
  const list = document.getElementById('notif-list');
  const readAllBtn = document.getElementById('notif-read-all');
  const pushBtn = document.getElementById('push-enable-btn');
  const pushStatus = document.getElementById('push-status');

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;
  const pushSupported = 'serviceWorker' in navigator
    && 'PushManager' in window
    && typeof Notification !== 'undefined';

  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  function post(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken(), 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : null,
    });
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(base64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  /* ── Badge ──────────────────────────────────────────────────────────── */
  function setBadge(count) {
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : count;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }

  function refreshUnread() {
    fetch(cfg.urlUnread)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setBadge(d.unread_count); })
      .catch(() => {});
  }
  setInterval(refreshUnread, 60000);

  /* ── Lista del dropdown ─────────────────────────────────────────────── */
  function timeAgo(iso) {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return 'hace un momento';
    if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
    if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
    return `hace ${Math.floor(diff / 86400)} d`;
  }

  function eventIcon(event) {
    return event === 'technician_pending' ? 'fa-user-clock' : 'fa-clipboard-check';
  }

  function renderList(items) {
    if (!items.length) {
      list.innerHTML = '<li class="px-4 py-6 text-center text-sm text-base-content/40">Sin notificaciones</li>';
      return;
    }
    list.innerHTML = items.map((n) => `
      <li>
        <button type="button" data-id="${n.id}" data-url="${n.url}"
                class="notif-item w-full text-left px-4 py-3 flex gap-3 items-start hover:bg-base-200 transition-colors ${n.is_read ? 'opacity-55' : ''}">
          <span class="mt-0.5 w-8 h-8 shrink-0 rounded-full flex items-center justify-center
                       ${n.is_read ? 'bg-base-200 text-base-content/40' : 'bg-primary/10 text-primary'}">
            <i class="fa-solid ${eventIcon(n.event)} text-xs"></i>
          </span>
          <span class="min-w-0">
            <span class="block text-[13px] font-semibold leading-snug">${n.title}</span>
            ${n.body ? `<span class="block text-xs text-base-content/60 leading-snug mt-0.5">${n.body}</span>` : ''}
            <span class="block text-[11px] text-base-content/40 mt-1">${timeAgo(n.created_at)}</span>
          </span>
        </button>
      </li>`).join('');

    list.querySelectorAll('.notif-item').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const url = btn.dataset.url;
        post(cfg.urlRead.replace('/0/', `/${id}/`)).finally(() => {
          if (url) window.location.href = url;
        });
      });
    });
  }

  function loadList() {
    list.innerHTML = '<li class="px-4 py-6 text-center"><span class="loading loading-spinner loading-sm"></span></li>';
    fetch(cfg.urlList)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setBadge(d.unread_count);
        renderList(d.items);
      })
      .catch(() => {
        list.innerHTML = '<li class="px-4 py-6 text-center text-sm text-error">Error al cargar</li>';
      });
  }

  bell.querySelector('label, [tabindex]').addEventListener('click', loadList);
  bell.addEventListener('focusin', function once() {
    loadList();
    bell.removeEventListener('focusin', once);
  });

  if (readAllBtn) {
    readAllBtn.addEventListener('click', () => {
      post(cfg.urlReadAll).then(() => {
        setBadge(0);
        loadList();
      });
    });
  }

  /* ── Web Push ───────────────────────────────────────────────────────── */
  let swRegistration = null;

  function setPushUI(state) {
    // state: 'available' | 'active' | 'denied' | 'ios-install' | 'unsupported'
    pushBtn.classList.add('hidden');
    pushBtn.disabled = false;
    switch (state) {
      case 'available':
        pushBtn.classList.remove('hidden');
        pushBtn.innerHTML = '<i class="fa-solid fa-bell"></i> Activar notificaciones en este dispositivo';
        pushStatus.textContent = '';
        break;
      case 'active':
        pushStatus.innerHTML = '<i class="fa-solid fa-circle-check text-success"></i> Notificaciones activas en este dispositivo · <a href="#" id="push-disable" class="link">desactivar</a>';
        attachDisable();
        break;
      case 'denied':
        pushStatus.textContent = 'Notificaciones bloqueadas — habilítalas en la configuración del navegador.';
        break;
      case 'ios-install':
        pushBtn.classList.remove('hidden');
        pushBtn.innerHTML = '<i class="fa-brands fa-apple"></i> Activar notificaciones en iPhone';
        pushStatus.textContent = '';
        break;
      default:
        pushStatus.textContent = 'Este navegador no soporta notificaciones push.';
    }
  }

  function attachDisable() {
    const a = document.getElementById('push-disable');
    if (!a) return;
    a.addEventListener('click', (e) => {
      e.preventDefault();
      if (!swRegistration) return;
      swRegistration.pushManager.getSubscription().then((sub) => {
        if (!sub) { setPushUI('available'); return; }
        const endpoint = sub.endpoint;
        sub.unsubscribe().then(() => {
          post(cfg.urlUnsubscribe, { endpoint });
          setPushUI('available');
          if (window.Alert) Alert.info('Notificaciones desactivadas en este dispositivo.');
        });
      });
    });
  }

  function initPush() {
    if (isIOS && !isStandalone) {
      setPushUI('ios-install');
      pushBtn.addEventListener('click', () => {
        document.getElementById('ios-install-modal').showModal();
      });
      return;
    }
    if (!pushSupported) {
      setPushUI('unsupported');
      return;
    }
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      swRegistration = reg;
      if (Notification.permission === 'denied') {
        setPushUI('denied');
        return;
      }
      reg.pushManager.getSubscription().then((sub) => {
        setPushUI(sub ? 'active' : 'available');
      });
    }).catch(() => setPushUI('unsupported'));

    pushBtn.addEventListener('click', subscribe);
  }

  function subscribe() {
    if (!swRegistration) return;
    pushBtn.disabled = true;
    // requestPermission debe ejecutarse dentro del gesto de usuario (crítico en iOS)
    Notification.requestPermission().then((permission) => {
      if (permission !== 'granted') {
        setPushUI(permission === 'denied' ? 'denied' : 'available');
        return;
      }
      return swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(cfg.vapidKey),
      }).then((sub) => post(cfg.urlSubscribe, sub.toJSON()))
        .then((r) => {
          if (r && r.ok) {
            setPushUI('active');
            if (window.Alert) Alert.success('Notificaciones activadas en este dispositivo.');
          } else {
            setPushUI('available');
            if (window.Alert) Alert.error('No se pudo registrar la suscripción.');
          }
        });
    }).catch(() => {
      setPushUI('available');
      if (window.Alert) Alert.error('No se pudo activar las notificaciones.');
    });
  }

  initPush();
})();
